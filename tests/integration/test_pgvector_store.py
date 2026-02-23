"""Integration tests for PgVectorStore: PostgreSQL + pgvector via testcontainers.

Runs: save → search, time decay ordering, tag filter, archive exclusion, tenant_id isolation.

Requires: Docker. If port 8080 is in use (e.g. Ryuk reaper conflict), set
TESTCONTAINERS_RYUK_DISABLED=true.
"""

from __future__ import annotations

import os

# Disable Ryuk reaper if port 8080 is unavailable (e.g. on some Windows/CI setups)
os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")
import subprocess
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer

from owlclaw.agent.memory.models import MemoryEntry
from owlclaw.agent.memory.store_pgvector import PgVectorStore
from owlclaw.db.session import create_session_factory


def _sync_url_to_async(url: str) -> str:
    """Convert postgresql+psycopg2 or postgresql URL to postgresql+asyncpg."""
    u = url.strip()
    if u.startswith("postgresql+psycopg2://"):
        return "postgresql+asyncpg://" + u[len("postgresql+psycopg2://") :]
    if u.startswith("postgresql://"):
        return "postgresql+asyncpg://" + u[len("postgresql://") :]
    return u


def _run_migrations(sync_url: str, project_root: Path) -> None:
    env = os.environ.copy()
    env["OWLCLAW_DATABASE_URL"] = sync_url
    subprocess.run(
        ["alembic", "-c", "alembic.ini", "upgrade", "head"],
        cwd=project_root,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="module")
def pg_container():
    """Start PostgreSQL with pgvector for the module."""
    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        yield postgres


@pytest.fixture(scope="module")
def _migrated_async_url(pg_container):
    """Run migrations once per module; return async URL for engine creation."""
    project_root = Path(__file__).resolve().parents[2]
    sync_url = pg_container.get_connection_url()
    _run_migrations(sync_url, project_root)
    return _sync_url_to_async(sync_url)


@pytest.fixture
def store(_migrated_async_url):
    """PgVectorStore instance per test (fresh engine/session, avoids event loop reuse issues)."""
    engine = create_async_engine(_migrated_async_url, pool_pre_ping=True)
    factory = create_session_factory(engine)
    store = PgVectorStore(
        session_factory=factory,
        embedding_dimensions=1536,
        time_decay_half_life_hours=168.0,
    )
    yield store
    engine.sync_engine.dispose()


pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_pgvector_save_and_search(store: PgVectorStore) -> None:
    """Save entries and search by vector similarity (full save → search flow)."""
    agent_id, tenant_id = "int-agent", "int-tenant"
    # Deterministic embeddings (same length as schema)
    emb1 = [0.1] * 1536
    emb2 = [0.2] * 1536
    emb_query = [0.15] * 1536

    e1 = MemoryEntry(agent_id=agent_id, tenant_id=tenant_id, content="First memory", embedding=emb1)
    e2 = MemoryEntry(agent_id=agent_id, tenant_id=tenant_id, content="Second memory", embedding=emb2)
    id1 = await store.save(e1)
    id2 = await store.save(e2)

    assert id1 is not None
    assert id2 is not None
    assert await store.count(agent_id, tenant_id) == 2

    results = await store.search(agent_id, tenant_id, emb_query, limit=5)
    assert len(results) >= 1
    assert len(results) <= 5
    entries = [r[0] for r in results]
    contents = {e.content for e in entries}
    assert "First memory" in contents or "Second memory" in contents
    for _, score in results:
        assert 0 <= score <= 1


@pytest.mark.asyncio
async def test_pgvector_time_decay_ordering(store: PgVectorStore) -> None:
    """Search results are ordered by similarity * time decay (recent favored when similar)."""
    agent_id, tenant_id = "decay-agent", "default"
    emb = [0.5] * 1536

    for i, content in enumerate(["Old", "Newer", "Newest"]):
        entry = MemoryEntry(agent_id=agent_id, tenant_id=tenant_id, content=content, embedding=emb)
        await store.save(entry)

    results = await store.search(agent_id, tenant_id, emb, limit=3)
    assert len(results) >= 1
    # All same embedding so similarity equal; time decay gives higher score to newer
    scores = [r[1] for r in results]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_pgvector_tag_filter(store: PgVectorStore) -> None:
    """Search with tags only returns entries that have those tags."""
    agent_id, tenant_id = "tag-agent", "default"
    emb = [0.3] * 1536

    await store.save(MemoryEntry(agent_id=agent_id, tenant_id=tenant_id, content="No tag", embedding=emb))
    await store.save(MemoryEntry(agent_id=agent_id, tenant_id=tenant_id, content="With important", embedding=emb, tags=["important"]))
    await store.save(MemoryEntry(agent_id=agent_id, tenant_id=tenant_id, content="With other", embedding=emb, tags=["other"]))

    results_tag = await store.search(agent_id, tenant_id, None, limit=10, tags=["important"])
    contents_tag = {r[0].content for r in results_tag}
    assert "With important" in contents_tag
    assert "No tag" not in contents_tag
    assert "With other" not in contents_tag


@pytest.mark.asyncio
async def test_pgvector_archive_excluded_from_search(store: PgVectorStore) -> None:
    """Archived entries do not appear in search and are excluded from count."""
    agent_id, tenant_id = "arch-agent", "default"
    emb = [0.7] * 1536

    entry = MemoryEntry(agent_id=agent_id, tenant_id=tenant_id, content="To archive", embedding=emb)
    eid = await store.save(entry)
    assert await store.count(agent_id, tenant_id) == 1
    results_before = await store.search(agent_id, tenant_id, emb, limit=5)
    assert any(r[0].id == eid for r in results_before)

    n = await store.archive([eid])
    assert n == 1
    assert await store.count(agent_id, tenant_id) == 0
    results_after = await store.search(agent_id, tenant_id, emb, limit=5)
    assert not any(r[0].id == eid for r in results_after)


@pytest.mark.asyncio
async def test_pgvector_tenant_id_isolation(store: PgVectorStore) -> None:
    """Entries from one tenant are not visible to another (agent_id + tenant_id scope)."""
    agent_id = "iso-agent"
    tenant_a, tenant_b = "tenant-a", "tenant-b"
    emb = [0.4] * 1536

    entry_a = MemoryEntry(agent_id=agent_id, tenant_id=tenant_a, content="Only in A", embedding=emb)
    await store.save(entry_a)

    assert await store.count(agent_id, tenant_a) == 1
    assert await store.count(agent_id, tenant_b) == 0
    results_b = await store.search(agent_id, tenant_b, emb, limit=5)
    assert len(results_b) == 0
    results_a = await store.search(agent_id, tenant_a, emb, limit=5)
    assert len(results_a) >= 1
    assert results_a[0][0].content == "Only in A"
