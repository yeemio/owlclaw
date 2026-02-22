"""Unit tests for SnapshotBuilder."""

import pytest

from owlclaw.agent.memory import InMemoryStore, MemoryEntry, RandomEmbedder
from owlclaw.agent.memory.snapshot import SnapshotBuilder


@pytest.mark.asyncio
async def test_snapshot_build_semantic_and_recent() -> None:
    """Snapshot combines semantic (trigger) + recent + dedup."""
    store = InMemoryStore()
    embedder = RandomEmbedder(dimensions=8, seed=42)
    builder = SnapshotBuilder(store, embedder)
    agent_id, tenant_id = "a", "default"

    # One entry that will match semantic; one that will be recent
    for content in ["Deploy pipeline failed", "User asked for report"]:
        emb = await embedder.embed(content)
        await store.save(MemoryEntry(agent_id=agent_id, tenant_id=tenant_id, content=content, embedding=emb))

    snap = await builder.build(
        agent_id, tenant_id,
        trigger_event="pipeline deployment",
        focus=None,
        max_tokens=500,
        semantic_limit=2,
        recent_hours=24,
        recent_limit=2,
    )
    assert "Long-term memory" in snap.prompt_fragment
    assert len(snap.entry_ids) >= 1
    assert "Deploy" in snap.prompt_fragment or "report" in snap.prompt_fragment


@pytest.mark.asyncio
async def test_snapshot_pinned_tag() -> None:
    """Pinned tag recall is included."""
    store = InMemoryStore()
    embedder = RandomEmbedder(dimensions=8, seed=42)
    builder = SnapshotBuilder(store, embedder)
    agent_id, tenant_id = "a", "default"

    emb = await embedder.embed("Pinned rule: always confirm")
    await store.save(MemoryEntry(
        agent_id=agent_id, tenant_id=tenant_id,
        content="Pinned rule: always confirm",
        embedding=emb,
        tags=["pinned"],
    ))

    snap = await builder.build(
        agent_id, tenant_id,
        trigger_event="other",
        focus=None,
        max_tokens=500,
        pinned_limit=5,
    )
    assert "Long-term memory" in snap.prompt_fragment
    assert "always confirm" in snap.prompt_fragment or "Pinned" in snap.prompt_fragment
    assert len(snap.entry_ids) >= 1


@pytest.mark.asyncio
async def test_snapshot_dedup_and_token_trim() -> None:
    """Dedup by id; token trim respects max_tokens."""
    store = InMemoryStore()
    embedder = RandomEmbedder(dimensions=8, seed=42)
    builder = SnapshotBuilder(store, embedder)
    agent_id, tenant_id = "a", "default"

    # One entry that can appear in both semantic and recent
    emb = await embedder.embed("Only one")
    entry = MemoryEntry(agent_id=agent_id, tenant_id=tenant_id, content="Only one", embedding=emb)
    await store.save(entry)

    snap = await builder.build(
        agent_id, tenant_id,
        trigger_event="Only one",
        focus=None,
        max_tokens=500,
    )
    assert snap.entry_ids.count(entry.id) <= 1
    assert len(snap.prompt_fragment) > 0


class _CaptureEmbedder:
    def __init__(self) -> None:
        self.last_text = ""

    async def embed(self, text: str) -> list[float]:
        self.last_text = text
        return [0.1, 0.2]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2] for _ in texts]

    @property
    def dimensions(self) -> int:
        return 2


@pytest.mark.asyncio
async def test_snapshot_build_includes_focus_in_semantic_query() -> None:
    """Snapshot semantic query should include focus context when provided."""
    store = InMemoryStore()
    embedder = _CaptureEmbedder()
    builder = SnapshotBuilder(store, embedder)

    await builder.build(
        agent_id="a",
        tenant_id="default",
        trigger_event="cron: hourly_check",
        focus="risk-control",
        max_tokens=100,
    )

    assert "cron: hourly_check" in embedder.last_text
    assert "focus: risk-control" in embedder.last_text
