"""Integration tests for Hatchet (use mock_run when no server).

Requires: .env with HATCHET_API_TOKEN and HATCHET_SERVER_URL (or set in env).
One test is skipped in mock_run: durable_sleep needs a real Hatchet worker (durable event listener).
"""

import asyncio
import os
import subprocess
import sys
import time
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from owlclaw.integrations.hatchet import HatchetClient, HatchetConfig

pytestmark = pytest.mark.integration
_WORKER_RUNNER = Path(__file__).with_name("_hatchet_worker_runner.py")
_SUCCESS_TERMINALS = ("succeeded", "completed", "success")
_FAILED_TERMINALS = ("failed", "cancelled", "canceled", "error", "timeout")


def _has_hatchet_token() -> bool:
    token = os.environ.get("HATCHET_API_TOKEN", "").strip()
    return bool(token and token.startswith("ey"))


def _normalize_status(value: str) -> str:
    return value.strip().lower()


def _start_worker_process(task_name: str, sleep_seconds: float) -> subprocess.Popen:
    env = os.environ.copy()
    env["HATCHET_E2E_TASK_NAME"] = task_name
    env["HATCHET_E2E_SLEEP_SECONDS"] = str(sleep_seconds)
    env.setdefault("HATCHET_GRPC_TLS_STRATEGY", "none")
    return subprocess.Popen(
        [sys.executable, str(_WORKER_RUNNER)],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _stop_process(proc: subprocess.Popen | None, timeout: float = 20.0) -> None:
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=timeout)


async def _poll_terminal_status(client: HatchetClient, run_id: str, timeout_seconds: int = 180) -> str:
    deadline = time.monotonic() + timeout_seconds
    last_status = ""
    while time.monotonic() < deadline:
        status_obj = await client.get_task_status(run_id)
        raw = str(status_obj.get("status", ""))
        norm = _normalize_status(raw)
        last_status = raw
        if any(done in norm for done in _SUCCESS_TERMINALS):
            return raw
        if any(bad in norm for bad in _FAILED_TERMINALS):
            raise AssertionError(f"workflow run entered failure status: {raw}")
        await asyncio.sleep(1.0)
    raise AssertionError(f"workflow run did not reach terminal success, last status={last_status}")


async def _run_task_when_registered(client: HatchetClient, task_name: str, timeout_seconds: int = 30) -> str:
    deadline = time.monotonic() + timeout_seconds
    last_error = ""
    while time.monotonic() < deadline:
        try:
            run_id = await client.run_task_now(task_name)
            if run_id:
                return run_id
        except Exception as exc:
            last_error = str(exc)
            lowered = last_error.lower()
            if "workflow names not found" not in lowered and "not found" not in lowered:
                raise
        await asyncio.sleep(1.0)
    raise AssertionError(f"workflow did not become schedulable in time: {last_error}")


@pytest.mark.asyncio
async def test_hatchet_task_mock_run_e2e():
    """E2E: connect, register task, run via mock_run (no Hatchet server)."""
    if not _has_hatchet_token():
        pytest.skip("HATCHET_API_TOKEN not set or invalid JWT; skipping Hatchet integration")

    config = HatchetConfig(api_token=os.environ["HATCHET_API_TOKEN"])
    client = HatchetClient(config)
    try:
        client.connect()
    except Exception:
        pytest.skip("Could not connect to Hatchet (server may be down)")

    try:
        @client.task(name="integration-echo")
        async def echo_task(input, ctx):
            return {"status": "ok"}

        standalone = client._workflows["integration-echo"]
        result = await standalone.aio_mock_run({})
        assert result == {"status": "ok"}
    finally:
        client.disconnect()


@pytest.mark.asyncio
async def test_hatchet_durable_task_aio_sleep_for_mock():
    """Task 7.2.1: Create task using ctx.aio_sleep_for(); verify via mock_run."""
    if not _has_hatchet_token():
        pytest.skip("HATCHET_API_TOKEN not set; skipping durable sleep test")

    config = HatchetConfig(api_token=os.environ["HATCHET_API_TOKEN"])
    client = HatchetClient(config)
    try:
        client.connect()
    except Exception:
        pytest.skip("Could not connect to Hatchet (server may be down)")

    try:
        @client.durable_task(name="integration-durable-sleep", timeout=30)
        async def durable_sleep_task(input, ctx):
            await ctx.aio_sleep_for(timedelta(seconds=0))  # 0s for fast mock
            return {"slept": True}

        standalone = client._workflows["integration-durable-sleep"]
        try:
            result = await standalone.aio_mock_run({})
            assert result == {"slept": True}
        except ValueError as e:
            if "durable event listener" in str(e).lower() or "Durable event listener" in str(e):
                pytest.skip("aio_sleep_for not supported in mock_run (no durable event listener); run with real worker for 7.2.3/7.2.4")
            raise
    finally:
        client.disconnect()


