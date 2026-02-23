"""End-to-end style tests for cron trigger workflow wiring (Task 15.1)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from owlclaw.triggers.cron import CronTriggerRegistry, ExecutionStatus

pytestmark = pytest.mark.integration


def _registry() -> CronTriggerRegistry:
    return CronTriggerRegistry(app=None)


@pytest.mark.asyncio
async def test_cron_e2e_register_start_execute_success() -> None:
    registry = _registry()
    registry.register("hourly_job", "0 * * * *", focus="ops")

    hatchet = MagicMock()
    hatchet.task = MagicMock(return_value=lambda fn: fn)
    runtime = MagicMock()
    runtime.trigger_event = AsyncMock(return_value={"run_id": "run-1", "tool_calls_total": 1})
    ledger = MagicMock()
    ledger.record_execution = AsyncMock()
    ledger.query_records = AsyncMock(return_value=[])

    registry.start(hatchet, agent_runtime=runtime, ledger=ledger, tenant_id="tenant-a")
    handler = registry._hatchet_workflows["hourly_job"]
    result = await handler({})

    assert result["status"] == ExecutionStatus.SUCCESS.value
    runtime.trigger_event.assert_awaited_once()
    ledger.record_execution.assert_awaited_once()


@pytest.mark.asyncio
async def test_cron_e2e_agent_failure_fallback_path() -> None:
    calls: list[str] = []

    async def fallback() -> dict[str, str]:
        calls.append("fallback")
        return {"status": "ok"}

    registry = _registry()
    registry.register(
        "job_with_fallback",
        "*/15 * * * *",
        fallback_handler=fallback,
        fallback_strategy="on_failure",
    )

    hatchet = MagicMock()
    hatchet.task = MagicMock(return_value=lambda fn: fn)
    runtime = MagicMock()
    runtime.trigger_event = AsyncMock(side_effect=RuntimeError("agent failed"))
    ledger = MagicMock()
    ledger.record_execution = AsyncMock()
    ledger.query_records = AsyncMock(return_value=[])

    registry.start(hatchet, agent_runtime=runtime, ledger=ledger, tenant_id="tenant-a")
    handler = registry._hatchet_workflows["job_with_fallback"]
    result = await handler({})

    assert result["status"] in {ExecutionStatus.FALLBACK.value, ExecutionStatus.SUCCESS.value}
    assert calls == ["fallback"]


@pytest.mark.asyncio
async def test_cron_e2e_manual_trigger_pause_resume() -> None:
    registry = _registry()
    registry.register("manual_job", "0 9 * * *")

    hatchet = MagicMock()
    hatchet.task = MagicMock(return_value=lambda fn: fn)
    hatchet.run_task_now = AsyncMock(return_value="manual-run-1")
    hatchet.pause_task = MagicMock(return_value=None)
    hatchet.resume_task = MagicMock(return_value=None)

    registry.start(hatchet, agent_runtime=None, ledger=None, tenant_id="tenant-a")
    registry.pause_trigger("manual_job")
    assert registry.get_trigger("manual_job").enabled is False  # type: ignore[union-attr]
    registry.resume_trigger("manual_job")
    assert registry.get_trigger("manual_job").enabled is True  # type: ignore[union-attr]

    run_id = await registry.trigger_now("manual_job")
    assert run_id == "manual-run-1"
