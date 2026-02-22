"""Unit tests for MemoryLifecycleManager (archive excess, delete expired)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from owlclaw.agent.memory import InMemoryStore, MemoryConfig, MemoryEntry, MemoryLifecycleManager, RandomEmbedder


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_lifecycle_archive_excess() -> None:
    """When count > max_entries, oldest entries are archived."""
    store = InMemoryStore()
    embedder = RandomEmbedder(dimensions=8, seed=42)
    config = MemoryConfig(max_entries=3, retention_days=365)
    manager = MemoryLifecycleManager(store, config)

    agent_id, tenant_id = "a", "default"
    for i in range(5):
        emb = await embedder.embed(f"Entry {i}")
        await store.save(MemoryEntry(agent_id=agent_id, tenant_id=tenant_id, content=f"Entry {i}", embedding=emb))

    assert await store.count(agent_id, tenant_id) == 5
    result = await manager.run_maintenance(agent_id, tenant_id)
    assert result.error is None
    assert result.archived_count == 2  # 5 - 3 = 2
    assert result.deleted_count == 0
    assert await store.count(agent_id, tenant_id) == 3


@pytest.mark.asyncio
async def test_lifecycle_delete_expired() -> None:
    """Entries older than retention_days with access_count 0 are deleted."""
    store = InMemoryStore()
    embedder = RandomEmbedder(dimensions=8, seed=42)
    config = MemoryConfig(max_entries=10000, retention_days=1)
    manager = MemoryLifecycleManager(store, config)

    agent_id, tenant_id = "a", "default"
    emb = await embedder.embed("Old")
    old = MemoryEntry(agent_id=agent_id, tenant_id=tenant_id, content="Old", embedding=emb)
    # Simulate old created_at (e.g. 2 days ago)
    old.created_at = _utc_now() - timedelta(days=2)
    await store.save(old)

    recent = MemoryEntry(agent_id=agent_id, tenant_id=tenant_id, content="Recent", embedding=emb)
    await store.save(recent)

    assert await store.count(agent_id, tenant_id) == 2
    result = await manager.run_maintenance(agent_id, tenant_id)
    assert result.error is None
    assert result.deleted_count == 1
    assert await store.count(agent_id, tenant_id) == 1


@pytest.mark.asyncio
async def test_lifecycle_run_for_agents() -> None:
    """run_maintenance_for_agents returns one result per (agent_id, tenant_id)."""
    store = InMemoryStore()
    config = MemoryConfig(max_entries=10, retention_days=365)
    manager = MemoryLifecycleManager(store, config)
    results = await manager.run_maintenance_for_agents([("agent1", "t1"), ("agent2", "t2")])
    assert len(results) == 2
    assert results[0].agent_id == "agent1" and results[0].tenant_id == "t1"
    assert results[1].agent_id == "agent2" and results[1].tenant_id == "t2"
