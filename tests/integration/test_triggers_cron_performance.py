"""Performance-oriented integration tests for cron trigger subsystem (Task 15.2)."""

from __future__ import annotations

import asyncio
import statistics
import time
from typing import Any

import pytest

from owlclaw.triggers.cron import ConcurrencyController, PriorityScheduler

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_cron_performance_concurrency_100_tasks() -> None:
    controller = ConcurrencyController(max_concurrency=20)
    latencies: list[float] = []

    async def one_task(i: int) -> dict[str, Any]:
        start = time.perf_counter()
        await asyncio.sleep(0.005 + (i % 5) * 0.001)
        elapsed = time.perf_counter() - start
        latencies.append(elapsed)
        return {"i": i}

    started = time.perf_counter()
    results = await asyncio.gather(
        *[
            controller.execute_with_limit(
                f"t-{idx}",
                lambda idx=idx: one_task(idx),
            )
            for idx in range(100)
        ]
    )
    total_elapsed = time.perf_counter() - started

    assert len(results) == 100
    assert controller.get_active_count() == 0
    assert total_elapsed < 5.0
    assert statistics.quantiles(latencies, n=100)[94] < 0.2  # p95
    assert statistics.quantiles(latencies, n=100)[98] < 0.3  # p99


@pytest.mark.asyncio
async def test_cron_performance_priority_scheduler_ordering_and_throughput() -> None:
    scheduler = PriorityScheduler()
    executed: list[int] = []

    async def _task(priority: int) -> int:
        await asyncio.sleep(0)
        executed.append(priority)
        return priority

    for idx in range(120):
        await scheduler.schedule(
            task_id=f"job-{idx}",
            task_factory=lambda p=idx % 10: _task(p),
            priority=idx % 10,
        )

    started = time.perf_counter()
    out: list[int] = []
    for _ in range(120):
        result = await scheduler.execute_next()
        assert result is not None
        out.append(result)
    elapsed = time.perf_counter() - started

    assert len(out) == 120
    assert elapsed < 3.0
    assert out[0] >= out[-1]
