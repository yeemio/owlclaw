"""Integration-style tests for CronTriggerRegistry execution engine (Task 3.8)."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from owlclaw.triggers.cron import (
    CronExecution,
    CronTriggerConfig,
    CronTriggerRegistry,
    ExecutionStatus,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _registry() -> CronTriggerRegistry:
    return CronTriggerRegistry(app=None)


def _config(**kwargs) -> CronTriggerConfig:
    defaults = dict(
        event_name="test_job",
        expression="0 * * * *",
        migration_weight=1.0,
        fallback_strategy="on_failure",
        cooldown_seconds=0,
        retry_on_failure=True,
        max_retries=1,
        enabled=True,
    )
    defaults.update(kwargs)
    return CronTriggerConfig(**defaults)


def _mock_agent_runtime(run_id="run-1", tool_calls_total=2):
    rt = MagicMock()
    rt.trigger_event = AsyncMock(
        return_value={
            "status": "completed",
            "run_id": run_id,
            "tool_calls_total": tool_calls_total,
        }
    )
    return rt


# ---------------------------------------------------------------------------
# Task 3.2 — Main execution step
# ---------------------------------------------------------------------------


class TestRunCron:
    async def test_successful_agent_execution(self) -> None:
        reg = _registry()
        cfg = _config()
        agent_rt = _mock_agent_runtime(run_id="run-42")

        result = await reg._run_cron(cfg, agent_rt, None, "default")

        assert result["status"] == ExecutionStatus.SUCCESS.value
        assert "execution_id" in result
        agent_rt.trigger_event.assert_called_once_with(
            "test_job",
            focus=None,
            payload={"trigger_type": "cron", "expression": "0 * * * *", "focus": None},
        )

    async def test_skipped_when_disabled(self) -> None:
        reg = _registry()
        cfg = _config(enabled=False)
        result = await reg._run_cron(cfg, None, None, "default")
        assert result["status"] == ExecutionStatus.SKIPPED.value
        assert "disabled" in result["reason"]

    async def test_fallback_when_no_agent_runtime(self) -> None:
        fallback = AsyncMock()
        cfg = _config(fallback_handler=fallback, migration_weight=1.0)
        reg = _registry()

        # agent_runtime=None → should fall back even with weight=1.0
        result = await reg._run_cron(cfg, None, None, "default")
        fallback.assert_called_once()
        assert result["status"] == ExecutionStatus.FALLBACK.value

    async def test_no_fallback_handler_returns_skipped(self) -> None:
        cfg = _config(fallback_handler=None, migration_weight=0.0)
        reg = _registry()
        result = await reg._run_cron(cfg, None, None, "default")
        assert result["status"] == ExecutionStatus.SKIPPED.value

    async def test_duration_recorded(self) -> None:
        reg = _registry()
        cfg = _config()
        agent_rt = _mock_agent_runtime()

        result = await reg._run_cron(cfg, agent_rt, None, "default")
        assert result["duration_seconds"] is not None
        assert result["duration_seconds"] >= 0

    async def test_ledger_called_on_success(self) -> None:
        reg = _registry()
        cfg = _config()
        agent_rt = _mock_agent_runtime()
        ledger = MagicMock()
        ledger.record_execution = AsyncMock()
        ledger.query_records = AsyncMock(return_value=[])

        await reg._run_cron(cfg, agent_rt, ledger, "tenant1")
        ledger.record_execution.assert_called_once()
        call_kwargs = ledger.record_execution.call_args.kwargs
        assert call_kwargs["tenant_id"] == "tenant1"
        assert call_kwargs["capability_name"] == "test_job"
        assert call_kwargs["task_type"] == "cron_execution"
        assert call_kwargs["status"] == ExecutionStatus.SUCCESS.value

    async def test_ledger_called_on_failure(self) -> None:
        reg = _registry()
        cfg = _config(fallback_strategy="never")

        async def failing_agent(*a, **kw):
            raise RuntimeError("boom")

        agent_rt = MagicMock()
        agent_rt.trigger_event = AsyncMock(side_effect=RuntimeError("boom"))
        ledger = MagicMock()
        ledger.record_execution = AsyncMock()
        ledger.query_records = AsyncMock(return_value=[])

        await reg._run_cron(cfg, agent_rt, ledger, "default")
        ledger.record_execution.assert_called_once()
        call_kwargs = ledger.record_execution.call_args.kwargs
        assert call_kwargs["status"] == ExecutionStatus.FAILED.value
        assert "boom" in call_kwargs["error_message"]


# ---------------------------------------------------------------------------
# Task 3.3 — Governance checks
# ---------------------------------------------------------------------------


class TestGovernanceChecks:
    async def test_no_ledger_passes_all_checks(self) -> None:
        reg = _registry()
        cfg = _config(cooldown_seconds=3600, max_daily_runs=1, max_daily_cost=5.0)
        import uuid
        from datetime import datetime, timezone

        from owlclaw.triggers.cron import CronExecution, ExecutionStatus

        execution = CronExecution(
            execution_id=str(uuid.uuid4()),
            event_name="test_job",
            triggered_at=datetime.now(timezone.utc),
            status=ExecutionStatus.PENDING,
            context={},
        )
        passed, reason = await reg._check_governance(cfg, execution, None, "default")
        assert passed is True
        assert reason == ""

    async def test_cooldown_blocks_run(self) -> None:
        import uuid
        from datetime import datetime, timedelta, timezone

        reg = _registry()
        cfg = _config(cooldown_seconds=3600)

        # Mock a Ledger record created 10 seconds ago
        recent_record = MagicMock()
        recent_record.created_at = datetime.now(timezone.utc) - timedelta(seconds=10)
        ledger = MagicMock()
        ledger.query_records = AsyncMock(return_value=[recent_record])

        execution = CronExecution(
            execution_id=str(uuid.uuid4()),
            event_name="test_job",
            triggered_at=datetime.now(timezone.utc),
            status=ExecutionStatus.PENDING,
            context={},
        )
        passed, reason = await reg._check_governance(cfg, execution, ledger, "default")
        assert passed is False
        assert "Cooldown" in reason

    async def test_max_daily_runs_blocks(self) -> None:
        import uuid
        from datetime import datetime, timezone

        reg = _registry()
        cfg = _config(max_daily_runs=2)

        # Already 2 runs today
        ledger = MagicMock()
        ledger.query_records = AsyncMock(return_value=[MagicMock(), MagicMock()])

        execution = CronExecution(
            execution_id=str(uuid.uuid4()),
            event_name="test_job",
            triggered_at=datetime.now(timezone.utc),
            status=ExecutionStatus.PENDING,
            context={},
        )
        passed, reason = await reg._check_governance(cfg, execution, ledger, "default")
        assert passed is False
        assert "Daily run limit" in reason

    async def test_max_daily_cost_blocks(self) -> None:
        import uuid
        from datetime import datetime, timezone

        reg = _registry()
        cfg = _config(max_daily_cost=1.0)

        # Simulate 3 records with $0.50 each = $1.50
        def make_record(cost):
            r = MagicMock()
            r.estimated_cost = Decimal(str(cost))
            return r

        ledger = MagicMock()
        ledger.query_records = AsyncMock(
            return_value=[make_record(0.5), make_record(0.5), make_record(0.5)]
        )

        execution = CronExecution(
            execution_id=str(uuid.uuid4()),
            event_name="test_job",
            triggered_at=datetime.now(timezone.utc),
            status=ExecutionStatus.PENDING,
            context={},
        )
        passed, reason = await reg._check_governance(cfg, execution, ledger, "default")
        assert passed is False
        assert "Daily cost limit" in reason


# ---------------------------------------------------------------------------
# Task 3.4 — Agent vs Fallback decision
# ---------------------------------------------------------------------------


class TestShouldUseAgent:
    def test_weight_1_always_agent(self) -> None:
        cfg = _config(migration_weight=1.0)
        results = [CronTriggerRegistry._should_use_agent(cfg) for _ in range(20)]
        assert all(results)

    def test_weight_0_never_agent(self) -> None:
        cfg = _config(migration_weight=0.0)
        results = [CronTriggerRegistry._should_use_agent(cfg) for _ in range(20)]
        assert not any(results)

    def test_weight_half_mixed(self) -> None:
        cfg = _config(migration_weight=0.5)
        with patch("owlclaw.triggers.cron.random.random", side_effect=[0.3, 0.7, 0.4]):
            r1 = CronTriggerRegistry._should_use_agent(cfg)
            r2 = CronTriggerRegistry._should_use_agent(cfg)
            r3 = CronTriggerRegistry._should_use_agent(cfg)
        assert r1 is True
        assert r2 is False
        assert r3 is True


# ---------------------------------------------------------------------------
# Task 3.5/3.6 — Agent and fallback paths
# ---------------------------------------------------------------------------


class TestExecuteAgent:
    async def test_agent_run_id_recorded(self) -> None:
        import uuid
        from datetime import datetime, timezone

        reg = _registry()
        cfg = _config()
        agent_rt = _mock_agent_runtime(run_id="agent-xyz", tool_calls_total=5)
        execution = CronExecution(
            execution_id=str(uuid.uuid4()),
            event_name="test_job",
            triggered_at=datetime.now(timezone.utc),
            status=ExecutionStatus.RUNNING,
            context={},
        )
        await reg._execute_agent(cfg, execution, agent_rt)
        assert execution.agent_run_id == "agent-xyz"
        assert execution.llm_calls == 5


class TestExecuteFallback:
    async def test_async_fallback_called(self) -> None:
        import uuid
        from datetime import datetime, timezone

        fallback = AsyncMock()
        reg = _registry()
        cfg = _config(fallback_handler=fallback)
        execution = CronExecution(
            execution_id=str(uuid.uuid4()),
            event_name="test_job",
            triggered_at=datetime.now(timezone.utc),
            status=ExecutionStatus.RUNNING,
            context={},
        )
        await reg._execute_fallback(cfg, execution)
        fallback.assert_called_once()
        assert execution.status == ExecutionStatus.FALLBACK

    async def test_sync_fallback_called(self) -> None:
        import uuid
        from datetime import datetime, timezone

        called = []
        def sync_handler():
            called.append(True)

        reg = _registry()
        cfg = _config(fallback_handler=sync_handler)
        execution = CronExecution(
            execution_id=str(uuid.uuid4()),
            event_name="test_job",
            triggered_at=datetime.now(timezone.utc),
            status=ExecutionStatus.RUNNING,
            context={},
        )
        await reg._execute_fallback(cfg, execution)
        assert called == [True]
        assert execution.status == ExecutionStatus.FALLBACK

    async def test_no_fallback_handler_skips(self) -> None:
        import uuid
        from datetime import datetime, timezone

        reg = _registry()
        cfg = _config(fallback_handler=None)
        execution = CronExecution(
            execution_id=str(uuid.uuid4()),
            event_name="test_job",
            triggered_at=datetime.now(timezone.utc),
            status=ExecutionStatus.RUNNING,
            context={},
        )
        await reg._execute_fallback(cfg, execution)
        assert execution.status == ExecutionStatus.SKIPPED


# ---------------------------------------------------------------------------
# Task 3.7 — Failure handling
# ---------------------------------------------------------------------------


class TestHandleFailure:
    async def test_on_failure_triggers_fallback(self) -> None:
        fallback = AsyncMock()
        reg = _registry()
        cfg = _config(fallback_handler=fallback, fallback_strategy="on_failure")
        import uuid
        from datetime import datetime, timezone

        execution = CronExecution(
            execution_id=str(uuid.uuid4()),
            event_name="test_job",
            triggered_at=datetime.now(timezone.utc),
            status=ExecutionStatus.FAILED,
            context={},
        )
        await reg._handle_failure(cfg, execution)
        fallback.assert_called_once()

    async def test_never_strategy_skips_fallback(self) -> None:
        fallback = AsyncMock()
        reg = _registry()
        cfg = _config(fallback_handler=fallback, fallback_strategy="never")
        import uuid
        from datetime import datetime, timezone

        execution = CronExecution(
            execution_id=str(uuid.uuid4()),
            event_name="test_job",
            triggered_at=datetime.now(timezone.utc),
            status=ExecutionStatus.FAILED,
            context={},
        )
        await reg._handle_failure(cfg, execution)
        fallback.assert_not_called()

    async def test_failure_in_fallback_is_logged_not_raised(self) -> None:
        async def bad_fallback():
            raise RuntimeError("fallback also failed")

        reg = _registry()
        cfg = _config(fallback_handler=bad_fallback, fallback_strategy="on_failure")
        import uuid
        from datetime import datetime, timezone

        execution = CronExecution(
            execution_id=str(uuid.uuid4()),
            event_name="test_job",
            triggered_at=datetime.now(timezone.utc),
            status=ExecutionStatus.FAILED,
            context={},
        )
        # Should NOT raise
        await reg._handle_failure(cfg, execution)


# ---------------------------------------------------------------------------
# Task 3.1 — Hatchet registration
# ---------------------------------------------------------------------------


class TestHatchetRegistration:
    def test_start_registers_all_triggers(self) -> None:
        reg = _registry()
        reg.register("job_a", "0 * * * *")
        reg.register("job_b", "0 9 * * *")

        hatchet = MagicMock()
        task_decorator = MagicMock(return_value=lambda fn: fn)
        hatchet.task = MagicMock(return_value=task_decorator)
        hatchet._hatchet = MagicMock()  # simulate connected

        reg.start(hatchet)

        assert hatchet.task.call_count == 2
        names = [call.kwargs["name"] for call in hatchet.task.call_args_list]
        assert "cron_job_a" in names
        assert "cron_job_b" in names

    def test_start_passes_cron_expression(self) -> None:
        reg = _registry()
        reg.register("hourly", "0 * * * *")

        hatchet = MagicMock()
        hatchet.task = MagicMock(return_value=lambda fn: fn)
        hatchet._hatchet = MagicMock()

        reg.start(hatchet)

        call_kwargs = hatchet.task.call_args.kwargs
        assert call_kwargs["cron"] == "0 * * * *"

    def test_hatchet_workflows_populated(self) -> None:
        reg = _registry()
        reg.register("weekly_report", "0 8 * * 1")

        hatchet = MagicMock()
        hatchet.task = MagicMock(return_value=lambda fn: fn)
        hatchet._hatchet = MagicMock()

        reg.start(hatchet)
        assert "weekly_report" in reg._hatchet_workflows
