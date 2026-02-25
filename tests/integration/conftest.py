"""Integration test defaults."""

from __future__ import annotations

import os

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

pytestmark = pytest.mark.requires_postgres


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Apply default PostgreSQL requirement marker to all integration tests."""
    for item in items:
        item.add_marker(pytest.mark.requires_postgres)


@pytest_asyncio.fixture(scope="module")
async def db_engine() -> AsyncEngine:
    """Module-scoped async DB engine for integration tests."""
    db_url = os.getenv("OWLCLAW_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not db_url:
        pytest.skip("DATABASE_URL/OWLCLAW_DATABASE_URL is not set")
    # NullPool avoids cross-event-loop connection reuse with asyncpg on Windows.
    engine = create_async_engine(db_url, future=True, poolclass=NullPool)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture(scope="session")
def run_migrations() -> None:
    """Best-effort migration to latest schema for integration test sessions."""
    db_url = os.getenv("OWLCLAW_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not db_url:
        pytest.skip("DATABASE_URL/OWLCLAW_DATABASE_URL is not set")
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(cfg, "head")


@pytest_asyncio.fixture
async def isolated_session(db_engine: AsyncEngine, run_migrations: None):
    """Per-test isolated session with rollback."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        await session.begin()
        try:
            yield session
        finally:
            if session.in_transaction():
                await session.rollback()
