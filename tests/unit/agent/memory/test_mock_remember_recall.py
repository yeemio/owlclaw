"""Verify remember → recall flow in mock_mode (InMemoryStore + RandomEmbedder)."""

import pytest

from owlclaw.agent.memory import InMemoryStore, MemoryEntry, RandomEmbedder


@pytest.mark.asyncio
async def test_remember_recall_mock_mode_flow() -> None:
    """Save entries with RandomEmbedder, then search; full mock remember→recall path works."""
    store = InMemoryStore()
    embedder = RandomEmbedder(dimensions=8, seed=42)
    agent_id = "test-agent"
    tenant_id = "default"

    # "Remember" three items (simulate: embed + save)
    texts = ["User prefers dark mode", "Meeting at 3pm Friday", "API key stored in vault"]
    ids = []
    for t in texts:
        emb = await embedder.embed(t)
        entry = MemoryEntry(agent_id=agent_id, tenant_id=tenant_id, content=t, embedding=emb)
        uid = await store.save(entry)
        ids.append(uid)

    assert len(ids) == 3
    assert await store.count(agent_id, tenant_id) == 3

    # "Recall" with a query (embed query + search)
    query = "when is the meeting"
    query_emb = await embedder.embed(query)
    results = await store.search(agent_id, tenant_id, query_emb, limit=3)
    assert len(results) >= 1
    entries_and_scores = results
    for entry, score in entries_and_scores:
        assert entry.agent_id == agent_id
        assert entry.tenant_id == tenant_id
        assert entry.content in texts
        assert 0 <= score <= 1

    # get_recent returns by time
    recent = await store.get_recent(agent_id, tenant_id, hours=24, limit=2)
    assert len(recent) == 2
    assert all(e.agent_id == agent_id and e.tenant_id == tenant_id for e in recent)

    # archive one, then count excludes it
    await store.archive([ids[0]])
    assert await store.count(agent_id, tenant_id) == 2
    search_after = await store.search(agent_id, tenant_id, query_emb, limit=5)
    assert len(search_after) == 2

    # delete one
    await store.delete([ids[1]])
    assert await store.count(agent_id, tenant_id) == 1
