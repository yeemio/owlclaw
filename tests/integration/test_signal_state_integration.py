"""Integration tests for persistent signal state manager."""

from __future__ import annotations

import os

import pytest
from docker.errors import DockerException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from testcontainers.postgres import PostgresContainer

from owlclaw.db import Base, create_engine, create_session_factory
from owlclaw.triggers.signal import AgentStateManager, PendingInstruction, SignalSource
from owlclaw.triggers.signal.persistence import AgentControlStateORM, PendingInstructionORM  # noqa: F401

os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")
pytestmark = pytest.mark.integration


def _sync_url_to_async(url: str) -> str:
    value = url.strip()
    if value.startswith("postgresql+psycopg2://"):
        return "postgresql+asyncpg://" + value[len("postgresql+psycopg2://") :]
    if value.startswith("postgresql://"):
        return "postgresql+asyncpg://" + value[len("postgresql://") :]
    return value


@pytest.fixture(scope="module")
def pg_container() -> PostgresContainer:
    try:
        with PostgresContainer("pgvector/pgvector:pg16") as postgres:
            yield postgres
    except DockerException as exc:
        pytest.skip(f"Docker unavailable for integration test: {exc}")


@pytest.fixture(scope="module")
def async_url(pg_container: PostgresContainer) -> str:
    return _sync_url_to_async(pg_container.get_connection_url())


@pytest.fixture
async def db_engine(async_url: str) -> AsyncEngine:
    engine = create_engine(async_url, pool_size=5, max_overflow=5, pool_timeout=10)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_persistent_agent_state_manager_roundtrip(db_engine: AsyncEngine) -> None:
    session_factory = create_session_factory(db_engine)
    manager = AgentStateManager(max_pending_instructions=2, session_factory=session_factory)

    await manager.set_paused("agent-a", "tenant-1", True)
    state = await manager.get("agent-a", "tenant-1")
    assert state.paused is True

    await manager.add_instruction(
        "agent-a",
        "tenant-1",
        PendingInstruction.create(content="first", operator="op", source=SignalSource.CLI, ttl_seconds=3600),
    )
    await manager.add_instruction(
        "agent-a",
        "tenant-1",
        PendingInstruction.create(content="second", operator="op", source=SignalSource.CLI, ttl_seconds=3600),
    )
    await manager.add_instruction(
        "agent-a",
        "tenant-1",
        PendingInstruction.create(content="third", operator="op", source=SignalSource.CLI, ttl_seconds=3600),
    )

    consumed = await manager.consume_instructions("agent-a", "tenant-1")
    assert [item.content for item in consumed] == ["second", "third"]

    cleaned = await manager.cleanup_expired_instructions("agent-a", "tenant-1")
    assert cleaned >= 0
