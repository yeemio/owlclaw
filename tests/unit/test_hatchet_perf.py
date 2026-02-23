"""Light performance tests for Hatchet integration (no server)."""

import asyncio
import contextlib
import time
from datetime import datetime, timezone

from owlclaw.integrations.hatchet import HatchetClient, HatchetConfig


def test_config_from_yaml_perf(tmp_path):
    """Config load from YAML is fast (< 50ms for single load)."""
    (tmp_path / "c.yaml").write_text("hatchet:\n  server_url: http://localhost:7077\n", encoding="utf-8")
    start = time.perf_counter()
    for _ in range(100):
        HatchetConfig.from_yaml(tmp_path / "c.yaml")
    elapsed = time.perf_counter() - start
    assert elapsed < 2.0, "100 config loads should complete in under 2s"


def test_schedule_task_validation_perf():
    """schedule_task validation (unregistered task) is fast."""
    import asyncio
    client = HatchetClient(HatchetConfig())

    async def run_many():
        for _ in range(200):
            with contextlib.suppress(ValueError):
                await client.schedule_task("x", delay_seconds=1)

    start = time.perf_counter()
    asyncio.run(run_many())
    elapsed = time.perf_counter() - start
    assert elapsed < 2.0, "200 validation failures should complete in under 2s"


def test_worker_restart_simulation_preserves_durable_task_execution():
    """7.2.3: simulate worker restart and verify durable task can still run."""

    class _Workflow:
        async def aio_run(self, input):  # type: ignore[no-untyped-def]
            return type("RunResult", (), {"workflow_run_id": f"run-{input.get('n', 0)}"})()

    class _Standalone:
        def __init__(self):
            self._workflow = _Workflow()

    client = HatchetClient(HatchetConfig())
    client._workflows["durable-x"] = _Standalone()
    client._hatchet = object()  # started worker
    # Simulate restart: worker process restarted, client reconnects.
    client._hatchet = object()

    run_id = asyncio.run(client.run_task_now("durable-x", n=1))
    assert run_id == "run-1"


def test_concurrent_ten_tasks_complete_within_target():
    """11.2: run 10 concurrent tasks and assert completion within 30s target."""

    class _Workflow:
        async def aio_run(self, input):  # type: ignore[no-untyped-def]
            await asyncio.sleep(0.01)
            return type("RunResult", (), {"workflow_run_id": f"run-{input.get('idx', 0)}"})()

    class _Standalone:
        def __init__(self):
            self._workflow = _Workflow()

    client = HatchetClient(HatchetConfig())
    client._workflows["concurrent-x"] = _Standalone()

    async def _runner():
        tasks = [client.run_task_now("concurrent-x", idx=i) for i in range(10)]
        return await asyncio.gather(*tasks)

    start = time.perf_counter()
    run_ids = asyncio.run(_runner())
    elapsed = time.perf_counter() - start
    assert len(run_ids) == 10
    assert elapsed < 30.0


def test_scheduling_delay_precision_simulation():
    """11.3: schedule precision across delays should stay within small tolerance."""

    class _Workflow:
        def __init__(self):
            self.run_at_values = []

        async def aio_schedule(self, run_at, input):  # type: ignore[no-untyped-def]
            self.run_at_values.append(run_at)
            return type("ScheduleResult", (), {"workflow_run_id": "scheduled-id"})()

    class _Standalone:
        def __init__(self):
            self._workflow = _Workflow()

    client = HatchetClient(HatchetConfig())
    standalone = _Standalone()
    client._workflows["delay-x"] = standalone

    for delay in (1, 5, 30):
        start = datetime.now(timezone.utc)
        scheduled_id = asyncio.run(client.schedule_task("delay-x", delay_seconds=delay))
        assert scheduled_id == "scheduled-id"
        actual_run_at = standalone._workflow.run_at_values[-1]
        delta = (actual_run_at - start).total_seconds()
        assert abs(delta - delay) < 0.5


def test_optional_throughput_1000_schedules_simulation():
    """11.1.2: optional 1000 schedule throughput check via local simulation."""

    class _Workflow:
        async def aio_schedule(self, run_at, input):  # type: ignore[no-untyped-def]
            return type("ScheduleResult", (), {"workflow_run_id": "scheduled"})()

    class _Standalone:
        def __init__(self):
            self._workflow = _Workflow()

    client = HatchetClient(HatchetConfig())
    client._workflows["throughput-x"] = _Standalone()

    async def _runner():
        for i in range(1000):
            await client.schedule_task("throughput-x", delay_seconds=1, idx=i)

    start = time.perf_counter()
    asyncio.run(_runner())
    elapsed = time.perf_counter() - start
    assert elapsed < 10.0
