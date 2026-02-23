"""Unit tests for cron performance helpers (Task 12)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from owlclaw.triggers.cron import (
    BatchOperations,
    ConcurrencyController,
    CronCache,
    CronTriggerRegistry,
    PriorityScheduler,
)


@pytest.mark.asyncio
async def test_concurrency_controller_limits_parallelism() -> None:
    controller = ConcurrencyController(max_concurrency=2)
    active = 0
    peak_active = 0
    lock = asyncio.Lock()

    async def build_task() -> str:
        nonlocal active, peak_active
        async with lock:
            active += 1
            peak_active = max(peak_active, active)
        await asyncio.sleep(0.02)
        async with lock:
            active -= 1
        return "ok"

    results = await asyncio.gather(
        controller.execute_with_limit("t1", build_task),
        controller.execute_with_limit("t2", build_task),
        controller.execute_with_limit("t3", build_task),
        controller.execute_with_limit("t4", build_task),
    )
    assert results == ["ok", "ok", "ok", "ok"]
    assert peak_active <= 2
    assert controller.get_active_count() == 0


@pytest.mark.asyncio
async def test_concurrency_controller_wait_all_waits_for_pending_tasks() -> None:
    controller = ConcurrencyController(max_concurrency=1)
    gate = asyncio.Event()

    async def blocked() -> str:
        await gate.wait()
        return "done"

    task = asyncio.create_task(controller.execute_with_limit("blocked", blocked))
    await asyncio.sleep(0.01)
    assert controller.get_active_count() == 1
    gate.set()
    await controller.wait_all()
    assert await task == "done"
    assert controller.get_active_count() == 0


@pytest.mark.asyncio
async def test_priority_scheduler_executes_higher_priority_first() -> None:
    scheduler = PriorityScheduler()
    order: list[str] = []

    async def low() -> str:
        order.append("low")
        return "low"

    async def high() -> str:
        order.append("high")
        return "high"

    async def mid() -> str:
        order.append("mid")
        return "mid"

    await scheduler.schedule(task_id="a", task_factory=low, priority=1)
    await scheduler.schedule(task_id="b", task_factory=high, priority=10)
    await scheduler.schedule(task_id="c", task_factory=mid, priority=5)

    assert await scheduler.execute_next() == "high"
    assert await scheduler.execute_next() == "mid"
    assert await scheduler.execute_next() == "low"
    assert await scheduler.execute_next() is None
    assert order == ["high", "mid", "low"]


def test_cron_cache_records_and_stats_ttl() -> None:
    cache = CronCache(stats_ttl_seconds=60, execution_cache_size=3)
    cache.record_execution("job", {"run_id": "r1"})
    cache.record_execution("job", {"run_id": "r2"})
    cache.record_execution("job", {"run_id": "r3"})
    cache.record_execution("job", {"run_id": "r4"})

    records = cache.get_execution_records("job", limit=3)
    assert [record["run_id"] for record in records] == ["r4", "r3", "r2"]

    cache.set_stats("job", {"success_rate": 0.8}, ttl_seconds=30)
    assert cache.get_stats("job") == {"success_rate": 0.8}

    expires_in_past = datetime.now(timezone.utc) - timedelta(seconds=1)
    cache._stats_cache["job"] = (expires_in_past, {"success_rate": 0.8})
    assert cache.get_stats("job") is None


def test_cron_cache_next_trigger_time_and_invalidate() -> None:
    cache = CronCache()
    base = datetime(2026, 2, 23, 10, 0, 0, tzinfo=timezone.utc)
    next_run = cache.next_trigger_time("0 * * * *", base_time=base)
    assert next_run is not None
    assert next_run.startswith("2026-02-23T11:00:00")

    assert cache.next_trigger_time("invalid cron", base_time=base) is None

    cache.record_execution("job", {"run_id": "r1"})
    cache.set_stats("job", {"ok": True})
    cache.invalidate("job")
    assert cache.get_execution_records("job") == []
    assert cache.get_stats("job") is None


@pytest.mark.asyncio
async def test_batch_operations_record_with_single_record_api() -> None:
    batch = BatchOperations(batch_size=2)
    ledger = MagicMock()
    ledger.record_execution = AsyncMock()
    records = [
        {"tenant_id": "t1", "run_id": "r1"},
        {"tenant_id": "t1", "run_id": "r2"},
        {"tenant_id": "t1", "run_id": "r3"},
    ]

    written = await batch.batch_record_executions(ledger=ledger, records=records)
    assert written == 3
    assert ledger.record_execution.await_count == 3


@pytest.mark.asyncio
async def test_batch_operations_record_with_batch_api() -> None:
    batch = BatchOperations(batch_size=2)
    ledger = MagicMock()
    ledger.batch_record_executions = AsyncMock()
    records = [{"run_id": "r1"}, {"run_id": "r2"}, {"run_id": "r3"}]

    written = await batch.batch_record_executions(ledger=ledger, records=records)
    assert written == 3
    assert ledger.batch_record_executions.await_count == 2


@pytest.mark.asyncio
async def test_batch_operations_query_preserves_order() -> None:
    batch = BatchOperations(batch_size=2)
    ledger = MagicMock()
    ledger.query_records = AsyncMock(side_effect=[["a"], ["b"], ["c"]])
    filters_list: list[Any] = ["f1", "f2", "f3"]

    out = await batch.batch_query_executions(
        ledger=ledger,
        tenant_id="tenant-1",
        filters_list=filters_list,
    )
    assert out == [["a"], ["b"], ["c"]]
    assert ledger.query_records.await_count == 3


@pytest.mark.asyncio
async def test_registry_wait_for_all_tasks_returns_after_activity_clears() -> None:
    reg = CronTriggerRegistry(app=None)
    reg._active_tasks = 1

    async def _clear() -> None:
        await asyncio.sleep(0.05)
        reg._active_tasks = 0

    waiter = asyncio.create_task(reg.wait_for_all_tasks(timeout_seconds=1.0))
    await _clear()
    await waiter
