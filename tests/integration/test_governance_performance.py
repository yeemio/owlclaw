"""Performance checks for governance latency and throughput targets."""

from __future__ import annotations

import asyncio
import os
import statistics
import subprocess
import time
from decimal import Decimal
from pathlib import Path

import pytest
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
        pytest.skip(f"Docker unavailable for governance performance test: {exc}")


@pytest.fixture(scope="module")
def _migrated_async_url(pg_container):
    project_root = Path(__file__).resolve().parents[2]
    sync_url = pg_container.get_connection_url()
    _run_migrations(sync_url, project_root)
    return _sync_url_to_async(sync_url)


@pytest.mark.asyncio
async def test_ledger_enqueue_p95_under_10ms(_migrated_async_url) -> None:
    engine = create_async_engine(_migrated_async_url, pool_pre_ping=True)
    try:
        ledger = Ledger(create_session_factory(engine), batch_size=2000, flush_interval=60.0)
        latencies_ms: list[float] = []
        for idx in range(300):
            start = time.perf_counter()
            await ledger.record_execution(
                tenant_id="perf-tenant",
                agent_id="perf-agent",
                run_id=f"enqueue-{idx}",
                capability_name="perf-cap",
                task_type="perf",
                input_params={"n": idx},
                output_result=None,
                decision_reasoning=None,
                execution_time_ms=1,
                llm_model="gpt-4o-mini",
                llm_tokens_input=1,
                llm_tokens_output=1,
                estimated_cost=Decimal("0.0001"),
                status="success",
            )
            latencies_ms.append((time.perf_counter() - start) * 1000.0)
        p95 = statistics.quantiles(latencies_ms, n=100)[94]
        assert p95 < 10.0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_ledger_query_p95_under_200ms(_migrated_async_url) -> None:
    engine = create_async_engine(_migrated_async_url, pool_pre_ping=True)
    try:
        ledger = Ledger(create_session_factory(engine), batch_size=1000, flush_interval=60.0)
        for idx in range(500):
            await ledger.record_execution(
                tenant_id="query-tenant",
                agent_id="query-agent",
                run_id=f"query-{idx}",
                capability_name=f"cap-{idx % 5}",
                task_type="perf",
                input_params={"n": idx},
                output_result=None,
                decision_reasoning=None,
                execution_time_ms=1,
                llm_model="gpt-4o-mini",
                llm_tokens_input=1,
                llm_tokens_output=1,
                estimated_cost=Decimal("0.0001"),
                status="success",
            )
        batch = []
        while not ledger._write_queue.empty():
            batch.append(ledger._write_queue.get_nowait())
        await ledger._flush_batch(batch)

        latencies_ms: list[float] = []
        for _ in range(30):
            start = time.perf_counter()
            records = await ledger.query_records(
                "query-tenant",
                LedgerQueryFilters(limit=50, order_by="created_at DESC"),
            )
            latencies_ms.append((time.perf_counter() - start) * 1000.0)
            assert len(records) <= 50
        p95 = statistics.quantiles(latencies_ms, n=100)[94]
        assert p95 < 200.0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_ledger_high_concurrency_supports_10plus_runs_per_minute(_migrated_async_url) -> None:
    engine = create_async_engine(_migrated_async_url, pool_pre_ping=True)
    try:
        ledger = Ledger(create_session_factory(engine), batch_size=2000, flush_interval=60.0)

        async def _enqueue(idx: int) -> None:
            await ledger.record_execution(
                tenant_id="concurrency-tenant",
                agent_id="concurrency-agent",
                run_id=f"concurrency-{idx}",
                capability_name="perf-cap",
                task_type="perf",
                input_params={"n": idx},
                output_result=None,
                decision_reasoning=None,
                execution_time_ms=1,
                llm_model="gpt-4o-mini",
                llm_tokens_input=1,
                llm_tokens_output=1,
                estimated_cost=Decimal("0.0001"),
                status="success",
            )

        run_count = 120
        start = time.perf_counter()
        await asyncio.gather(*(_enqueue(i) for i in range(run_count)))
        elapsed_seconds = time.perf_counter() - start
        runs_per_minute = run_count / max(elapsed_seconds, 1e-6) * 60.0
        assert runs_per_minute >= 10.0

        batch = []
        while not ledger._write_queue.empty():
            batch.append(ledger._write_queue.get_nowait())
        await ledger._flush_batch(batch)

        records = await ledger.query_records(
            "concurrency-tenant",
            LedgerQueryFilters(limit=200),
        )
        assert len(records) == run_count
    finally:
        await engine.dispose()
