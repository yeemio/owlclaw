"""Integration tests for owlclaw.db core infrastructure."""

from __future__ import annotations

import asyncio
import os
from uuid import uuid4

import pytest
from docker.errors import DockerException
from sqlalchemy import String, func, select, text
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm import Mapped, mapped_column
from testcontainers.postgres import PostgresContainer

from owlclaw.db import Base, create_engine, get_session

# Disable Ryuk reaper for Windows/CI environments where port 8080 is occupied.
os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")


class _DbCoreTestItem(Base):
    """Temporary integration-test table for db core checks."""

    __tablename__ = "db_core_test_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    content: Mapped[str] = mapped_column(String(255), nullable=False)


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
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_db_core_connect_and_query(db_engine: AsyncEngine) -> None:
    """Engine and session can connect and execute SQL."""
    async with get_session(db_engine) as session:
        value = await session.scalar(select(text("1")))
    assert value == 1


@pytest.mark.asyncio
async def test_db_core_create_insert_and_read(db_engine: AsyncEngine) -> None:
    """Can create rows and query rows through get_session context manager."""
    item = _DbCoreTestItem(content="hello-db-core")
    async with get_session(db_engine) as session:
        session.add(item)

    async with get_session(db_engine) as session:
        rows = (await session.execute(select(_DbCoreTestItem))).scalars().all()
    assert len(rows) == 1
    assert rows[0].content == "hello-db-core"
    assert rows[0].tenant_id == "default"


@pytest.mark.asyncio
async def test_db_core_pgvector_extension_compatibility(db_engine: AsyncEngine) -> None:
    """pgvector extension is available and enabled in test database."""
    async with get_session(db_engine) as session:
        ext = await session.scalar(
            select(text("extname")).select_from(text("pg_extension")).where(text("extname = 'vector'"))
        )
    assert ext == "vector"


@pytest.mark.asyncio
async def test_db_core_connection_pool_concurrency(db_engine: AsyncEngine) -> None:
    """Session helper works under concurrent writes/reads with pooled connections."""

    async def _insert_one(idx: int) -> None:
        async with get_session(db_engine) as session:
            session.add(_DbCoreTestItem(content=f"item-{idx}"))

    await asyncio.gather(*[_insert_one(i) for i in range(20)])

    async with get_session(db_engine) as session:
        count = await session.scalar(select(func.count()).select_from(_DbCoreTestItem))
    assert count == 20
