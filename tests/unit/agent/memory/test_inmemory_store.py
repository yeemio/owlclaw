"""Unit tests for InMemoryStore — mock_mode full flow (save, search, get_recent, archive, delete, count, update_access)."""

from __future__ import annotations

import pytest

from owlclaw.agent.memory import InMemoryStore, MemoryEntry, RandomEmbedder


@pytest.mark.asyncio
async def test_inmemory_save_and_count() -> None:
    """Save entries and count by agent/tenant."""
    store = InMemoryStore()
    embedder = RandomEmbedder(dimensions=8, seed=42)
    agent_id, tenant_id = "agent-1", "tenant-1"

    for content in ["First", "Second", "Third"]:
        emb = await embedder.embed(content)
        entry = MemoryEntry(agent_id=agent_id, tenant_id=tenant_id, content=content, embedding=emb)
        await store.save(entry)

    assert await store.count(agent_id, tenant_id) == 3
    assert await store.count("other", tenant_id) == 0


@pytest.mark.asyncio
async def test_inmemory_search_by_similarity() -> None:
    """Search returns entries ordered by similarity score."""
    store = InMemoryStore()
    embedder = RandomEmbedder(dimensions=8, seed=42)
    agent_id, tenant_id = "a", "default"

    texts = ["Meeting on Friday", "API key in vault", "User likes dark mode"]
    for t in texts:
        emb = await embedder.embed(t)
        await store.save(MemoryEntry(agent_id=agent_id, tenant_id=tenant_id, content=t, embedding=emb))

    query_emb = await embedder.embed("when is the meeting")
    results = await store.search(agent_id, tenant_id, query_emb, limit=2)
    assert len(results) <= 2
    for entry, score in results:
        assert entry.agent_id == agent_id
        assert entry.tenant_id == tenant_id
        assert 0 <= score <= 1


@pytest.mark.asyncio
async def test_inmemory_get_recent() -> None:
    """get_recent returns entries in time window, newest first."""
    store = InMemoryStore()
    embedder = RandomEmbedder(dimensions=8, seed=42)
    agent_id, tenant_id = "a", "default"

    for content in ["Old", "Newer", "Newest"]:
        emb = await embedder.embed(content)
        await store.save(MemoryEntry(agent_id=agent_id, tenant_id=tenant_id, content=content, embedding=emb))

    recent = await store.get_recent(agent_id, tenant_id, hours=24, limit=2)
    assert len(recent) == 2
    assert all(e.agent_id == agent_id and e.tenant_id == tenant_id for e in recent)


@pytest.mark.asyncio
async def test_inmemory_archive_excludes_from_count_and_search() -> None:
    """Archived entries are excluded from count and search."""
    store = InMemoryStore()
    embedder = RandomEmbedder(dimensions=8, seed=42)
    agent_id, tenant_id = "a", "default"

    emb = await embedder.embed("To archive")
    entry = MemoryEntry(agent_id=agent_id, tenant_id=tenant_id, content="To archive", embedding=emb)
    eid = await store.save(entry)

    assert await store.count(agent_id, tenant_id) == 1
    n = await store.archive([eid])
    assert n == 1
    assert await store.count(agent_id, tenant_id) == 0
    results = await store.search(agent_id, tenant_id, await embedder.embed("archive"), limit=5)
    assert len(results) == 0


@pytest.mark.asyncio
async def test_inmemory_delete_removes_entries() -> None:
    """Delete removes entries permanently."""
    store = InMemoryStore()
    embedder = RandomEmbedder(dimensions=8, seed=42)
    agent_id, tenant_id = "a", "default"

    emb = await embedder.embed("To delete")
    eid = await store.save(MemoryEntry(agent_id=agent_id, tenant_id=tenant_id, content="To delete", embedding=emb))
    assert await store.count(agent_id, tenant_id) == 1

    n = await store.delete([eid])
    assert n == 1
    assert await store.count(agent_id, tenant_id) == 0


@pytest.mark.asyncio
async def test_inmemory_update_access() -> None:
    """update_access updates accessed_at and increments access_count."""
    store = InMemoryStore()
    embedder = RandomEmbedder(dimensions=8, seed=42)
    agent_id, tenant_id = "a", "default"

    emb = await embedder.embed("Target")
    eid = await store.save(MemoryEntry(agent_id=agent_id, tenant_id=tenant_id, content="Target", embedding=emb))

    results = await store.search(agent_id, tenant_id, emb, limit=1)
    assert len(results) == 1
    entry_before = results[0][0]
    assert entry_before.access_count == 0
    assert entry_before.accessed_at is None

    await store.update_access(agent_id, tenant_id, [eid])

    results2 = await store.search(agent_id, tenant_id, emb, limit=1)
    assert len(results2) == 1
    entry_after = results2[0][0]
    assert entry_after.access_count == 1
    assert entry_after.accessed_at is not None
