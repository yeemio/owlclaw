"""Unit tests for memory backend migration helpers."""

from __future__ import annotations

import pytest
import logging

from owlclaw.agent.memory.migration import migrate_store_data
from owlclaw.agent.memory.models import MemoryEntry
from owlclaw.agent.memory.store_inmemory import InMemoryStore


@pytest.mark.asyncio
async def test_migrate_store_data_copies_entries() -> None:
    source = InMemoryStore()
    target = InMemoryStore()
    await source.save(MemoryEntry(agent_id="a", tenant_id="t", content="one", embedding=[0.1, 0.2]))
    await source.save(MemoryEntry(agent_id="a", tenant_id="t", content="two", embedding=[0.2, 0.3]))

    result = await migrate_store_data(
        source=source,
        target=target,
        agent_id="a",
        tenant_id="t",
        batch_size=1,
    )

    assert result.moved == 2
    assert result.failed == 0
    assert await target.count("a", "t") == 2


@pytest.mark.asyncio
async def test_migrate_store_data_rejects_blank_agent() -> None:
    source = InMemoryStore()
    target = InMemoryStore()
    with pytest.raises(ValueError, match="agent_id must not be empty"):
        await migrate_store_data(source=source, target=target, agent_id=" ", tenant_id="t")


@pytest.mark.asyncio
async def test_migrate_store_data_rejects_blank_tenant() -> None:
    source = InMemoryStore()
    target = InMemoryStore()
    with pytest.raises(ValueError, match="tenant_id must not be empty"):
        await migrate_store_data(source=source, target=target, agent_id="a", tenant_id=" ")


@pytest.mark.asyncio
async def test_migrate_store_data_logs_failures(caplog) -> None:
    class _FailingTarget(InMemoryStore):
        async def save(self, entry: MemoryEntry):  # type: ignore[override]
            raise RuntimeError("write failed")

    source = InMemoryStore()
    await source.save(MemoryEntry(agent_id="a", tenant_id="t", content="one", embedding=[0.1, 0.2]))
    caplog.set_level(logging.WARNING)
    result = await migrate_store_data(source=source, target=_FailingTarget(), agent_id="a", tenant_id="t")
    assert result.failed == 1
    assert "memory migration failed for entry_id=" in caplog.text
