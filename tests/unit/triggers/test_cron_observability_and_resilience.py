"""Unit tests for cron observability and resilience helpers (Tasks 7/10/11)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from owlclaw.triggers.cron import (
    CircuitBreaker,
    CronExecution,
    CronLogger,
    CronMetrics,
    CronTriggerConfig,
    CronTriggerRegistry,
    ErrorNotifier,
    ExecutionStatus,
    RetryStrategy,
)


def _config(**kwargs) -> CronTriggerConfig:
    data: dict[str, Any] = {
        "event_name": "test_job",
        "expression": "0 * * * *",
        "migration_weight": 1.0,
        "fallback_strategy": "on_failure",
        "max_retries": 2,
        "retry_on_failure": True,
    }
    data.update(kwargs)
    return CronTriggerConfig(**data)


def test_retry_strategy_should_retry_rules() -> None:
    assert RetryStrategy.should_retry(
        error=RuntimeError("boom"),
        retry_count=0,
        max_retries=2,
        retry_on_failure=True,
    )
    assert not RetryStrategy.should_retry(
        error=ValueError("bad input"),
        retry_count=0,
        max_retries=2,
        retry_on_failure=True,
    )
    assert not RetryStrategy.should_retry(
        error=RuntimeError("boom"),
        retry_count=2,
        max_retries=2,
        retry_on_failure=True,
    )


def test_retry_strategy_calculate_delay() -> None:
    assert RetryStrategy.calculate_delay(0, base_delay_seconds=5, max_delay_seconds=60) == 5
    assert RetryStrategy.calculate_delay(2, base_delay_seconds=5, max_delay_seconds=60) == 20
    assert RetryStrategy.calculate_delay(10, base_delay_seconds=5, max_delay_seconds=60) == 60


def test_circuit_breaker_state_transitions() -> None:
    breaker = CircuitBreaker(failure_threshold=0.5, window_size=4)
    ok, _ = breaker.check("job")
    assert ok

    records = []
    for _ in range(4):
        r = MagicMock()
        r.status = "failed"
        records.append(r)
    assert breaker.evaluate("job", records) is True
    assert breaker.is_open("job") is True
    ok2, reason = breaker.check("job")
    assert ok2 is False
    assert "open" in reason

    breaker.close("job")
    assert breaker.is_open("job") is False


def test_circuit_breaker_persistent_state_store() -> None:
    class Store:
        def __init__(self) -> None:
            self.data: dict[str, str] = {}

        def get(self, key: str) -> str | None:
            return self.data.get(key)

        def set(self, key: str, value: str) -> None:
            self.data[key] = value

        def delete(self, key: str) -> None:
            self.data.pop(key, None)

    store = Store()
    breaker = CircuitBreaker(window_size=2, state_store=store)
    breaker.open("job")
    assert store.get("cron:circuit_breaker:job") == "1"
    ok, _ = breaker.check("job")
    assert ok is False
    breaker.close("job")
    assert store.get("cron:circuit_breaker:job") is None


def test_error_notifier_sampling_policy() -> None:
    notifier = ErrorNotifier()
    assert notifier._should_notify(1) is True
    assert notifier._should_notify(2) is False
    assert notifier._should_notify(3) is True
    assert notifier._should_notify(5) is True


def test_error_notifier_supports_multiple_channels() -> None:
    channel_calls: list[str] = []

    def email_channel(message: str) -> None:
        channel_calls.append(f"email:{message}")

    def slack_channel(message: str) -> None:
        channel_calls.append(f"slack:{message}")

    notifier = ErrorNotifier(channels={"email": email_channel, "slack": slack_channel})
    notifier.notify_failure("job", 1, "boom")
    assert len(channel_calls) == 2
    assert channel_calls[0].startswith("email:")
    assert channel_calls[1].startswith("slack:")


def test_cron_metrics_records_execution_in_fallback_store() -> None:
    metrics = CronMetrics()
    execution = CronExecution(
        execution_id="e1",
        event_name="job",
        triggered_at=datetime.now(timezone.utc),
        status=ExecutionStatus.SUCCESS,
        context={},
        decision_mode="agent",
        duration_seconds=1.2,
        cost_usd=0.03,
        llm_calls=4,
    )
    metrics.record_execution("job", execution)
    metrics.record_trigger_delay("job", 2.5)
    metrics.set_active_tasks(3)
    metrics.set_circuit_breaker_open(1)

    assert metrics.execution_counts[("job", "success", "agent")] == 1
    assert metrics.duration_samples[-1] == pytest.approx(1.2)
    assert metrics.cost_samples[-1] == pytest.approx(0.03)
    assert metrics.delay_samples[-1] == pytest.approx(2.5)
    assert metrics.llm_calls_total == 4
    assert metrics.active_tasks == 3
    assert metrics.circuit_breaker_open == 1


@pytest.mark.asyncio
async def test_governance_blocks_when_circuit_breaker_open() -> None:
    reg = CronTriggerRegistry(app=None)
    cfg = _config(event_name="job")
    execution = CronExecution(
        execution_id="e2",
        event_name="job",
        triggered_at=datetime.now(timezone.utc),
        status=ExecutionStatus.PENDING,
        context={},
    )
    reg._circuit_breaker.open("job")
    passed, reason = await reg._check_governance(cfg, execution, None, "default")
    assert passed is False
    assert "Circuit breaker" in reason
    assert execution.governance_checks["circuit_breaker"] is False


@pytest.mark.asyncio
async def test_governance_update_circuit_breaker_uses_recent_records() -> None:
    reg = CronTriggerRegistry(app=None)
    cfg = _config(event_name="job")
    ledger = MagicMock()
    records = []
    for _ in range(10):
        r = MagicMock()
        r.status = "failed"
        records.append(r)
    ledger.query_records = AsyncMock(return_value=records)

    await reg._governance.update_circuit_breaker(cfg, ledger, "default")
    assert reg._circuit_breaker.is_open("job") is True
    assert reg._metrics.circuit_breaker_open >= 1


def test_health_check_reports_degraded_without_hatchet() -> None:
    reg = CronTriggerRegistry(app=None)
    reg.register("a", "0 * * * *")
    reg.pause_trigger("a")
    status = reg.get_health_status()
    assert status["status"] == "degraded"
    assert status["hatchet_connected"] is False
    assert status["total_triggers"] == 1
    assert status["enabled_triggers"] == 0
    assert status["disabled_triggers"] == 1


def test_health_check_reports_unhealthy_without_any_trigger() -> None:
    reg = CronTriggerRegistry(app=None)
    status = reg.get_health_status()
    assert status["status"] == "unhealthy"
    assert status["total_triggers"] == 0


def test_cron_logger_emits_structured_style_messages(caplog: pytest.LogCaptureFixture) -> None:
    logger_helper = CronLogger()
    cfg = _config(event_name="job", focus="ops")
    with caplog.at_level(logging.INFO):
        logger_helper.log_registration(cfg)
        logger_helper.log_trigger("job", {"trigger_type": "cron"})
        logger_helper.log_execution_start("job", "e-1", "agent")
        logger_helper.log_execution_complete("job", "e-1", "success", 1.2)
        logger_helper.log_governance_skip("job", "cooldown")

    joined = " | ".join(record.message for record in caplog.records)
    assert "cron_registration event_name=job" in joined
    assert "cron_trigger event_name=job" in joined
    assert "cron_execution_start event_name=job" in joined
    assert "cron_execution_complete event_name=job" in joined
    assert "cron_governance_skip event_name=job" in joined
