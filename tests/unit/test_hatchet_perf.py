"""Light performance tests for Hatchet integration (no server)."""

import contextlib
import time
from dataclasses import dataclass
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


@dataclass
class _RunResult:
    workflow_run_id: str


class _WorkflowStub:
    def __init__(self) -> None:
        self.scheduled_run_at: datetime | None = None

    async def aio_run(self, input):  # type: ignore[no-untyped-def]
        import asyncio

        await asyncio.sleep(0.01)
        ident = str(input.get("idx", "x")) if isinstance(input, dict) else "x"
        return _RunResult(workflow_run_id=f"run-{ident}")

    async def aio_schedule(self, run_at, input):  # type: ignore[no-untyped-def]
        self.scheduled_run_at = run_at
        return _RunResult(workflow_run_id="scheduled-1")


class _StandaloneStub:
    def __init__(self, workflow: _WorkflowStub) -> None:
        self._workflow = workflow


def test_run_task_now_concurrency_10_tasks_under_30s():
    """Task 11.2: concurrent execution path handles 10 tasks well below 30s."""
    import asyncio

    async def _run() -> tuple[list[str], float]:
        client = HatchetClient(HatchetConfig())
        wf = _WorkflowStub()
        client._workflows["job"] = _StandaloneStub(wf)
        start = time.perf_counter()
        ids = await asyncio.gather(*(client.run_task_now("job", idx=i) for i in range(10)))
        elapsed = time.perf_counter() - start
        return ids, elapsed

    ids, elapsed = asyncio.run(_run())
    assert len(ids) == 10
    assert all(run_id.startswith("run-") for run_id in ids)
    assert elapsed < 30.0


def test_schedule_task_delay_precision_within_tolerance():
    """Task 11.3: scheduled run_at stays close to expected delay."""
    import asyncio

    async def _run() -> float:
        client = HatchetClient(HatchetConfig())
        wf = _WorkflowStub()
        client._workflows["job"] = _StandaloneStub(wf)
        delay_seconds = 5
        before = datetime.now(timezone.utc)
        await client.schedule_task("job", delay_seconds=delay_seconds)
        assert wf.scheduled_run_at is not None
        actual_delay = (wf.scheduled_run_at - before).total_seconds()
        return abs(actual_delay - delay_seconds)

    delta = asyncio.run(_run())
    assert delta < 0.3
