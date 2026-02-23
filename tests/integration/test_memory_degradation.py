"""Integration-style degradation tests for MemoryService fallback paths."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import UUID

import pytest

from owlclaw.agent.memory.embedder_random import RandomEmbedder
from owlclaw.agent.memory.models import MemoryConfig, MemoryEntry
from owlclaw.agent.memory.service import MemoryService
from owlclaw.agent.memory.store import MemoryStore
from owlclaw.agent.memory.store_inmemory import InMemoryStore


class _StoreSaveUnavailable(MemoryStore):
    def __init__(self) -> None:
        self._delegate = InMemoryStore()

    async def save(self, entry: MemoryEntry) -> UUID:  # noqa: ARG002
        raise RuntimeError("postgres unavailable")

    async def search(
        self,
        agent_id: str,
        tenant_id: str,
        query_embedding: list[float] | None,
        limit: int = 5,
        tags: list[str] | None = None,
        include_archived: bool = False,
    ) -> list[tuple[MemoryEntry, float]]:
        return await self._delegate.search(agent_id, tenant_id, query_embedding, limit, tags, include_archived)

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


pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_remember_falls_back_to_memory_file_when_store_unavailable(tmp_path: Path) -> None:
    fallback_file = tmp_path / "MEMORY.md"
    config = MemoryConfig(
        vector_backend="inmemory",
        enable_file_fallback=True,
        file_fallback_path=str(fallback_file),
    )
    service = MemoryService(
        store=_StoreSaveUnavailable(),
        embedder=RandomEmbedder(dimensions=32),
        config=config,
    )
    memory_id = await service.remember("agent-a", "tenant-a", "critical outage runbook", tags=["ops"])

    text = fallback_file.read_text(encoding="utf-8")
    assert str(memory_id) in text
    assert "critical outage runbook" in text
