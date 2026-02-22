"""Unit tests for MemoryService."""

from __future__ import annotations

import pytest

from owlclaw.agent.memory.models import MemoryConfig, MemoryEntry
from owlclaw.agent.memory.service import MemoryService
from owlclaw.agent.memory.store import MemoryStore


class _DummyEmbedder:
    async def embed(self, text: str) -> list[float]:
        return [0.1, 0.2]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2] for _ in texts]

    @property
    def dimensions(self) -> int:
        return 2


class _CaptureLimitStore(MemoryStore):
    def __init__(self) -> None:
        self.last_limit: int | None = None

    async def save(self, entry: MemoryEntry):
        return entry.id

    async def search(
        self,
        agent_id: str,
        tenant_id: str,
        query_embedding: list[float] | None,
        limit: int = 5,
        tags: list[str] | None = None,
        include_archived: bool = False,
    ) -> list[tuple[MemoryEntry, float]]:
        self.last_limit = limit
        return []

    async def get_recent(
        self, agent_id: str, tenant_id: str, hours: int = 24, limit: int = 5
    ) -> list[MemoryEntry]:
        return []

    async def archive(self, entry_ids):
        return 0

    async def delete(self, entry_ids):
        return 0

    async def count(self, agent_id: str, tenant_id: str) -> int:
        return 0


@pytest.mark.asyncio
async def test_recall_clamps_limit_to_spec_max() -> None:
    """Recall limit should be constrained to spec max=20."""
    store = _CaptureLimitStore()
    service = MemoryService(store=store, embedder=_DummyEmbedder(), config=MemoryConfig())

    await service.recall(
        agent_id="a",
        tenant_id="default",
        query="q",
        limit=999,
    )
    assert store.last_limit == 20
