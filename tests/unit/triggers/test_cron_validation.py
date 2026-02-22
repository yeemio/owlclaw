"""Unit tests for CronTriggerRegistry cron expression validation (Task 2.3)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from owlclaw.triggers.cron import CronTriggerRegistry


class TestCronExpressionValidation:
    """Tests for _validate_cron_expression."""

    # ------------------------------------------------------------------
    # Valid expressions
    # ------------------------------------------------------------------

    @pytest.mark.parametrize(
        "expression",
        [
            "* * * * *",          # every minute
            "0 * * * *",          # every hour
            "0 9 * * *",          # daily at 09:00
            "0 9 * * 1-5",        # weekdays at 09:00
            "0 0 1 * *",          # first of month
            "30 6 * * 0",         # every Sunday at 06:30
            "*/15 * * * *",       # every 15 minutes
            "0 8,12,18 * * *",    # three times a day
            "0 0 1,15 * *",       # 1st and 15th of month
        ],
    )
    def test_valid_expression(self, expression: str) -> None:
        assert CronTriggerRegistry._validate_cron_expression(expression) is True

    # ------------------------------------------------------------------
    # Invalid expressions
    # ------------------------------------------------------------------

    @pytest.mark.parametrize(
        "expression",
        [
            "",                  # empty string
            "not_cron",          # random text
            "0 0 0 0",           # only 4 fields
            "0 0 0 0 0 0",       # 6 fields (Quartz style, not supported)
            "60 * * * *",        # minute out of range
            "* 25 * * *",        # hour out of range
            "* * 32 * *",        # day of month out of range
            "* * * 13 *",        # month out of range
            "* * * * 8",         # day of week out of range
        ],
    )
    def test_invalid_expression(self, expression: str) -> None:
        assert CronTriggerRegistry._validate_cron_expression(expression) is False


class TestCronRegistration:
    """Tests for register(), get_trigger(), list_triggers()."""

    def _registry(self) -> CronTriggerRegistry:
        return CronTriggerRegistry(app=None)

    def test_register_and_get(self) -> None:
        reg = self._registry()
        reg.register("daily_check", "0 9 * * *")
        config = reg.get_trigger("daily_check")
        assert config is not None
        assert config.event_name == "daily_check"
        assert config.expression == "0 9 * * *"

    def test_register_duplicate_raises(self) -> None:
        reg = self._registry()
        reg.register("check", "0 * * * *")
        with pytest.raises(ValueError, match="already registered"):
            reg.register("check", "0 * * * *")

    def test_register_invalid_expression_raises(self) -> None:
        reg = self._registry()
        with pytest.raises(ValueError, match="Invalid cron expression"):
            reg.register("bad", "not_a_cron")

    def test_list_triggers_empty(self) -> None:
        reg = self._registry()
        assert reg.list_triggers() == []

    def test_list_triggers_returns_all(self) -> None:
        reg = self._registry()
        reg.register("a", "0 * * * *")
        reg.register("b", "0 9 * * *")
        names = {t.event_name for t in reg.list_triggers()}
        assert names == {"a", "b"}

    def test_get_missing_returns_none(self) -> None:
        reg = self._registry()
        assert reg.get_trigger("nonexistent") is None

    def test_register_stores_optional_fields(self) -> None:
        reg = self._registry()

        async def fallback() -> None:
            pass

        reg.register(
            "weekly_report",
            "0 8 * * 1",
            focus="reporting",
            fallback_handler=fallback,
            description="Weekly report",
            max_daily_runs=1,
            priority=5,
        )
        config = reg.get_trigger("weekly_report")
        assert config.focus == "reporting"
        assert config.fallback_handler is fallback
        assert config.description == "Weekly report"
        assert config.max_daily_runs == 1
        assert config.priority == 5

    def test_register_rejects_empty_event_name(self) -> None:
        reg = self._registry()
        with pytest.raises(ValueError, match="event_name must not be empty"):
            reg.register("   ", "0 * * * *")

    def test_register_normalizes_focus_whitespace(self) -> None:
        reg = self._registry()
        reg.register("daily", "0 9 * * *", focus="  reporting  ")
        config = reg.get_trigger("daily")
        assert config is not None
        assert config.focus == "reporting"
        reg.register("daily2", "0 10 * * *", focus="   ")
        config2 = reg.get_trigger("daily2")
        assert config2 is not None
        assert config2.focus is None

    def test_register_special_chars(self) -> None:
        reg = self._registry()
        reg.register("every_15m", "*/15 * * * *")
        reg.register("multi_hour", "0 8,12,18 * * *")
        assert reg.get_trigger("every_15m") is not None
        assert reg.get_trigger("multi_hour") is not None


class TestTaskManagement:
    """Tests for pause_trigger, resume_trigger, get_trigger_status, trigger_now (Task 8)."""

    def _registry(self) -> CronTriggerRegistry:
        return CronTriggerRegistry(app=None)

    def test_pause_resume_toggle_enabled(self) -> None:
        reg = self._registry()
        reg.register("job", "0 * * * *")
        assert reg.get_trigger("job").enabled is True
        reg.pause_trigger("job")
        assert reg.get_trigger("job").enabled is False
        reg.resume_trigger("job")
        assert reg.get_trigger("job").enabled is True

    def test_pause_missing_raises(self) -> None:
        reg = self._registry()
        with pytest.raises(KeyError, match="not found"):
            reg.pause_trigger("missing")

    def test_resume_missing_raises(self) -> None:
        reg = self._registry()
        with pytest.raises(KeyError, match="not found"):
            reg.resume_trigger("missing")

    def test_get_trigger_status_returns_expected_fields(self) -> None:
        reg = self._registry()
        reg.register("daily", "0 9 * * *", focus="morning")
        status = reg.get_trigger_status("daily")
        assert status["event_name"] == "daily"
        assert status["enabled"] is True
        assert status["expression"] == "0 9 * * *"
        assert status["focus"] == "morning"
        assert "next_run" in status

    def test_get_trigger_status_missing_raises(self) -> None:
        reg = self._registry()
        with pytest.raises(KeyError, match="not found"):
            reg.get_trigger_status("missing")

    def test_get_trigger_status_invalid_expression_returns_none_next_run(self) -> None:
        reg = self._registry()
        reg.register("daily", "0 9 * * *", focus="morning")
        cfg = reg.get_trigger("daily")
        assert cfg is not None
        cfg.expression = "invalid cron expression"
        status = reg.get_trigger_status("daily")
        assert status["next_run"] is None

    @pytest.mark.asyncio
    async def test_trigger_now_calls_hatchet_run_task_now(self) -> None:
        reg = self._registry()
        reg.register("job", "0 * * * *")
        hatchet = MagicMock()
        hatchet.run_task_now = AsyncMock(return_value="run-123")
        reg.start(hatchet, agent_runtime=None, ledger=None)
        run_id = await reg.trigger_now("job")
        assert run_id == "run-123"
        hatchet.run_task_now.assert_awaited_once_with("cron_job")

    @pytest.mark.asyncio
    async def test_trigger_now_without_start_raises(self) -> None:
        reg = self._registry()
        reg.register("job", "0 * * * *")
        with pytest.raises(RuntimeError, match="start\\(\\)"):
            await reg.trigger_now("job")

    @pytest.mark.asyncio
    async def test_trigger_now_without_run_task_now_support_raises(self) -> None:
        reg = self._registry()
        reg.register("job", "0 * * * *")
        hatchet = MagicMock()
        # Simulate client missing async run_task_now capability
        if hasattr(hatchet, "run_task_now"):
            del hatchet.run_task_now
        reg.start(hatchet, agent_runtime=None, ledger=None)
        with pytest.raises(RuntimeError, match="run_task_now"):
            await reg.trigger_now("job")

    @pytest.mark.asyncio
    async def test_get_execution_history_missing_raises(self) -> None:
        reg = self._registry()
        reg.register("job", "0 * * * *")
        hatchet = MagicMock()
        ledger = MagicMock()
        reg.start(hatchet, agent_runtime=None, ledger=ledger)
        with pytest.raises(KeyError, match="not found"):
            await reg.get_execution_history("missing")

    @pytest.mark.asyncio
    async def test_get_execution_history_without_ledger_raises(self) -> None:
        reg = self._registry()
        reg.register("job", "0 * * * *")
        hatchet = MagicMock()
        reg.start(hatchet, agent_runtime=None, ledger=None)
        with pytest.raises(RuntimeError, match="Ledger"):
            await reg.get_execution_history("job")

    @pytest.mark.asyncio
    async def test_get_execution_history_returns_records(self) -> None:
        from datetime import datetime, timezone

        reg = self._registry()
        reg.register("daily", "0 9 * * *")
        hatchet = MagicMock()
        ledger = MagicMock()
        mock_rec = type("LedgerRecord", (), {})()
        mock_rec.run_id = "run-1"
        mock_rec.status = "success"
        mock_rec.created_at = datetime(2026, 2, 21, 9, 0, 0, tzinfo=timezone.utc)
        mock_rec.execution_time_ms = 150
        mock_rec.output_result = {"agent_run_id": "ar-1"}
        mock_rec.error_message = None
        ledger.query_records = AsyncMock(return_value=[mock_rec])
        reg.start(hatchet, agent_runtime=None, ledger=ledger)
        history = await reg.get_execution_history("daily", limit=5)
        assert len(history) == 1
        assert history[0]["run_id"] == "run-1"
        assert history[0]["status"] == "success"
        assert "2026-02-21" in (history[0]["created_at"] or "")
        assert history[0]["execution_time_ms"] == 150
        assert history[0]["agent_run_id"] == "ar-1"
        assert history[0]["error_message"] is None
