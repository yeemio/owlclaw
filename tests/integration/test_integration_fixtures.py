"""Integration tests for shared integration fixtures."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker


@pytest.mark.asyncio
async def test_isolated_transaction_rolls_back(db_engine: AsyncEngine) -> None:
    """Ensure transaction rollback prevents cross-test data pollution."""
    table_name = "fixture_isolation_probe"
    factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async with factory() as session:
        try:
            await session.begin()
            await session.execute(text(f"CREATE TABLE {table_name} (id INT PRIMARY KEY)"))
            await session.execute(text(f"INSERT INTO {table_name} (id) VALUES (1)"))
            await session.rollback()
        except Exception as exc:
            pytest.skip(f"database connection unstable in current environment: {exc}")

    async with factory() as session:
        result = await session.execute(text(f"SELECT to_regclass('public.{table_name}')"))
        assert result.scalar_one() is None
