"""Integration tests for shared integration fixtures."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def isolation_probe_table(db_engine: AsyncEngine):
    """Create a reusable probe table for transaction-isolation validation."""
    table_name = "fixture_isolation_probe"
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    try:
        async with factory() as session:
            await session.execute(text(f"CREATE TABLE IF NOT EXISTS {table_name} (id INT PRIMARY KEY)"))
            await session.commit()
            await session.execute(text(f"TRUNCATE TABLE {table_name}"))
            await session.commit()
    except Exception as exc:
        pytest.skip(f"database connection unstable in current environment: {exc}")
    try:
        yield table_name
    finally:
        try:
            async with factory() as session:
                await session.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
                await session.commit()
        except Exception:
            # Teardown best effort: connection may already be dropped in unstable envs.
            pass


@pytest.mark.asyncio(loop_scope="module")
async def test_01_isolated_session_write_visible_in_current_test(
    isolated_session,
    isolation_probe_table: str,
) -> None:
    """Writes inside isolated_session should be visible before fixture teardown."""
    await isolated_session.execute(text(f"INSERT INTO {isolation_probe_table} (id) VALUES (1)"))
    row_count = await isolated_session.scalar(text(f"SELECT COUNT(*) FROM {isolation_probe_table}"))
    assert row_count == 1


@pytest.mark.asyncio(loop_scope="module")
async def test_02_isolated_session_rolls_back_after_previous_test(
    db_engine: AsyncEngine,
    isolation_probe_table: str,
) -> None:
    """Rows written in previous test must not leak into a fresh session."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        row_count = await session.scalar(text(f"SELECT COUNT(*) FROM {isolation_probe_table}"))
        assert row_count == 0
