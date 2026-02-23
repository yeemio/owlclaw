"""Unit tests for BuiltInTools (agent-tools Task 6.4 subset)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from owlclaw.agent.tools import BuiltInTools, BuiltInToolsContext


class TestBuiltInToolsSchemas:
    def test_get_tool_schemas_returns_all_builtin_tools(self) -> None:
        tools = BuiltInTools()
        schemas = tools.get_tool_schemas()
        names = [s["function"]["name"] for s in schemas]
        assert "query_state" in names
        assert "log_decision" in names
        assert "schedule_once" in names
        assert "schedule_cron" in names
        assert "cancel_schedule" in names
        assert "remember" in names
        assert "recall" in names
        assert len(schemas) == 7

    def test_query_state_schema_has_required_state_name(self) -> None:
        tools = BuiltInTools()
        schemas = tools.get_tool_schemas()
        qs = next(s for s in schemas if s["function"]["name"] == "query_state")
        assert "state_name" in qs["function"]["parameters"]["properties"]
        assert "state_name" in qs["function"]["parameters"]["required"]

    def test_log_decision_schema_has_reasoning_and_decision_type(self) -> None:
        tools = BuiltInTools()
        schemas = tools.get_tool_schemas()
        ld = next(s for s in schemas if s["function"]["name"] == "log_decision")
        assert "reasoning" in ld["function"]["parameters"]["properties"]
        assert "reasoning" in ld["function"]["parameters"]["required"]
        assert "decision_type" in ld["function"]["parameters"]["properties"]


class TestBuiltInToolsIsBuiltin:
    def test_query_state_is_builtin(self) -> None:
        tools = BuiltInTools()
        assert tools.is_builtin("query_state") is True

    def test_log_decision_is_builtin(self) -> None:
        tools = BuiltInTools()
        assert tools.is_builtin("log_decision") is True

    def test_schedule_cron_is_builtin(self) -> None:
        tools = BuiltInTools()
        assert tools.is_builtin("schedule_cron") is True

    def test_unknown_tool_not_builtin(self) -> None:
        tools = BuiltInTools()
        assert tools.is_builtin("foo") is False

    def test_is_builtin_trims_whitespace(self) -> None:
        tools = BuiltInTools()
        assert tools.is_builtin(" query_state ") is True


class TestBuiltInToolsContextValidation:
    def test_context_trims_fields(self) -> None:
        ctx = BuiltInToolsContext(agent_id=" bot ", run_id=" r1 ", tenant_id=" default ")
        assert ctx.agent_id == "bot"
        assert ctx.run_id == "r1"
        assert ctx.tenant_id == "default"

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"agent_id": " ", "run_id": "r1"},
            {"agent_id": "bot", "run_id": ""},
            {"agent_id": "bot", "run_id": "r1", "tenant_id": " "},
        ],
    )
    def test_context_rejects_blank_fields(self, kwargs) -> None:
        with pytest.raises(ValueError, match="must be a non-empty string"):
            BuiltInToolsContext(**kwargs)  # type: ignore[arg-type]


class TestBuiltInToolsInitValidation:
    @pytest.mark.parametrize("timeout_value", [0, -1, float("nan"), float("inf"), True, "bad"])
    def test_init_rejects_invalid_timeout_seconds(self, timeout_value) -> None:
        with pytest.raises(ValueError, match="timeout_seconds must be a positive finite number"):
            BuiltInTools(timeout_seconds=timeout_value)  # type: ignore[arg-type]

    @pytest.mark.parametrize("task_name", ["", "   ", None, 123])
    def test_init_rejects_invalid_scheduled_run_task_name(self, task_name) -> None:
        with pytest.raises(ValueError, match="scheduled_run_task_name must be a non-empty string"):
            BuiltInTools(scheduled_run_task_name=task_name)  # type: ignore[arg-type]

    @pytest.mark.parametrize("max_calls", [0, -1, True, 1.2, "bad"])
    def test_init_rejects_invalid_max_calls_per_run(self, max_calls) -> None:
        with pytest.raises(ValueError, match="max_calls_per_run must be a positive integer"):
            BuiltInTools(max_calls_per_run=max_calls)  # type: ignore[arg-type]

    @pytest.mark.parametrize("raise_errors", ["yes", 1, None])
    def test_init_rejects_invalid_raise_errors(self, raise_errors) -> None:
        with pytest.raises(ValueError, match="raise_errors must be a boolean"):
            BuiltInTools(raise_errors=raise_errors)  # type: ignore[arg-type]


class TestQueryState:
    @pytest.mark.asyncio
    async def test_query_state_success(self) -> None:
        reg = AsyncMock()
        reg.get_state.return_value = {"is_trading": True}
        ledger = AsyncMock()
        tools = BuiltInTools(capability_registry=reg, ledger=ledger)
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")

        result = await tools.execute(
            "query_state",
            {"state_name": "market_state"},
            ctx,
        )
        assert result == {"state": {"is_trading": True}}
        reg.get_state.assert_awaited_once_with("market_state")
        ledger.record_execution.assert_awaited_once()
        assert ledger.record_execution.call_args.kwargs["capability_name"] == "query_state"

    @pytest.mark.asyncio
    async def test_query_state_no_registry_returns_error(self) -> None:
        tools = BuiltInTools(capability_registry=None)
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")
        result = await tools.execute("query_state", {"state_name": "x"}, ctx)
        assert "error" in result
        assert "registry" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_query_state_missing_state_name_returns_error(self) -> None:
        reg = AsyncMock()
        tools = BuiltInTools(capability_registry=reg)
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")
        result = await tools.execute("query_state", {}, ctx)
        assert "error" in result
        assert "state_name" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_query_state_whitespace_state_name_returns_error(self) -> None:
        reg = AsyncMock()
        tools = BuiltInTools(capability_registry=reg)
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")
        result = await tools.execute("query_state", {"state_name": "   "}, ctx)
        assert "error" in result
        assert "state_name" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_query_state_value_error_returns_error(self) -> None:
        reg = AsyncMock()
        reg.get_state.side_effect = ValueError("unknown state 'foo'")
        tools = BuiltInTools(capability_registry=reg)
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")
        result = await tools.execute("query_state", {"state_name": "foo"}, ctx)
        assert "error" in result
        assert "unknown state" in result["error"]


class TestLogDecision:
    @pytest.mark.asyncio
    async def test_log_decision_success(self) -> None:
        ledger = AsyncMock()
        tools = BuiltInTools(ledger=ledger)
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")

        result = await tools.execute(
            "log_decision",
            {"reasoning": "no action needed", "decision_type": "no_action"},
            ctx,
        )
        assert result["logged"] is True
        assert "decision_id" in result
        assert result["decision_id"].startswith("decision-")
        ledger.record_execution.assert_awaited_once()
        call = ledger.record_execution.call_args
        assert call.kwargs["capability_name"] == "log_decision"
        assert call.kwargs["task_type"] == "decision_log"
        assert call.kwargs["decision_reasoning"] == "no action needed"
        assert call.kwargs["input_params"]["decision_type"] == "no_action"
        assert call.kwargs["output_result"]["decision_id"] == result["decision_id"]

    @pytest.mark.asyncio
    async def test_log_decision_id_is_unique_per_call(self) -> None:
        ledger = AsyncMock()
        tools = BuiltInTools(ledger=ledger)
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")

        r1 = await tools.execute("log_decision", {"reasoning": "a"}, ctx)
        r2 = await tools.execute("log_decision", {"reasoning": "b"}, ctx)

        assert r1["logged"] is True and r2["logged"] is True
        assert r1["decision_id"] != r2["decision_id"]

    @pytest.mark.asyncio
    async def test_log_decision_no_ledger_returns_no_ledger(self) -> None:
        tools = BuiltInTools(ledger=None)
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")
        result = await tools.execute(
            "log_decision",
            {"reasoning": "ok"},
            ctx,
        )
        assert result["logged"] is False
        assert result["decision_id"] == "no-ledger"

    @pytest.mark.asyncio
    async def test_log_decision_empty_reasoning_returns_error(self) -> None:
        tools = BuiltInTools()
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")
        result = await tools.execute("log_decision", {"reasoning": ""}, ctx)
        assert "error" in result
        assert "reasoning" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_log_decision_reasoning_over_1000_returns_error(self) -> None:
        tools = BuiltInTools()
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")
        result = await tools.execute(
            "log_decision",
            {"reasoning": "x" * 1001},
            ctx,
        )
        assert "error" in result
        assert "1000" in result["error"]

    @pytest.mark.asyncio
    async def test_log_decision_invalid_decision_type_defaults_to_other(self) -> None:
        ledger = AsyncMock()
        tools = BuiltInTools(ledger=ledger)
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")
        result = await tools.execute(
            "log_decision",
            {"reasoning": "ok", "decision_type": "invalid"},
            ctx,
        )
        assert result["logged"] is True
        call = ledger.record_execution.call_args
        assert call.kwargs["input_params"]["decision_type"] == "other"


class TestScheduleOnce:
    @pytest.mark.asyncio
    async def test_schedule_once_success(self) -> None:
        hatchet = AsyncMock()
        hatchet.schedule_task.return_value = "run-123"
        ledger = AsyncMock()
        tools = BuiltInTools(hatchet_client=hatchet, ledger=ledger)
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")
        result = await tools.execute(
            "schedule_once",
            {"delay_seconds": 300, "focus": "check entry"},
            ctx,
        )
        assert result["schedule_id"] == "run-123"
        assert result["focus"] == "check entry"
        hatchet.schedule_task.assert_awaited_once_with(
            "agent_scheduled_run",
            300,
            agent_id="bot",
            trigger="schedule_once",
            focus="check entry",
            scheduled_by_run_id="r1",
            tenant_id="default",
        )
        ledger.record_execution.assert_awaited_once()
        assert ledger.record_execution.call_args.kwargs["capability_name"] == "schedule_once"

    @pytest.mark.asyncio
    async def test_schedule_once_no_hatchet_returns_error(self) -> None:
        ledger = AsyncMock()
        tools = BuiltInTools(hatchet_client=None, ledger=ledger)
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")
        result = await tools.execute(
            "schedule_once",
            {"delay_seconds": 60, "focus": "x"},
            ctx,
        )
        assert "error" in result
        assert "Hatchet" in result["error"]
        ledger.record_execution.assert_awaited_once()
        assert ledger.record_execution.call_args.kwargs["status"] == "validation_error"

    @pytest.mark.asyncio
    async def test_schedule_once_whitespace_focus_returns_error(self) -> None:
        tools = BuiltInTools()
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")
        result = await tools.execute(
            "schedule_once",
            {"delay_seconds": 60, "focus": "   "},
            ctx,
        )
        assert "error" in result
        assert "focus" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_schedule_once_invalid_delay_returns_error(self) -> None:
        tools = BuiltInTools()
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")
        result = await tools.execute(
            "schedule_once",
            {"delay_seconds": 0, "focus": "x"},
            ctx,
        )
        assert "error" in result
        assert "2592000" in result["error"]

    @pytest.mark.asyncio
    async def test_schedule_once_bool_delay_returns_error(self) -> None:
        tools = BuiltInTools()
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")
        result = await tools.execute(
            "schedule_once",
            {"delay_seconds": True, "focus": "x"},
            ctx,
        )
        assert "error" in result
        assert "integer" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_schedule_once_delay_seconds_over_max_returns_error(self) -> None:
        tools = BuiltInTools()
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")
        result = await tools.execute(
            "schedule_once",
            {"delay_seconds": 2592001, "focus": "x"},
            ctx,
        )
        assert "error" in result
        assert "2592000" in result["error"]


class TestScheduleCron:
    @pytest.mark.asyncio
    async def test_schedule_cron_success(self) -> None:
        hatchet = AsyncMock()
        hatchet.schedule_cron = AsyncMock(return_value="cron-abc")
        tools = BuiltInTools(hatchet_client=hatchet)
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")
        result = await tools.execute(
            "schedule_cron",
            {"cron_expression": "0 9 * * 1-5", "focus": "morning check"},
            ctx,
        )
        assert result["schedule_id"] == "cron-abc"
        assert result["cron_name"].startswith("agent_cron_bot_")
        assert result["cron_expression"] == "0 9 * * 1-5"
        assert result["focus"] == "morning check"
        hatchet.schedule_cron.assert_awaited_once()
        call = hatchet.schedule_cron.call_args
        assert call.kwargs["workflow_name"] == "agent_scheduled_run"
        assert call.kwargs["expression"] == "0 9 * * 1-5"
        assert "agent_cron_bot_" in call.kwargs["cron_name"]
        assert call.kwargs["input_data"]["focus"] == "morning check"
        assert call.kwargs["input_data"]["trigger"] == "schedule_cron"

    @pytest.mark.asyncio
    async def test_schedule_cron_sanitizes_agent_id_in_cron_name(self) -> None:
        hatchet = AsyncMock()
        hatchet.schedule_cron = AsyncMock(return_value="cron-abc")
        tools = BuiltInTools(hatchet_client=hatchet)
        ctx = BuiltInToolsContext(agent_id="bot prod/v1", run_id="r1")
        await tools.execute(
            "schedule_cron",
            {"cron_expression": "0 9 * * 1-5", "focus": "morning check"},
            ctx,
        )
        cron_name = hatchet.schedule_cron.call_args.kwargs["cron_name"]
        assert cron_name.startswith("agent_cron_bot_prod_v1_")

    @pytest.mark.asyncio
    async def test_schedule_cron_no_hatchet_returns_error(self) -> None:
        tools = BuiltInTools(hatchet_client=None)
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")
        result = await tools.execute(
            "schedule_cron",
            {"cron_expression": "0 9 * * *", "focus": "daily"},
            ctx,
        )
        assert "error" in result
        assert "Hatchet" in result["error"]

    @pytest.mark.asyncio
    async def test_schedule_cron_invalid_expression_returns_error(self) -> None:
        hatchet = AsyncMock()
        tools = BuiltInTools(hatchet_client=hatchet)
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")
        result = await tools.execute(
            "schedule_cron",
            {"cron_expression": "invalid", "focus": "x"},
            ctx,
        )
        assert "error" in result
        assert "Invalid cron" in result["error"]
        hatchet.schedule_cron.assert_not_awaited()


class TestCancelSchedule:
    @pytest.mark.asyncio
    async def test_cancel_schedule_success(self) -> None:
        hatchet = AsyncMock()
        hatchet.cancel_task.return_value = True
        tools = BuiltInTools(hatchet_client=hatchet)
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")
        result = await tools.execute(
            "cancel_schedule",
            {"schedule_id": "run-123"},
            ctx,
        )
        assert result["cancelled"] is True
        assert result["schedule_id"] == "run-123"
        hatchet.cancel_task.assert_awaited_once_with("run-123")

    @pytest.mark.asyncio
    async def test_cancel_schedule_coerces_truthy_result_to_bool(self) -> None:
        hatchet = AsyncMock()
        hatchet.cancel_task.return_value = "ok"
        tools = BuiltInTools(hatchet_client=hatchet)
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")
        result = await tools.execute(
            "cancel_schedule",
            {"schedule_id": "run-123"},
            ctx,
        )
        assert result["cancelled"] is True

    @pytest.mark.asyncio
    async def test_cancel_schedule_no_hatchet_returns_error(self) -> None:
        tools = BuiltInTools(hatchet_client=None)
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")
        result = await tools.execute(
            "cancel_schedule",
            {"schedule_id": "run-123"},
            ctx,
        )
        assert "error" in result
        assert "Hatchet" in result["error"]

    @pytest.mark.asyncio
    async def test_cancel_schedule_whitespace_id_returns_error(self) -> None:
        tools = BuiltInTools(hatchet_client=AsyncMock())
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")
        result = await tools.execute(
            "cancel_schedule",
            {"schedule_id": "   "},
            ctx,
        )
        assert "error" in result
        assert "schedule_id" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_cancel_schedule_task_not_found_returns_cancelled_false(self) -> None:
        hatchet = AsyncMock()
        hatchet.cancel_task.return_value = False
        hatchet.cancel_cron = AsyncMock(return_value=False)
        ledger = AsyncMock()
        tools = BuiltInTools(hatchet_client=hatchet, ledger=ledger)
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")
        result = await tools.execute(
            "cancel_schedule",
            {"schedule_id": "nonexistent-run"},
            ctx,
        )
        assert result["cancelled"] is False
        assert result["schedule_id"] == "nonexistent-run"
        hatchet.cancel_task.assert_awaited_once_with("nonexistent-run")
        ledger.record_execution.assert_awaited_once()
        assert ledger.record_execution.call_args.kwargs["status"] == "not_found"

    @pytest.mark.asyncio
    async def test_cancel_schedule_cancel_cron_timeout_returns_error(self) -> None:
        async def _slow_cancel_cron(_: str) -> bool:
            await asyncio.sleep(0.05)
            return False

        hatchet = AsyncMock()
        hatchet.cancel_task.return_value = False
        hatchet.cancel_cron.side_effect = _slow_cancel_cron
        tools = BuiltInTools(hatchet_client=hatchet, timeout_seconds=0.01)
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")
        result = await tools.execute(
            "cancel_schedule",
            {"schedule_id": "cron-1"},
            ctx,
        )
        assert "error" in result
        assert "timed out" in result["error"]


class TestExecuteUnknownTool:
    @pytest.mark.asyncio
    async def test_execute_unknown_tool_raises(self) -> None:
        tools = BuiltInTools()
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")
        with pytest.raises(ValueError, match="Unknown built-in tool"):
            await tools.execute("unknown_tool", {}, ctx)

    @pytest.mark.asyncio
    async def test_execute_non_object_arguments_returns_error(self) -> None:
        tools = BuiltInTools()
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")
        result = await tools.execute("query_state", "bad-args", ctx)  # type: ignore[arg-type]
        assert "error" in result
        assert "JSON object" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_trims_tool_name_before_dispatch(self) -> None:
        reg = AsyncMock()
        reg.get_state.return_value = {"ok": True}
        tools = BuiltInTools(capability_registry=reg)
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")
        result = await tools.execute(" query_state ", {"state_name": "x"}, ctx)
        assert result == {"state": {"ok": True}}

    @pytest.mark.asyncio
    async def test_execute_enforces_max_calls_per_run(self) -> None:
        reg = AsyncMock()
        reg.get_state.return_value = {"ok": True}
        ledger = AsyncMock()
        tools = BuiltInTools(capability_registry=reg, ledger=ledger, max_calls_per_run=1)
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")

        first = await tools.execute("query_state", {"state_name": "x"}, ctx)
        second = await tools.execute("query_state", {"state_name": "x"}, ctx)

        assert first == {"state": {"ok": True}}
        assert "error" in second
        assert "max_calls_per_run=1" in second["error"]

    @pytest.mark.asyncio
    async def test_execute_limit_is_concurrency_safe(self) -> None:
        reg = AsyncMock()
        reg.get_state.return_value = {"ok": True}
        tools = BuiltInTools(capability_registry=reg, max_calls_per_run=1)
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")

        results = await asyncio.gather(
            tools.execute("query_state", {"state_name": "x"}, ctx),
            tools.execute("query_state", {"state_name": "x"}, ctx),
        )

        success_count = sum(1 for item in results if "state" in item)
        error_count = sum(1 for item in results if "error" in item)
        assert success_count == 1
        assert error_count == 1

    @pytest.mark.asyncio
    async def test_reset_run_call_budget_allows_new_calls(self) -> None:
        reg = AsyncMock()
        reg.get_state.return_value = {"ok": True}
        tools = BuiltInTools(capability_registry=reg, max_calls_per_run=1)
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")

        first = await tools.execute("query_state", {"state_name": "x"}, ctx)
        blocked = await tools.execute("query_state", {"state_name": "x"}, ctx)
        tools.reset_run_call_budget("r1")
        after_reset = await tools.execute("query_state", {"state_name": "x"}, ctx)

        assert "state" in first
        assert "error" in blocked
        assert "state" in after_reset

    @pytest.mark.asyncio
    async def test_raise_errors_converts_validation_error(self) -> None:
        tools = BuiltInTools(raise_errors=True)
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")
        with pytest.raises(ValueError, match="state_name is required"):
            await tools.execute("query_state", {}, ctx)

    @pytest.mark.asyncio
    async def test_raise_errors_converts_runtime_error(self) -> None:
        reg = AsyncMock()
        reg.get_state.side_effect = RuntimeError("dependency down")
        tools = BuiltInTools(capability_registry=reg, raise_errors=True)
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")
        with pytest.raises(RuntimeError, match="query_state failed: dependency down"):
            await tools.execute("query_state", {"state_name": "market_state"}, ctx)

    @pytest.mark.asyncio
    async def test_raise_errors_converts_timeout_error(self) -> None:
        async def _slow_cancel_cron(_: str) -> bool:
            await asyncio.sleep(0.05)
            return False

        hatchet = AsyncMock()
        hatchet.cancel_task.return_value = False
        hatchet.cancel_cron.side_effect = _slow_cancel_cron
        tools = BuiltInTools(hatchet_client=hatchet, timeout_seconds=0.01, raise_errors=True)
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")
        with pytest.raises(TimeoutError, match="cancel_schedule timed out"):
            await tools.execute("cancel_schedule", {"schedule_id": "cron-1"}, ctx)


class TestMemoryTools:
    @pytest.mark.asyncio
    async def test_remember_success(self) -> None:
        memory = AsyncMock()
        memory.write.return_value = {"memory_id": "m1", "created_at": "2026-01-01T00:00:00Z"}
        ledger = AsyncMock()
        tools = BuiltInTools(memory_system=memory, ledger=ledger)
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")
        result = await tools.execute("remember", {"content": "lesson", "tags": ["Ops", "ops"]}, ctx)
        assert result["memory_id"] == "m1"
        assert result["tags"] == ["ops"]
        memory.write.assert_awaited_once_with(content="lesson", tags=["ops"])
        assert ledger.record_execution.await_count == 1
        assert ledger.record_execution.call_args.kwargs["capability_name"] == "remember"

    @pytest.mark.asyncio
    async def test_remember_no_memory_returns_error(self) -> None:
        tools = BuiltInTools(memory_system=None)
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")
        result = await tools.execute("remember", {"content": "lesson"}, ctx)
        assert "error" in result
        assert "memory system" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_remember_content_validation(self) -> None:
        tools = BuiltInTools(memory_system=AsyncMock())
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")
        result = await tools.execute("remember", {"content": "   "}, ctx)
        assert "error" in result
        result = await tools.execute("remember", {"content": "x" * 2001}, ctx)
        assert "error" in result
        assert "2000" in result["error"]

    @pytest.mark.asyncio
    async def test_recall_success(self) -> None:
        memory = AsyncMock()
        memory.search.return_value = [{"content": "lesson a"}, {"content": "lesson b"}]
        ledger = AsyncMock()
        tools = BuiltInTools(memory_system=memory, ledger=ledger)
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")
        result = await tools.execute("recall", {"query": "lesson", "limit": 2, "tags": ["Trade"]}, ctx)
        assert result["count"] == 2
        assert len(result["memories"]) == 2
        memory.search.assert_awaited_once_with(query="lesson", limit=2, tags=["trade"])
        assert ledger.record_execution.await_count == 1
        assert ledger.record_execution.call_args.kwargs["capability_name"] == "recall"

    @pytest.mark.asyncio
    async def test_recall_limit_validation(self) -> None:
        tools = BuiltInTools(memory_system=AsyncMock())
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")
        result = await tools.execute("recall", {"query": "x", "limit": 0}, ctx)
        assert "error" in result
        assert "between 1 and 20" in result["error"]

    @pytest.mark.asyncio
    async def test_recall_no_results_returns_empty_list(self) -> None:
        memory = AsyncMock()
        memory.search.return_value = []
        tools = BuiltInTools(memory_system=memory)
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")
        result = await tools.execute("recall", {"query": "missing"}, ctx)
        assert result == {"memories": [], "count": 0}

    @pytest.mark.asyncio
    async def test_recall_no_memory_returns_error(self) -> None:
        tools = BuiltInTools(memory_system=None)
        ctx = BuiltInToolsContext(agent_id="bot", run_id="r1")
        result = await tools.execute("recall", {"query": "lesson"}, ctx)
        assert "error" in result
        assert "memory system" in result["error"].lower()
