"""Unit tests for the @app.cron decorator (Task 4.4)."""

import pytest

from owlclaw.app import OwlClaw


class TestCronDecorator:
    """Tests for OwlClaw.cron() decorator."""

    def _app(self) -> OwlClaw:
        return OwlClaw("test-app")

    # ------------------------------------------------------------------
    # Task 4.3 — cron_registry attribute exists on app
    # ------------------------------------------------------------------

    def test_cron_registry_initialized(self) -> None:
        app = self._app()
        from owlclaw.triggers.cron import CronTriggerRegistry
        assert isinstance(app.cron_registry, CronTriggerRegistry)

    def test_cron_registry_starts_empty(self) -> None:
        app = self._app()
        assert app.cron_registry.list_triggers() == []

    # ------------------------------------------------------------------
    # Task 4.1-4.2 — decorator behaviour
    # ------------------------------------------------------------------

    def test_basic_decorator(self) -> None:
        app = self._app()

        @app.cron("0 * * * *")
        async def hourly_check():
            """Hourly health check."""
            pass

        config = app.cron_registry.get_trigger("hourly_check")
        assert config is not None
        assert config.expression == "0 * * * *"

    def test_explicit_event_name(self) -> None:
        app = self._app()

        @app.cron("0 9 * * 1-5", event_name="morning_open")
        async def morning():
            pass

        assert app.cron_registry.get_trigger("morning_open") is not None
        assert app.cron_registry.get_trigger("morning") is None

    def test_function_name_used_as_default(self) -> None:
        app = self._app()

        @app.cron("30 8 * * *")
        async def premarket_scan():
            pass

        assert app.cron_registry.get_trigger("premarket_scan") is not None

    def test_focus_parameter(self) -> None:
        app = self._app()

        @app.cron("0 9 * * 1-5", focus="inventory_monitor")
        async def inventory_check():
            pass

        config = app.cron_registry.get_trigger("inventory_check")
        assert config.focus == "inventory_monitor"

    def test_governance_kwargs(self) -> None:
        app = self._app()

        @app.cron(
            "0 0 * * *",
            max_daily_runs=1,
            cooldown_seconds=3600,
            max_cost_per_run=0.5,
        )
        async def daily_report():
            pass

        config = app.cron_registry.get_trigger("daily_report")
        assert config.max_daily_runs == 1
        assert config.cooldown_seconds == 3600
        assert config.max_cost_per_run == 0.5

    def test_function_used_as_default_fallback(self) -> None:
        app = self._app()

        @app.cron("0 * * * *")
        async def check():
            pass

        config = app.cron_registry.get_trigger("check")
        assert config.fallback_handler is not None

    def test_explicit_fallback(self) -> None:
        app = self._app()

        async def my_fallback():
            pass

        @app.cron("0 * * * *", fallback=my_fallback)
        async def another_check():
            pass

        config = app.cron_registry.get_trigger("another_check")
        assert config.fallback_handler is my_fallback

    def test_function_metadata_preserved(self) -> None:
        app = self._app()

        @app.cron("0 9 * * *")
        async def documented_task():
            """This doc should be preserved."""
            pass

        assert documented_task.__name__ == "documented_task"
        assert "preserved" in (documented_task.__doc__ or "")

    def test_invalid_expression_raises(self) -> None:
        app = self._app()
        with pytest.raises(ValueError, match="Invalid cron expression"):

            @app.cron("not-valid")
            async def bad_cron():
                pass

    def test_description_from_docstring(self) -> None:
        app = self._app()

        @app.cron("0 0 * * *")
        async def nightly_cleanup():
            """Clean up stale records nightly."""
            pass

        config = app.cron_registry.get_trigger("nightly_cleanup")
        assert config.description == "Clean up stale records nightly."

    def test_multiple_crons_registered(self) -> None:
        app = self._app()

        @app.cron("0 * * * *")
        async def task_a():
            pass

        @app.cron("0 9 * * *")
        async def task_b():
            pass

        @app.cron("0 0 * * *")
        async def task_c():
            pass

        assert len(app.cron_registry.list_triggers()) == 3
