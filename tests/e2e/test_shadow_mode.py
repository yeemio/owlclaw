"""Tests for shadow mode and migration weight coordination."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from owlclaw.e2e.shadow_mode import (
    CronExecutionLog,
    MigrationWeightController,
    ShadowComparator,
    ShadowDecisionLog,
    ShadowModeInterceptor,
)


@pytest.mark.asyncio
async def test_shadow_mode_interceptor_records_without_execution() -> None:
    interceptor = ShadowModeInterceptor()
    result = await interceptor.intercept("agent-a", "check_entry_opportunity", {"symbol": "AAPL"})
    assert result.executed is False
    assert result.simulated_result["status"] == "shadow_simulated"
    logs = interceptor.get_logs(agent_id="agent-a")
    assert len(logs) == 1
    assert logs[0].capability == "check_entry_opportunity"


@pytest.mark.asyncio
async def test_shadow_comparator_dashboard_metrics() -> None:
    comparator = ShadowComparator()
    now = datetime.now(timezone.utc)

    for index in range(8):
        capability = "check_entry_opportunity" if index < 7 else "different"
        shadow = ShadowDecisionLog(
            agent_id="agent-a",
            capability="check_entry_opportunity",
            args={"idx": index},
            timestamp=now + timedelta(minutes=index),
        )
        cron = CronExecutionLog(
            agent_id="agent-a",
            capability=capability,
            result={"ok": True},
            timestamp=now + timedelta(minutes=index),
        )
        await comparator.compare_realtime(shadow, cron)

    metrics = await comparator.get_dashboard_metrics("agent-a", (now, now + timedelta(minutes=10)))
    assert metrics.total_comparisons == 8
    assert metrics.consistent_decisions == 7
    assert metrics.consistency_rate == 0.875
    assert len(metrics.inconsistent_decisions) == 1
    assert metrics.recommendation is None


@pytest.mark.asyncio
async def test_migration_weight_controller_adjusts_weight() -> None:
    comparator = ShadowComparator()
    now = datetime.now(timezone.utc)
    for index in range(10):
        shadow = ShadowDecisionLog(
            agent_id="agent-b",
            capability="c",
            args={"i": index},
            timestamp=now + timedelta(minutes=index),
        )
        cron = CronExecutionLog(
            agent_id="agent-b",
            capability="c",
            result={"ok": True},
            timestamp=now + timedelta(minutes=index),
        )
        await comparator.compare_realtime(shadow, cron)

    controller = MigrationWeightController(shadow_comparator=comparator, current_weight=0.0)
    updated = await controller.evaluate_and_adjust("agent-b", time_range=(now, now + timedelta(minutes=20)))
    assert updated == 0.1

