"""Unit tests for PgVectorStore input/schema validation."""

from __future__ import annotations

import pytest

from owlclaw.agent.memory.models import MemoryEntry
from owlclaw.agent.memory.store_pgvector import PgVectorStore


class _NeverSessionFactory:
    def __call__(self):
        raise AssertionError("session factory should not be called in validation failures")


def test_pgvector_store_rejects_schema_dimension_mismatch() -> None:
    with pytest.raises(ValueError, match="does not match"):
        PgVectorStore(
            session_factory=_NeverSessionFactory(),  # type: ignore[arg-type]
            embedding_dimensions=3072,
        )


@pytest.mark.asyncio
async def test_pgvector_store_save_rejects_invalid_embedding_length() -> None:
    store = PgVectorStore(
        session_factory=_NeverSessionFactory(),  # type: ignore[arg-type]
        embedding_dimensions=1536,
    )
    entry = MemoryEntry(agent_id="a", tenant_id="default", content="x", embedding=[0.1, 0.2])

    with pytest.raises(ValueError, match="entry.embedding length must be 1536"):
        await store.save(entry)


@pytest.mark.asyncio
async def test_pgvector_store_search_rejects_invalid_query_embedding_length() -> None:
    store = PgVectorStore(
        session_factory=_NeverSessionFactory(),  # type: ignore[arg-type]
        embedding_dimensions=1536,
    )

    with pytest.raises(ValueError, match="query_embedding length must be 1536"):
        await store.search(
            agent_id="a",
            tenant_id="default",
            query_embedding=[0.1, 0.2],
        )

