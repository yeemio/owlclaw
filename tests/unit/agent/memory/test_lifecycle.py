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
    """Entries older than retention_days with access_count < 3 are deleted."""
    store = InMemoryStore()
    embedder = RandomEmbedder(dimensions=8, seed=42)
    config = MemoryConfig(max_entries=10000, retention_days=1)
    manager = MemoryLifecycleManager(store, config)

    agent_id, tenant_id = "a", "default"
    emb = await embedder.embed("Old")
    old = MemoryEntry(agent_id=agent_id, tenant_id=tenant_id, content="Old", embedding=emb)
    # Simulate old created_at (e.g. 2 days ago)
    old.created_at = _utc_now() - timedelta(days=2)
    old.access_count = 2
    await store.save(old)

    old_frequent = MemoryEntry(agent_id=agent_id, tenant_id=tenant_id, content="Old frequent", embedding=emb)
    old_frequent.created_at = _utc_now() - timedelta(days=2)
    old_frequent.access_count = 3
    await store.save(old_frequent)

    recent = MemoryEntry(agent_id=agent_id, tenant_id=tenant_id, content="Recent", embedding=emb)
    await store.save(recent)

    assert await store.count(agent_id, tenant_id) == 3
    result = await manager.run_maintenance(agent_id, tenant_id)
    assert result.error is None
    assert result.deleted_count == 1
    assert await store.count(agent_id, tenant_id) == 2


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


@pytest.mark.asyncio
async def test_lifecycle_archive_prioritizes_low_access_entries() -> None:
    store = InMemoryStore()
    embedder = RandomEmbedder(dimensions=8, seed=42)
    config = MemoryConfig(max_entries=2, retention_days=365)
    manager = MemoryLifecycleManager(store, config)

    agent_id, tenant_id = "a", "default"
    emb = await embedder.embed("Entry")

    oldest_high_access = MemoryEntry(agent_id=agent_id, tenant_id=tenant_id, content="old-high", embedding=emb)
    oldest_high_access.created_at = _utc_now() - timedelta(days=3)
    oldest_high_access.access_count = 10
    await store.save(oldest_high_access)

    old_low_access = MemoryEntry(agent_id=agent_id, tenant_id=tenant_id, content="old-low", embedding=emb)
    old_low_access.created_at = _utc_now() - timedelta(days=2)
    old_low_access.access_count = 0
    await store.save(old_low_access)

    recent_low_access = MemoryEntry(agent_id=agent_id, tenant_id=tenant_id, content="recent-low", embedding=emb)
    recent_low_access.created_at = _utc_now() - timedelta(days=1)
    recent_low_access.access_count = 0
    await store.save(recent_low_access)

    result = await manager.run_maintenance(agent_id, tenant_id)
    assert result.error is None
    assert result.archived_count == 1

    remaining = await store.list_entries(agent_id, tenant_id, order_created_asc=True, limit=10)
    remaining_contents = {entry.content for entry in remaining}
    assert "old-high" in remaining_contents
    assert "old-low" not in remaining_contents


@pytest.mark.asyncio
async def test_lifecycle_rejects_blank_agent_scope() -> None:
    store = InMemoryStore()
    config = MemoryConfig(max_entries=10, retention_days=365)
    manager = MemoryLifecycleManager(store, config)
    result = await manager.run_maintenance(" ", "default")
    assert result.error == "agent_id must not be empty"


@pytest.mark.asyncio
async def test_lifecycle_rejects_blank_tenant_scope() -> None:
    store = InMemoryStore()
    config = MemoryConfig(max_entries=10, retention_days=365)
    manager = MemoryLifecycleManager(store, config)
    result = await manager.run_maintenance("agent-a", " ")
    assert result.error == "tenant_id must not be empty"
