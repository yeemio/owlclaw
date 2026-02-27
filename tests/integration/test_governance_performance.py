"""Performance checks for governance latency and throughput targets."""

from __future__ import annotations

import asyncio
import os
import statistics
import time
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from owlclaw.db.session import create_session_factory
from owlclaw.governance.ledger import Ledger, LedgerQueryFilters

pytestmark = pytest.mark.integration

IS_CI = os.getenv("CI", "").lower() == "true"
ENQUEUE_P95_MS = 25.0 if IS_CI else 10.0
QUERY_P95_MS = 500.0 if IS_CI else 200.0


@pytest.mark.asyncio
async def test_ledger_enqueue_p95_under_10ms(
    db_engine: AsyncEngine,
    run_migrations: None,
) -> None:
    try:
        ledger = Ledger(create_session_factory(db_engine), batch_size=2000, flush_interval=60.0)
        latencies_ms: list[float] = []
        for idx in range(120):
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
        assert p95 < ENQUEUE_P95_MS
    finally:
        pass


@pytest.mark.asyncio
async def test_ledger_query_p95_under_200ms(
    db_engine: AsyncEngine,
    run_migrations: None,
) -> None:
    try:
        ledger = Ledger(create_session_factory(db_engine), batch_size=1000, flush_interval=60.0)
        for idx in range(200):
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
        for _ in range(15):
            start = time.perf_counter()
            records = await ledger.query_records(
                "query-tenant",
                LedgerQueryFilters(limit=50, order_by="created_at DESC"),
            )
            latencies_ms.append((time.perf_counter() - start) * 1000.0)
            assert len(records) <= 50
        p95 = statistics.quantiles(latencies_ms, n=100)[94]
        assert p95 < QUERY_P95_MS
    finally:
        pass


@pytest.mark.asyncio
async def test_ledger_high_concurrency_supports_10plus_runs_per_minute(
    db_engine: AsyncEngine,
    run_migrations: None,
) -> None:
    try:
        ledger = Ledger(create_session_factory(db_engine), batch_size=2000, flush_interval=60.0)

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
        pass
