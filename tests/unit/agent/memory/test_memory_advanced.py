"""Unit tests for memory advanced features: fallback and compaction."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import pytest

from owlclaw.agent.memory.models import MemoryConfig, MemoryEntry
from owlclaw.agent.memory.service import MemoryService
from owlclaw.agent.memory.store import MemoryStore
from owlclaw.agent.memory.store_inmemory import InMemoryStore


class _FailingEmbedder:
    async def embed(self, text: str) -> list[float]:  # noqa: ARG002
        raise RuntimeError("embed unavailable")

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:  # noqa: ARG002
        raise RuntimeError("embed unavailable")

    @property
    def dimensions(self) -> int:
        return 2


class _FailingSearchStore(MemoryStore):
    def __init__(self) -> None:
        self._delegate = InMemoryStore()

    async def save(self, entry: MemoryEntry) -> UUID:
        return await self._delegate.save(entry)

    async def search(
        self,
        agent_id: str,
        tenant_id: str,
        query_embedding: list[float] | None,
        limit: int = 5,
        tags: list[str] | None = None,
        include_archived: bool = False,
    ) -> list[tuple[MemoryEntry, float]]:
        raise RuntimeError("vector unavailable")

    async def get_recent(self, agent_id: str, tenant_id: str, hours: int = 24, limit: int = 5) -> list[MemoryEntry]:
        return await self._delegate.get_recent(agent_id, tenant_id, hours, limit)

    async def archive(self, entry_ids: list[UUID]) -> int:
        return await self._delegate.archive(entry_ids)

    async def delete(self, entry_ids: list[UUID]) -> int:
        return await self._delegate.delete(entry_ids)

    async def count(self, agent_id: str, tenant_id: str) -> int:
        return await self._delegate.count(agent_id, tenant_id)

    async def update_access(self, agent_id: str, tenant_id: str, entry_ids: list[UUID]) -> None:
        await self._delegate.update_access(agent_id, tenant_id, entry_ids)

    async def list_entries(
        self,
        agent_id: str,
        tenant_id: str,
        order_created_asc: bool,
        limit: int,
        include_archived: bool = False,
    ) -> list[MemoryEntry]:
        return await self._delegate.list_entries(agent_id, tenant_id, order_created_asc, limit, include_archived)

    async def get_expired_entry_ids(
        self,
        agent_id: str,
        tenant_id: str,
        before: datetime,
        max_access_count: int = 0,
    ) -> list[UUID]:
        return await self._delegate.get_expired_entry_ids(agent_id, tenant_id, before, max_access_count)


class _FailingSaveStore(MemoryStore):
    async def save(self, entry: MemoryEntry) -> UUID:
        raise RuntimeError("store unavailable")

    async def search(
        self,
        agent_id: str,
        tenant_id: str,
        query_embedding: list[float] | None,
        limit: int = 5,
        tags: list[str] | None = None,
        include_archived: bool = False,
    ) -> list[tuple[MemoryEntry, float]]:
        return []

    async def get_recent(self, agent_id: str, tenant_id: str, hours: int = 24, limit: int = 5) -> list[MemoryEntry]:
        return []

    async def archive(self, entry_ids: list[UUID]) -> int:
        return 0

    async def delete(self, entry_ids: list[UUID]) -> int:
        return 0

    async def count(self, agent_id: str, tenant_id: str) -> int:
        return 0

    async def update_access(self, agent_id: str, tenant_id: str, entry_ids: list[UUID]) -> None:
        return None

    async def list_entries(
        self,
        agent_id: str,
        tenant_id: str,
        order_created_asc: bool,
        limit: int,
        include_archived: bool = False,
    ) -> list[MemoryEntry]:
        return []

    async def get_expired_entry_ids(
        self,
        agent_id: str,
        tenant_id: str,
        before: datetime,
        max_access_count: int = 0,
    ) -> list[UUID]:
        return []


@pytest.mark.asyncio
async def test_recall_uses_keyword_fallback_when_search_fails() -> None:
    store = _FailingSearchStore()
    cfg = MemoryConfig(enable_keyword_fallback=True, enable_tfidf_fallback=False)
    service = MemoryService(store=store, embedder=_FailingEmbedder(), config=cfg)
    await store.save(MemoryEntry(agent_id="a", tenant_id="t", content="market crash rebound lesson", embedding=[1.0, 0.0]))

    with pytest.raises(RuntimeError):
        await service.recall("a", "t", "market rebound", limit=5)

    cfg2 = MemoryConfig(enable_keyword_fallback=True, enable_tfidf_fallback=True, tfidf_dimensions=32)
    service2 = MemoryService(store=store, embedder=_FailingEmbedder(), config=cfg2)

    class _FallbackEmbedder:
        async def embed(self, text: str) -> list[float]:
            return [1.0, 0.0]

        async def embed_batch(self, texts: list[str]) -> list[list[float]]:
            return [[1.0, 0.0] for _ in texts]

        @property
        def dimensions(self) -> int:
            return 2

    service2._fallback_embedder = _FallbackEmbedder()
    results = await service2.recall("a", "t", "market rebound", limit=5)
    assert len(results) == 1
    assert "rebound" in results[0].entry.content


@pytest.mark.asyncio
async def test_compact_merges_same_tag_group() -> None:
    store = InMemoryStore()
    cfg = MemoryConfig(vector_backend="inmemory", compaction_threshold=3, enable_tfidf_fallback=False)

    class _SimpleEmbedder:
        async def embed(self, text: str) -> list[float]:
            return [float(len(text)), 1.0]

        async def embed_batch(self, texts: list[str]) -> list[list[float]]:
            return [[float(len(t)), 1.0] for t in texts]

        @property
        def dimensions(self) -> int:
            return 2

    service = MemoryService(store=store, embedder=_SimpleEmbedder(), config=cfg)
    for i in range(3):
        await service.remember("a", "t", f"trading lesson {i}", tags=["trading"])

    result = await service.compact("a", "t")
    assert result.merged_groups == 1
    assert result.created_summaries == 1

    entries = await store.list_entries("a", "t", order_created_asc=False, limit=20, include_archived=True)
    assert any("compaction:trading" in e.content for e in entries)


@pytest.mark.asyncio
async def test_remember_file_fallback_sanitizes_multiline_content(tmp_path) -> None:
    cfg = MemoryConfig(
        enable_file_fallback=True,
        enable_tfidf_fallback=False,
        file_fallback_path=str(tmp_path / "MEMORY.md"),
    )

    class _StaticEmbedder:
        async def embed(self, text: str) -> list[float]:
            return [0.1, 0.2]

        async def embed_batch(self, texts: list[str]) -> list[list[float]]:
            return [[0.1, 0.2] for _ in texts]

        @property
        def dimensions(self) -> int:
            return 2

    service = MemoryService(store=_FailingSaveStore(), embedder=_StaticEmbedder(), config=cfg)
    await service.remember("agent-a", "default", "line1\nline2", tags=["a,b", " c "])
    text = (tmp_path / "MEMORY.md").read_text(encoding="utf-8")
    assert "content: line1\\nline2" in text
    assert "tags: [a_b, c]" in text
