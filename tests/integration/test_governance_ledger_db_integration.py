"""Integration tests for governance ledger migration and tenant isolation."""

from __future__ import annotations

import os
import subprocess
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer

from owlclaw.db.session import create_session_factory
from owlclaw.governance.ledger import Ledger, LedgerQueryFilters

os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")

pytestmark = pytest.mark.integration


def _sync_url_to_async(url: str) -> str:
    value = url.strip()
    if value.startswith("postgresql+psycopg2://"):
        return "postgresql+asyncpg://" + value[len("postgresql+psycopg2://") :]
    if value.startswith("postgresql://"):
        return "postgresql+asyncpg://" + value[len("postgresql://") :]
    return value


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
    try:
        with PostgresContainer("pgvector/pgvector:pg16") as postgres:
            yield postgres
    except Exception as exc:
        pytest.skip(f"Docker unavailable for governance integration test: {exc}")


@pytest.fixture(scope="module")
def _migrated_async_url(pg_container):
    project_root = Path(__file__).resolve().parents[2]
    sync_url = pg_container.get_connection_url()
    _run_migrations(sync_url, project_root)
    return _sync_url_to_async(sync_url)


@pytest.mark.asyncio
async def test_ledger_migration_creates_expected_table_shape(_migrated_async_url) -> None:
    engine = create_async_engine(_migrated_async_url, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            table_exists = await conn.scalar(
                text(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = 'public' AND table_name = 'ledger_records'
                    )
                    """
                )
            )
            assert table_exists is True

            column_rows = await conn.execute(
                text(
                    """
                    SELECT column_name, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'ledger_records'
                    """
                )
            )
            columns = {name: nullable for name, nullable in column_rows}
            assert "tenant_id" in columns
            assert columns["tenant_id"] == "NO"
            assert "agent_id" in columns
            assert "run_id" in columns
            assert "capability_name" in columns
            assert "execution_time_ms" in columns
            assert "estimated_cost" in columns
            assert "created_at" in columns
            required_not_null = [
                "tenant_id",
                "agent_id",
                "run_id",
                "capability_name",
                "task_type",
                "input_params",
                "execution_time_ms",
                "llm_model",
                "llm_tokens_input",
                "llm_tokens_output",
                "estimated_cost",
                "status",
                "created_at",
            ]
            for field in required_not_null:
                assert columns[field] == "NO"

            index_rows = await conn.execute(
                text(
                    """
                    SELECT indexname
                    FROM pg_indexes
                    WHERE schemaname = 'public' AND tablename = 'ledger_records'
                    """
                )
            )
            index_names = {name for (name,) in index_rows}
            assert "idx_ledger_tenant_agent" in index_names
            assert "idx_ledger_tenant_capability" in index_names
            assert "idx_ledger_tenant_created" in index_names
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_ledger_query_isolates_tenants(_migrated_async_url) -> None:
    engine = create_async_engine(_migrated_async_url, pool_pre_ping=True)
    try:
        session_factory = create_session_factory(engine)
        ledger = Ledger(session_factory, batch_size=10, flush_interval=1.0)
        async with session_factory() as session:
            await session.execute(
                text(
                    """
                    DELETE FROM ledger_records
                    WHERE tenant_id IN ('tenant-a', 'tenant-b')
                    """
                )
            )
            await session.commit()

        await ledger.record_execution(
            tenant_id="tenant-a",
            agent_id="agent1",
            run_id="run-a",
            capability_name="cap-A",
            task_type="task",
            input_params={"x": 1},
            output_result={"ok": True},
            decision_reasoning="a",
            execution_time_ms=10,
            llm_model="gpt-4o-mini",
            llm_tokens_input=10,
            llm_tokens_output=5,
            estimated_cost=Decimal("0.0100"),
            status="success",
        )
        await ledger.record_execution(
            tenant_id="tenant-b",
            agent_id="agent1",
            run_id="run-b",
            capability_name="cap-B",
            task_type="task",
            input_params={"x": 2},
            output_result={"ok": True},
            decision_reasoning="b",
            execution_time_ms=12,
            llm_model="gpt-4o-mini",
            llm_tokens_input=12,
            llm_tokens_output=6,
            estimated_cost=Decimal("0.0200"),
            status="success",
        )

        batch = []
        while not ledger._write_queue.empty():
            batch.append(ledger._write_queue.get_nowait())
        await ledger._flush_batch(batch)

        result_a = await ledger.query_records("tenant-a", LedgerQueryFilters())
        result_b = await ledger.query_records("tenant-b", LedgerQueryFilters())

        assert len(result_a) == 1
        assert result_a[0].tenant_id == "tenant-a"
        assert result_a[0].capability_name == "cap-A"

        assert len(result_b) == 1
        assert result_b[0].tenant_id == "tenant-b"
        assert result_b[0].capability_name == "cap-B"
    finally:
        await engine.dispose()
