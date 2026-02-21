"""Unit tests for CronTriggerRegistry cron expression validation (Task 2.3)."""

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

    def test_register_special_chars(self) -> None:
        reg = self._registry()
        reg.register("every_15m", "*/15 * * * *")
        reg.register("multi_hour", "0 8,12,18 * * *")
        assert reg.get_trigger("every_15m") is not None
        assert reg.get_trigger("multi_hour") is not None
