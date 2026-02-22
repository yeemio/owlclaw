"""Unit tests for AgentRuntime (Tasks 6/7/8)."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlclaw.agent.runtime.context import AgentRunContext
from owlclaw.agent.runtime.runtime import AgentRuntime

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_app_dir(tmp_path):
    """Create minimal SOUL.md in tmp_path, return str path."""
    (tmp_path / "SOUL.md").write_text(
        "You are a helpful assistant.", encoding="utf-8"
    )
    return str(tmp_path)


def _make_llm_response(content="Done.", tool_calls=None):
    """Build a fake litellm response object."""
    message = MagicMock()
    message.content = content
    message.tool_calls = tool_calls or []
    message.model_dump.return_value = {
        "role": "assistant",
        "content": content,
        "tool_calls": tool_calls or [],
    }
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


def _make_llm_response_dict_message(content="Done.", tool_calls=None):
    """Build a fake litellm response whose message is already a dict."""
    choice = MagicMock()
    choice.message = {
        "role": "assistant",
        "content": content,
        "tool_calls": tool_calls or [],
    }
    response = MagicMock()
    response.choices = [choice]
    return response


def _make_tool_call(name: str, arguments: dict):
    tc = MagicMock()
    tc.id = "tc_1"
    tc.function.name = name
    tc.function.arguments = json.dumps(arguments)
    return tc


def _make_tool_call_raw(name: str, raw_arguments):
    tc = MagicMock()
    tc.id = "tc_1"
    tc.function.name = name
    tc.function.arguments = raw_arguments
    return tc


# ---------------------------------------------------------------------------
# AgentRunContext
# ---------------------------------------------------------------------------


class TestAgentRunContext:
    def test_defaults(self) -> None:
        ctx = AgentRunContext(agent_id="bot", trigger="cron")
        assert ctx.tenant_id == "default"
        assert ctx.focus is None
        assert ctx.payload == {}
        assert len(ctx.run_id) == 36  # UUID

    def test_custom_run_id(self) -> None:
        ctx = AgentRunContext(agent_id="bot", trigger="cron", run_id="my-id")
        assert ctx.run_id == "my-id"


# ---------------------------------------------------------------------------
# AgentRuntime — lifecycle
# ---------------------------------------------------------------------------


class TestAgentRuntimeLifecycle:
    async def test_run_before_setup_raises(self, tmp_path) -> None:
        rt = AgentRuntime(agent_id="bot", app_dir=_make_app_dir(tmp_path))
        ctx = AgentRunContext(agent_id="bot", trigger="cron")
        with pytest.raises(RuntimeError, match="setup\\(\\)"):
            await rt.run(ctx)

    async def test_setup_missing_soul_raises(self, tmp_path) -> None:
        rt = AgentRuntime(agent_id="bot", app_dir=str(tmp_path))
        with pytest.raises(FileNotFoundError, match="SOUL.md"):
            await rt.setup()

    async def test_setup_success(self, tmp_path) -> None:
        rt = AgentRuntime(agent_id="bot", app_dir=_make_app_dir(tmp_path))
        await rt.setup()
        assert rt.is_initialized is True


# ---------------------------------------------------------------------------
# AgentRuntime — trigger_event and run
# ---------------------------------------------------------------------------


class TestAgentRuntimeRun:
    @patch("owlclaw.agent.runtime.runtime.llm_integration.acompletion")
    async def test_trigger_event_returns_completed(
        self, mock_llm, tmp_path
    ) -> None:
        mock_llm.return_value = _make_llm_response("All done.")
        rt = AgentRuntime(agent_id="bot", app_dir=_make_app_dir(tmp_path))
        await rt.setup()
        result = await rt.trigger_event("morning_check", focus="markets")
        assert result["status"] == "completed"
        assert "run_id" in result

    @patch("owlclaw.agent.runtime.runtime.llm_integration.acompletion")
    async def test_run_returns_iteration_count(self, mock_llm, tmp_path) -> None:
        mock_llm.return_value = _make_llm_response("Done.")
        rt = AgentRuntime(agent_id="bot", app_dir=_make_app_dir(tmp_path))
        await rt.setup()
        ctx = AgentRunContext(agent_id="bot", trigger="cron")
        result = await rt.run(ctx)
        assert result["iterations"] >= 1

    @patch("owlclaw.agent.runtime.runtime.llm_integration.acompletion")
    async def test_focus_used_in_user_message(self, mock_llm, tmp_path) -> None:
        """Focus should appear in the user message sent to LLM."""
        mock_llm.return_value = _make_llm_response()
        rt = AgentRuntime(agent_id="bot", app_dir=_make_app_dir(tmp_path))
        await rt.setup()
        await rt.trigger_event("check", focus="inventory_monitor")
        call_messages = mock_llm.call_args.kwargs["messages"]
        user_msg = next(m for m in call_messages if m["role"] == "user")
        assert "inventory_monitor" in user_msg["content"]

    @patch("owlclaw.agent.runtime.runtime.llm_integration.acompletion")
    async def test_trigger_event_normalizes_blank_focus(self, mock_llm, tmp_path) -> None:
        """Blank focus strings should be normalized to None."""
        mock_llm.return_value = _make_llm_response()
        rt = AgentRuntime(agent_id="bot", app_dir=_make_app_dir(tmp_path))
        await rt.setup()
        await rt.trigger_event("check", focus="   ")
        call_messages = mock_llm.call_args.kwargs["messages"]
        user_msg = next(m for m in call_messages if m["role"] == "user")
        assert "Focus:" not in user_msg["content"]

    def test_skill_focus_match_uses_owlclaw_focus(self, tmp_path) -> None:
        """Focus matching should prioritize owlclaw.focus extension field."""
        rt = AgentRuntime(agent_id="bot", app_dir=_make_app_dir(tmp_path))
        skill = MagicMock()
        skill.owlclaw_config = {"focus": ["Inventory_Monitor", "ops"]}
        skill.metadata = {"tags": ["legacy-tag"]}
        rt.registry = MagicMock()
        rt.registry.skills_loader.get_skill.return_value = skill
        assert rt._skill_has_focus("x", "inventory_monitor") is True

    def test_skill_focus_match_falls_back_to_metadata_tags(self, tmp_path) -> None:
        """Legacy skills without owlclaw.focus still match via metadata.tags."""
        rt = AgentRuntime(agent_id="bot", app_dir=_make_app_dir(tmp_path))
        skill = MagicMock()
        skill.owlclaw_config = {}
        skill.metadata = {"tags": ["inventory_monitor"]}
        rt.registry = MagicMock()
        rt.registry.skills_loader.get_skill.return_value = skill
        assert rt._skill_has_focus("x", "inventory_monitor") is True

    def test_skill_focus_declared_disables_metadata_tag_fallback(self, tmp_path) -> None:
        """When owlclaw.focus is declared, metadata.tags should not override it."""
        rt = AgentRuntime(agent_id="bot", app_dir=_make_app_dir(tmp_path))
        skill = MagicMock()
        skill.owlclaw_config = {"focus": ["ops"]}
        skill.metadata = {"tags": ["inventory_monitor"]}
        rt.registry = MagicMock()
        rt.registry.skills_loader.get_skill.return_value = skill
        assert rt._skill_has_focus("x", "inventory_monitor") is False

    def test_build_skills_context_empty_when_focus_has_no_match(self, tmp_path) -> None:
        """When focus is set and no skill matches, no skill knowledge should be injected."""
        rt = AgentRuntime(agent_id="bot", app_dir=_make_app_dir(tmp_path))
        rt.registry = MagicMock()
        rt.registry.handlers = {"skill-a": MagicMock()}
        rt.registry.skills_loader.get_skill.return_value = MagicMock(
            owlclaw_config={"focus": ["other"]},
            metadata={},
        )
        rt.knowledge_injector = MagicMock()
        ctx = AgentRunContext(agent_id="bot", trigger="cron", focus="inventory_monitor")
        assert rt._build_skills_context(ctx) == ""
        rt.knowledge_injector.get_skills_knowledge.assert_not_called()

    def test_build_skills_context_includes_only_focus_matches(self, tmp_path) -> None:
        """When focus is set, only matching skills are passed to knowledge injector."""
        rt = AgentRuntime(agent_id="bot", app_dir=_make_app_dir(tmp_path))
        rt.registry = MagicMock()
        rt.registry.handlers = {"skill-a": MagicMock(), "skill-b": MagicMock()}

        def _get_skill(name):  # type: ignore[no-untyped-def]
            if name == "skill-a":
                return MagicMock(owlclaw_config={"focus": ["inventory_monitor"]}, metadata={})
            return MagicMock(owlclaw_config={"focus": ["ops"]}, metadata={})

        rt.registry.skills_loader.get_skill.side_effect = _get_skill
        rt.knowledge_injector = MagicMock()
        rt.knowledge_injector.get_skills_knowledge.return_value = "focused"
        ctx = AgentRunContext(agent_id="bot", trigger="cron", focus="inventory_monitor")
        result = rt._build_skills_context(ctx)
        assert result == "focused"
        rt.knowledge_injector.get_skills_knowledge.assert_called_once_with(["skill-a"])

    def test_capability_schemas_sorted_by_name(self, tmp_path) -> None:
        """Capability schema order should be deterministic by name."""
        rt = AgentRuntime(agent_id="bot", app_dir=_make_app_dir(tmp_path))
        rt.registry = MagicMock()
        rt.registry.list_capabilities.return_value = [
            {"name": "z-skill", "description": "z"},
            {"name": "a-skill", "description": "a"},
        ]
        schemas = rt._capability_schemas()
        names = [item["function"]["name"] for item in schemas]
        assert names == ["a-skill", "z-skill"]

    @patch("owlclaw.agent.runtime.runtime.llm_integration.acompletion")
    async def test_accepts_dict_assistant_message(self, mock_llm, tmp_path) -> None:
        """Runtime should support providers returning dict message objects."""
        mock_llm.return_value = _make_llm_response_dict_message("Dict done.")
        rt = AgentRuntime(agent_id="bot", app_dir=_make_app_dir(tmp_path))
        await rt.setup()
        result = await rt.trigger_event("cron")
        assert result["status"] == "completed"
        assert result["final_response"] == "Dict done."

    @patch("owlclaw.agent.runtime.runtime.llm_integration.acompletion")
    async def test_tool_call_dispatched_to_registry(
        self, mock_llm, tmp_path
    ) -> None:
        """When LLM returns a tool_call, the registry is invoked."""
        tc = _make_tool_call("market_scan", {"symbol": "AAPL"})
        # First response has a tool call; second response completes
        mock_llm.side_effect = [
            _make_llm_response(tool_calls=[tc]),
            _make_llm_response("Completed."),
        ]

        registry = MagicMock()
        registry.handlers = {"market_scan": MagicMock()}
        registry.list_capabilities.return_value = [
            {"name": "market_scan", "description": "Scans market data"}
        ]
        registry.invoke_handler = AsyncMock(return_value={"price": 180})

        rt = AgentRuntime(
            agent_id="bot",
            app_dir=_make_app_dir(tmp_path),
            registry=registry,
        )
        await rt.setup()
        ctx = AgentRunContext(agent_id="bot", trigger="cron")
        result = await rt.run(ctx)
        registry.invoke_handler.assert_called_once_with("market_scan", symbol="AAPL")
        assert result["tool_calls_total"] == 1

    @patch("owlclaw.agent.runtime.runtime.llm_integration.acompletion")
    async def test_tool_call_kwargs_wrapper_unwrapped(
        self, mock_llm, tmp_path
    ) -> None:
        """Legacy {"kwargs": {...}} payload should be unwrapped before invoke."""
        tc = _make_tool_call("market_scan", {"kwargs": {"symbol": "AAPL"}})
        mock_llm.side_effect = [
            _make_llm_response(tool_calls=[tc]),
            _make_llm_response("Completed."),
        ]

        registry = MagicMock()
        registry.handlers = {"market_scan": MagicMock()}
        registry.list_capabilities.return_value = [
            {"name": "market_scan", "description": "Scans market data"}
        ]
        registry.invoke_handler = AsyncMock(return_value={"price": 180})

        rt = AgentRuntime(
            agent_id="bot",
            app_dir=_make_app_dir(tmp_path),
            registry=registry,
        )
        await rt.setup()
        ctx = AgentRunContext(agent_id="bot", trigger="cron")
        await rt.run(ctx)
        registry.invoke_handler.assert_called_once_with("market_scan", symbol="AAPL")

    @patch("owlclaw.agent.runtime.runtime.llm_integration.acompletion")
    async def test_tool_call_without_args_injects_session(
        self, mock_llm, tmp_path
    ) -> None:
        """No-arg calls should pass a default session payload to handlers."""
        tc = _make_tool_call("market_scan", {})
        mock_llm.side_effect = [
            _make_llm_response(tool_calls=[tc]),
            _make_llm_response("Completed."),
        ]

        registry = MagicMock()
        registry.handlers = {"market_scan": MagicMock()}
        registry.list_capabilities.return_value = [
            {"name": "market_scan", "description": "Scans market data"}
        ]
        registry.invoke_handler = AsyncMock(return_value={"ok": True})

        rt = AgentRuntime(
            agent_id="bot",
            app_dir=_make_app_dir(tmp_path),
            registry=registry,
        )
        await rt.setup()
        ctx = AgentRunContext(agent_id="bot", trigger="cron")
        await rt.run(ctx)

        call = registry.invoke_handler.call_args
        assert call.args == ("market_scan",)
        assert "session" in call.kwargs
        assert call.kwargs["session"]["trigger"] == "cron"

    @patch("owlclaw.agent.runtime.runtime.llm_integration.acompletion")
    async def test_tool_not_registered_returns_error_dict(
        self, mock_llm, tmp_path
    ) -> None:
        tc = _make_tool_call("nonexistent_tool", {})
        mock_llm.side_effect = [
            _make_llm_response(tool_calls=[tc]),
            _make_llm_response("ok"),
        ]

        registry = MagicMock()
        registry.handlers = {}
        registry.list_capabilities.return_value = []
        registry.invoke_handler = AsyncMock(side_effect=ValueError("not found"))

        rt = AgentRuntime(
            agent_id="bot",
            app_dir=_make_app_dir(tmp_path),
            registry=registry,
        )
        await rt.setup()
        ctx = AgentRunContext(agent_id="bot", trigger="cron")
        result = await rt.run(ctx)
        # The loop should still complete without raising
        assert result["status"] == "completed"

    @patch("owlclaw.agent.runtime.runtime.llm_integration.acompletion")
    async def test_tool_invalid_json_arguments_not_executed(
        self, mock_llm, tmp_path
    ) -> None:
        tc = _make_tool_call_raw("market_scan", "{not-json")
        mock_llm.side_effect = [
            _make_llm_response(tool_calls=[tc]),
            _make_llm_response("ok"),
        ]

        registry = MagicMock()
        registry.handlers = {"market_scan": MagicMock()}
        registry.list_capabilities.return_value = [
            {"name": "market_scan", "description": "Scans market data"}
        ]
        registry.invoke_handler = AsyncMock(return_value={"price": 180})

        rt = AgentRuntime(
            agent_id="bot",
            app_dir=_make_app_dir(tmp_path),
            registry=registry,
        )
        await rt.setup()
        result = await rt.run(AgentRunContext(agent_id="bot", trigger="cron"))
        assert result["status"] == "completed"
        registry.invoke_handler.assert_not_called()

    @patch("owlclaw.agent.runtime.runtime.llm_integration.acompletion")
    async def test_tool_non_object_arguments_not_executed(
        self, mock_llm, tmp_path
    ) -> None:
        tc = _make_tool_call_raw("market_scan", json.dumps(["not", "object"]))
        mock_llm.side_effect = [
            _make_llm_response(tool_calls=[tc]),
            _make_llm_response("ok"),
        ]

        registry = MagicMock()
        registry.handlers = {"market_scan": MagicMock()}
        registry.list_capabilities.return_value = [
            {"name": "market_scan", "description": "Scans market data"}
        ]
        registry.invoke_handler = AsyncMock(return_value={"price": 180})

        rt = AgentRuntime(
            agent_id="bot",
            app_dir=_make_app_dir(tmp_path),
            registry=registry,
        )
        await rt.setup()
        result = await rt.run(AgentRunContext(agent_id="bot", trigger="cron"))
        assert result["status"] == "completed"
        registry.invoke_handler.assert_not_called()

    @patch("owlclaw.agent.runtime.runtime.llm_integration.acompletion")
    async def test_tool_missing_function_name_not_executed(
        self, mock_llm, tmp_path
    ) -> None:
        tc = MagicMock()
        tc.id = "tc_bad"
        tc.function = MagicMock()
        tc.function.name = None
        tc.function.arguments = "{}"
        mock_llm.side_effect = [
            _make_llm_response(tool_calls=[tc]),
            _make_llm_response("ok"),
        ]

        registry = MagicMock()
        registry.handlers = {"market_scan": MagicMock()}
        registry.list_capabilities.return_value = [
            {"name": "market_scan", "description": "Scans market data"}
        ]
        registry.invoke_handler = AsyncMock(return_value={"price": 180})

        rt = AgentRuntime(
            agent_id="bot",
            app_dir=_make_app_dir(tmp_path),
            registry=registry,
        )
        await rt.setup()
        result = await rt.run(AgentRunContext(agent_id="bot", trigger="cron"))
        assert result["status"] == "completed"
        registry.invoke_handler.assert_not_called()

    @patch("owlclaw.agent.runtime.runtime.llm_integration.acompletion")
    async def test_tool_missing_id_uses_fallback_tool_call_id(
        self, mock_llm, tmp_path
    ) -> None:
        tc = _make_tool_call("market_scan", {"symbol": "AAPL"})
        tc.id = None
        mock_llm.side_effect = [
            _make_llm_response(tool_calls=[tc]),
            _make_llm_response("ok"),
        ]

        registry = MagicMock()
        registry.handlers = {"market_scan": MagicMock()}
        registry.list_capabilities.return_value = [
            {"name": "market_scan", "description": "Scans market data"}
        ]
        registry.invoke_handler = AsyncMock(return_value={"price": 180})

        rt = AgentRuntime(
            agent_id="bot",
            app_dir=_make_app_dir(tmp_path),
            registry=registry,
        )
        await rt.setup()
        result = await rt.run(AgentRunContext(agent_id="bot", trigger="cron"))
        assert result["status"] == "completed"
        registry.invoke_handler.assert_called_once_with("market_scan", symbol="AAPL")

    async def test_execute_tool_records_risk_audit_in_decision_reasoning(
        self, tmp_path
    ) -> None:
        """Ledger decision_reasoning should include risk and confirmation audit fields."""
        tc = _make_tool_call("place-order", {"symbol": "AAPL"})
        registry = MagicMock()
        registry.invoke_handler = AsyncMock(return_value={"ok": True})
        registry.get_capability_metadata.return_value = {
            "name": "place-order",
            "task_type": "trading_decision",
            "risk_level": "high",
            "requires_confirmation": True,
        }
        ledger = AsyncMock()
        rt = AgentRuntime(
            agent_id="bot",
            app_dir=_make_app_dir(tmp_path),
            registry=registry,
            ledger=ledger,
        )
        ctx = AgentRunContext(
            agent_id="bot",
            trigger="cron",
            payload={"confirmed_capabilities": ["place-order"]},
        )
        out = await rt._execute_tool(tc, ctx)
        assert out == {"ok": True}
        kwargs = ledger.record_execution.await_args.kwargs
        reasoning = json.loads(kwargs["decision_reasoning"])
        assert reasoning["risk_level"] == "high"
        assert reasoning["requires_confirmation"] is True
        assert reasoning["confirmed"] is True

    @patch("owlclaw.agent.runtime.runtime.llm_integration.acompletion")
    async def test_invalid_llm_response_shape_exits_gracefully(
        self, mock_llm, tmp_path
    ) -> None:
        response = MagicMock()
        response.choices = []
        mock_llm.return_value = response

        rt = AgentRuntime(agent_id="bot", app_dir=_make_app_dir(tmp_path))
        await rt.setup()
        result = await rt.run(AgentRunContext(agent_id="bot", trigger="cron"))
        assert result["status"] == "completed"
        assert result["final_response"] == "LLM response missing assistant message."

    @patch("owlclaw.agent.runtime.runtime.llm_integration.acompletion")
    async def test_max_iterations_respected(self, mock_llm, tmp_path) -> None:
        """When every LLM response has a tool call, loop stops at max."""
        tc = _make_tool_call("loop_tool", {})
        registry = MagicMock()
        registry.handlers = {"loop_tool": MagicMock()}
        registry.list_capabilities.return_value = [
            {"name": "loop_tool", "description": "loops"}
        ]
        registry.invoke_handler = AsyncMock(return_value={})

        # Always return tool calls — loop must stop at max_function_calls
        mock_llm.return_value = _make_llm_response(tool_calls=[tc])

        rt = AgentRuntime(
            agent_id="bot",
            app_dir=_make_app_dir(tmp_path),
            registry=registry,
            config={"max_function_calls": 3},
        )
        await rt.setup()
        ctx = AgentRunContext(agent_id="bot", trigger="cron")
        result = await rt.run(ctx)
        assert result["iterations"] == 3

    @patch("owlclaw.agent.runtime.runtime.llm_integration.acompletion")
    async def test_llm_timeout_returns_timeout_message(self, mock_llm, tmp_path) -> None:
        """LLM timeout should end the loop gracefully with a clear final response."""

        async def _slow_completion(**_: object):
            await asyncio.sleep(0.05)
            return _make_llm_response("late")

        mock_llm.side_effect = _slow_completion
        rt = AgentRuntime(
            agent_id="bot",
            app_dir=_make_app_dir(tmp_path),
            config={"llm_timeout_seconds": 0.01},
        )
        await rt.setup()
        result = await rt.run(AgentRunContext(agent_id="bot", trigger="cron"))
        assert result["status"] == "completed"
        assert "timed out" in result["final_response"]

    @patch("owlclaw.agent.runtime.runtime.llm_integration.acompletion")
    async def test_no_registry_no_tools(self, mock_llm, tmp_path) -> None:
        """Without a registry the visible tools list is empty."""
        mock_llm.return_value = _make_llm_response()
        rt = AgentRuntime(
            agent_id="bot",
            app_dir=_make_app_dir(tmp_path),
            config={"heartbeat": {"enabled": False}},
        )
        await rt.setup()
        result = await rt.trigger_event("cron")
        assert result["status"] == "completed"
        # tools kwarg should NOT be present when list is empty
        call_kwargs = mock_llm.call_args.kwargs
        assert "tools" not in call_kwargs

    async def test_visible_tools_passes_confirmed_capabilities_to_run_context(
        self, tmp_path
    ) -> None:
        """Runtime should forward payload.confirmed_capabilities to governance context."""
        rt = AgentRuntime(agent_id="bot", app_dir=_make_app_dir(tmp_path))
        rt.registry = MagicMock()
        rt.registry.list_capabilities.return_value = [
            {"name": "x", "description": "d", "constraints": {}}
        ]
        rt.visibility_filter = MagicMock()
        rt.visibility_filter.filter_capabilities = AsyncMock(return_value=[])
        ctx = AgentRunContext(
            agent_id="bot",
            trigger="cron",
            payload={"confirmed_capabilities": ["x"]},
        )
        await rt._get_visible_tools(ctx)
        run_ctx = rt.visibility_filter.filter_capabilities.call_args.args[2]
        assert run_ctx.confirmed_capabilities == {"x"}

    async def test_visible_tools_accepts_confirmed_capabilities_csv(
        self, tmp_path
    ) -> None:
        """Runtime should accept comma-separated confirmation list strings."""
        rt = AgentRuntime(agent_id="bot", app_dir=_make_app_dir(tmp_path))
        rt.registry = MagicMock()
        rt.registry.list_capabilities.return_value = [
            {"name": "x", "description": "d", "constraints": {}}
        ]
        rt.visibility_filter = MagicMock()
        rt.visibility_filter.filter_capabilities = AsyncMock(return_value=[])
        ctx = AgentRunContext(
            agent_id="bot",
            trigger="cron",
            payload={"confirmed_capabilities": "x, y ,"},
        )
        await rt._get_visible_tools(ctx)
        run_ctx = rt.visibility_filter.filter_capabilities.call_args.args[2]
        assert run_ctx.confirmed_capabilities == {"x", "y"}

    async def test_visible_tools_accepts_confirmed_capabilities_set(
        self, tmp_path
    ) -> None:
        """Runtime should accept set/tuple confirmation lists."""
        rt = AgentRuntime(agent_id="bot", app_dir=_make_app_dir(tmp_path))
        rt.registry = MagicMock()
        rt.registry.list_capabilities.return_value = [
            {"name": "x", "description": "d", "constraints": {}}
        ]
        rt.visibility_filter = MagicMock()
        rt.visibility_filter.filter_capabilities = AsyncMock(return_value=[])
        ctx = AgentRunContext(
            agent_id="bot",
            trigger="cron",
            payload={"confirmed_capabilities": {"x", "y"}},
        )
        await rt._get_visible_tools(ctx)
        run_ctx = rt.visibility_filter.filter_capabilities.call_args.args[2]
        assert run_ctx.confirmed_capabilities == {"x", "y"}

    @patch("owlclaw.agent.runtime.runtime.llm_integration.acompletion")
    async def test_heartbeat_no_events_skips_llm(self, mock_llm, tmp_path) -> None:
        """When trigger is heartbeat and no events, skip LLM and return skipped."""
        rt = AgentRuntime(agent_id="bot", app_dir=_make_app_dir(tmp_path))
        await rt.setup()
        ctx = AgentRunContext(agent_id="bot", trigger="heartbeat")
        result = await rt.run(ctx)
        assert result["status"] == "skipped"
        assert result["reason"] == "heartbeat_no_events"
        assert "run_id" in result
        mock_llm.assert_not_called()

    @patch("owlclaw.agent.runtime.runtime.llm_integration.acompletion")
    async def test_heartbeat_disabled_runs_full_loop(
        self, mock_llm, tmp_path
    ) -> None:
        """When heartbeat is disabled, heartbeat trigger still runs full loop."""
        mock_llm.return_value = _make_llm_response()
        rt = AgentRuntime(
            agent_id="bot",
            app_dir=_make_app_dir(tmp_path),
            config={"heartbeat": {"enabled": False}},
        )
        await rt.setup()
        result = await rt.trigger_event("heartbeat")
        assert result["status"] == "completed"
        mock_llm.assert_called_once()

    @patch("owlclaw.agent.runtime.runtime.llm_integration.acompletion")
    @patch(
        "owlclaw.agent.runtime.runtime.HeartbeatChecker.check_events",
        new_callable=AsyncMock,
        return_value=True,
    )
    async def test_heartbeat_with_events_runs_full_loop(
        self, mock_check_events, mock_llm, tmp_path
    ) -> None:
        """When heartbeat has events, run full decision loop."""
        mock_llm.return_value = _make_llm_response()
        rt = AgentRuntime(agent_id="bot", app_dir=_make_app_dir(tmp_path))
        await rt.setup()
        result = await rt.trigger_event("heartbeat")
        assert result["status"] == "completed"
        mock_check_events.assert_called_once()
        mock_llm.assert_called_once()

    @patch("owlclaw.agent.runtime.runtime.llm_integration.acompletion")
    @patch(
        "owlclaw.agent.runtime.runtime.HeartbeatChecker.check_events",
        new_callable=AsyncMock,
        return_value=False,
    )
    async def test_heartbeat_payload_has_events_skips_checker(
        self, mock_check_events, mock_llm, tmp_path
    ) -> None:
        """Payload event signal should run decision loop without checker lookup."""
        mock_llm.return_value = _make_llm_response()
        rt = AgentRuntime(agent_id="bot", app_dir=_make_app_dir(tmp_path))
        await rt.setup()
        result = await rt.trigger_event(
            "heartbeat",
            payload={"has_events": True},
        )
        assert result["status"] == "completed"
        mock_check_events.assert_not_called()
        mock_llm.assert_called_once()

    @patch("owlclaw.agent.runtime.runtime.llm_integration.acompletion")
    @patch(
        "owlclaw.agent.runtime.runtime.HeartbeatChecker.check_events",
        new_callable=AsyncMock,
        return_value=False,
    )
    async def test_heartbeat_payload_bool_event_count_does_not_trigger_run(
        self, mock_check_events, mock_llm, tmp_path
    ) -> None:
        """Boolean event_count should not be treated as numeric pending events."""
        rt = AgentRuntime(agent_id="bot", app_dir=_make_app_dir(tmp_path))
        await rt.setup()
        result = await rt.trigger_event(
            "heartbeat",
            payload={"event_count": True},
        )
        assert result["status"] == "skipped"
        assert result["reason"] == "heartbeat_no_events"
        mock_check_events.assert_called_once()
        mock_llm.assert_not_called()
