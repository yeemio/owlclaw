"""Integration-style tests for Cron trigger management operations."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from owlclaw.triggers.cron import CronTriggerRegistry

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_pause_resume_and_manual_trigger_flow() -> None:
    reg = CronTriggerRegistry(app=None)
    reg.register("job", "0 * * * *")
    hatchet = MagicMock()
    hatchet.run_task_now = AsyncMock(return_value="run-123")
    ledger = MagicMock()
    ledger.record_execution = AsyncMock()
    reg.start(hatchet, agent_runtime=None, ledger=ledger, tenant_id="tenant-a")

    reg.pause_trigger("job")
    assert reg.get_trigger_status("job")["enabled"] is False
    reg.resume_trigger("job")
    assert reg.get_trigger_status("job")["enabled"] is True

    run_id = await reg.trigger_now("job")
    assert run_id == "run-123"
    hatchet.run_task_now.assert_awaited_once_with("cron_job", tenant_id="tenant-a")
    ledger.record_execution.assert_awaited_once()


def test_status_query_reports_recent_metrics() -> None:
    reg = CronTriggerRegistry(app=None)
    reg.register("daily", "0 9 * * *", focus="morning")
    reg._record_recent_execution("daily", "success", 1.2)
    reg._record_recent_execution("daily", "failed", 2.0)
    reg._record_recent_execution("daily", "fallback", 0.8)

    status = reg.get_trigger_status("daily")
    assert status["sample_size"] == 3
    assert status["success_rate"] == pytest.approx(2 / 3)
    assert status["average_duration_seconds"] == pytest.approx((1.2 + 2.0 + 0.8) / 3)


@pytest.mark.asyncio
async def test_execution_history_retrieval_with_ledger() -> None:
    reg = CronTriggerRegistry(app=None)
    reg.register("daily", "0 9 * * *")
    hatchet = MagicMock()
    ledger = MagicMock()
    record = type("LedgerRecord", (), {})()
    record.run_id = "run-1"
    record.status = "success"
    record.created_at = datetime(2026, 2, 23, 9, 0, 0, tzinfo=timezone.utc)
    record.execution_time_ms = 123
    record.output_result = {"agent_run_id": "agent-run-1"}
    record.error_message = None
    ledger.query_records = AsyncMock(return_value=[record])
    reg.start(hatchet, agent_runtime=None, ledger=ledger, tenant_id="tenant-a")

    history = await reg.get_execution_history("daily", limit=5)
    assert len(history) == 1
    assert history[0]["run_id"] == "run-1"
    assert history[0]["status"] == "success"
    assert history[0]["execution_time_ms"] == 123
    assert history[0]["agent_run_id"] == "agent-run-1"