@pytest.mark.asyncio
async def test_hatchet_durable_task_worker_restart_recovery_real_e2e():
    """Task 7.2.3/7.2.4: worker restart during durable sleep should recover."""
    if not _has_hatchet_token():
        pytest.skip("HATCHET_API_TOKEN not set; skipping real restart recovery test")

    sleep_seconds = float(os.environ.get("HATCHET_E2E_SLEEP_SECONDS", "8"))
    task_name = f"integration-durable-restart-{uuid4().hex[:8]}"
    worker_a: subprocess.Popen | None = None
    worker_b: subprocess.Popen | None = None
    client: HatchetClient | None = None

    worker_a = _start_worker_process(task_name=task_name, sleep_seconds=sleep_seconds)
    await asyncio.sleep(4.0)
    if worker_a.poll() is not None:
        pytest.skip("first worker process exited unexpectedly before test execution")

    try:
        config = HatchetConfig(
            api_token=os.environ["HATCHET_API_TOKEN"],
            grpc_tls_strategy=os.environ.get("HATCHET_GRPC_TLS_STRATEGY", "none"),
        )
        client = HatchetClient(config)
        client.connect()

        @client.durable_task(name=task_name, timeout=max(int(sleep_seconds * 4), 30))
        async def _durable_task(input, ctx):
            await ctx.aio_sleep_for(timedelta(seconds=sleep_seconds))
            return {"slept": True}

        run_id = await _run_task_when_registered(client, task_name=task_name, timeout_seconds=45)

        await asyncio.sleep(min(max(sleep_seconds / 2.0, 1.5), 5.0))
        _stop_process(worker_a)
        worker_a = None

        worker_b = _start_worker_process(task_name=task_name, sleep_seconds=sleep_seconds)
        await asyncio.sleep(4.0)
        if worker_b.poll() is not None:
            pytest.skip("second worker process exited unexpectedly during restart")

        final_status = await _poll_terminal_status(client, run_id=run_id, timeout_seconds=180)
        assert any(tag in _normalize_status(final_status) for tag in _SUCCESS_TERMINALS)
    finally:
        _stop_process(worker_a)
        _stop_process(worker_b)
        if client is not None:
            client.disconnect()


@pytest.mark.asyncio
async def test_hatchet_schedule_throughput_1000_optional_real():
    """Task 11.1.2: optional real-env throughput check for 1000 schedules."""
    if not _has_hatchet_token():
        pytest.skip("HATCHET_API_TOKEN not set; skipping 1000 scheduling throughput test")
    if os.environ.get("HATCHET_RUN_PERF_1000", "0") != "1":
        pytest.skip("Set HATCHET_RUN_PERF_1000=1 to run optional 1000 scheduling throughput test")

    task_name = f"integration-schedule-perf-{uuid4().hex[:8]}"
    total_jobs = 1000
    batch_size = 100
    config = HatchetConfig(
        api_token=os.environ["HATCHET_API_TOKEN"],
        grpc_tls_strategy=os.environ.get("HATCHET_GRPC_TLS_STRATEGY", "none"),
    )
    client = HatchetClient(config)
    client.connect()
    scheduled_ids: list[str] = []

    try:
        @client.task(name=task_name, timeout=30)
        async def _schedule_perf_task(input, ctx):
            return {"ok": True}

        started = time.perf_counter()
        for offset in range(0, total_jobs, batch_size):
            ids = await asyncio.gather(
                *(
                    client.schedule_task(
                        task_name,
                        delay_seconds=300,
                        n=i,
                    )
                    for i in range(offset, min(offset + batch_size, total_jobs))
                )
            )
            scheduled_ids.extend(ids)
        elapsed = max(time.perf_counter() - started, 1e-6)
        throughput = total_jobs / elapsed

        assert len(scheduled_ids) == total_jobs
        assert throughput > 1.0
    finally:
        await asyncio.gather(*(client.cancel_task(run_id) for run_id in scheduled_ids), return_exceptions=True)
        client.disconnect()
