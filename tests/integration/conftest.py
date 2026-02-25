"""Integration test defaults."""

from __future__ import annotations

import os

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

pytestmark = pytest.mark.requires_postgres


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Apply default PostgreSQL requirement marker to all integration tests."""
    for item in items:
        item.add_marker(pytest.mark.requires_postgres)


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def db_engine() -> AsyncEngine:
    """Module-scoped async DB engine for integration tests."""
    db_url = os.getenv("OWLCLAW_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not db_url:
        pytest.skip("DATABASE_URL/OWLCLAW_DATABASE_URL is not set")
    engine = create_async_engine(db_url, future=True)
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
    try:
        command.upgrade(cfg, "head")
    except Exception as exc:
        pytest.skip(f"database migration unavailable in current environment: {exc}")


@pytest_asyncio.fixture(loop_scope="module")
async def isolated_session(db_engine: AsyncEngine, run_migrations: None):
    """Per-test isolated session with rollback."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        await session.begin()
        try:
            yield session
        finally:
            await session.rollback()
