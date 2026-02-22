"""Unit tests for AgentRuntime (Tasks 6/7/8)."""

from __future__ import annotations

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


def _make_tool_call(name: str, arguments: dict):
    tc = MagicMock()
    tc.id = "tc_1"
    tc.function.name = name
    tc.function.arguments = json.dumps(arguments)
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
