"""Property tests for AgentRuntime behavior (agent-runtime Task 6/7/8)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given
from hypothesis import settings
from hypothesis import strategies as st

from owlclaw.agent.runtime.context import AgentRunContext
from owlclaw.agent.runtime.runtime import AgentRuntime


def _make_app_dir(path: Path) -> str:
    (path / "SOUL.md").write_text("You are a helpful assistant.", encoding="utf-8")
    (path / "IDENTITY.md").write_text("## My Capabilities\n- market_scan\n", encoding="utf-8")
    return str(path)


def _make_tool_call(name: str, arguments: dict[str, object]) -> MagicMock:
    tc = MagicMock()
    tc.id = "tc_1"
    tc.function.name = name
    tc.function.arguments = json.dumps(arguments)
    return tc


def _make_llm_response(content: str = "Done.", tool_calls: list[MagicMock] | None = None) -> MagicMock:
    message = MagicMock()
    message.content = content
    message.tool_calls = tool_calls or []
    message.model_dump.return_value = {"role": "assistant", "content": content, "tool_calls": tool_calls or []}
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


@pytest.mark.asyncio
@given(raw=st.one_of(st.lists(st.text(min_size=0, max_size=8), max_size=5), st.text(min_size=0, max_size=30)))
@settings(deadline=None)
async def test_property_visible_tools_normalizes_confirmed_capabilities(raw: object) -> None:
    """Property 13: runtime forwards normalized confirmed_capabilities into governance context."""
    with TemporaryDirectory() as tmp:
        rt = AgentRuntime(agent_id="bot", app_dir=_make_app_dir(Path(tmp)))
        rt.registry = MagicMock()
        rt.registry.list_capabilities.return_value = [{"name": "x", "description": "d", "constraints": {}}]
        rt.visibility_filter = MagicMock()
        rt.visibility_filter.filter_capabilities = AsyncMock(return_value=[])
        payload = {"confirmed_capabilities": raw}
        await rt._get_visible_tools(AgentRunContext(agent_id="bot", trigger="cron", payload=payload))
        run_ctx = rt.visibility_filter.filter_capabilities.call_args.args[2]
        expected = rt._extract_confirmed_capabilities(payload)
        assert run_ctx.confirmed_capabilities == (expected or None)


@pytest.mark.asyncio
@given(error_message=st.text(min_size=1, max_size=80))
@settings(deadline=None)
async def test_property_tool_error_propagation(error_message: str) -> None:
    """Property 21: tool execution failures are returned to LLM as error payloads."""
    with TemporaryDirectory() as tmp:
        registry = MagicMock()
        registry.handlers = {"market_scan": MagicMock()}
        registry.invoke_handler = AsyncMock(side_effect=RuntimeError(error_message))
        rt = AgentRuntime(agent_id="bot", app_dir=_make_app_dir(Path(tmp)), registry=registry)
        await rt.setup()
        tc = _make_tool_call("market_scan", {"symbol": "AAPL"})
        result = await rt._execute_tool(tc, AgentRunContext(agent_id="bot", trigger="cron"))
        assert "error" in result
        assert error_message in result["error"]


@pytest.mark.asyncio
@given(max_calls=st.integers(min_value=1, max_value=6))
@settings(deadline=None)
async def test_property_function_call_max_iterations(max_calls: int) -> None:
    """Property 11: decision loop stops at max_function_calls limit."""
    with TemporaryDirectory() as tmp, patch("owlclaw.agent.runtime.runtime.llm_integration.acompletion") as mock_llm:
        tc = _make_tool_call("loop_tool", {})
        mock_llm.return_value = _make_llm_response(tool_calls=[tc])

        registry = MagicMock()
        registry.handlers = {"loop_tool": MagicMock()}
        registry.list_capabilities.return_value = [{"name": "loop_tool", "description": "d"}]
        registry.invoke_handler = AsyncMock(return_value={"ok": True})

        rt = AgentRuntime(
            agent_id="bot",
            app_dir=_make_app_dir(Path(tmp)),
            registry=registry,
            config={"max_function_calls": max_calls},
        )
        await rt.setup()
        result = await rt.run(AgentRunContext(agent_id="bot", trigger="cron"))
        assert result["iterations"] == max_calls
        assert mock_llm.call_count == max_calls


@pytest.mark.asyncio
@given(timeout=st.floats(min_value=0.001, max_value=0.02, allow_nan=False, allow_infinity=False))
@settings(deadline=None)
async def test_property_llm_timeout_control(timeout: float) -> None:
    """Property 12: slow LLM calls are terminated by llm_timeout_seconds."""

    async def _slow_completion(**_: object) -> MagicMock:
        await asyncio.sleep(0.05)
        return _make_llm_response("late")

    with TemporaryDirectory() as tmp, patch(
        "owlclaw.agent.runtime.runtime.llm_integration.acompletion",
        new=AsyncMock(side_effect=_slow_completion),
    ):
        rt = AgentRuntime(
            agent_id="bot",
            app_dir=_make_app_dir(Path(tmp)),
            config={"llm_timeout_seconds": timeout},
        )
        await rt.setup()
        result = await rt.run(AgentRunContext(agent_id="bot", trigger="cron"))
        assert result["status"] == "completed"
        assert "timed out" in result["final_response"]


@pytest.mark.asyncio
@given(payload=st.sampled_from([{}, {"event_count": 0}, {"event_count": False}, {"pending_events": []}]))
@settings(deadline=None)
async def test_property_heartbeat_no_events_skips_llm(payload: dict[str, object]) -> None:
    """Property 14: heartbeat run is skipped when no pending events exist."""
    with TemporaryDirectory() as tmp, patch(
        "owlclaw.agent.runtime.runtime.llm_integration.acompletion"
    ) as mock_llm, patch(
        "owlclaw.agent.runtime.runtime.HeartbeatChecker.check_events",
        new_callable=AsyncMock,
        return_value=False,
    ):
        rt = AgentRuntime(agent_id="bot", app_dir=_make_app_dir(Path(tmp)))
        await rt.setup()
        result = await rt.trigger_event("heartbeat", payload=payload)
        assert result["status"] == "skipped"
        assert result["reason"] == "heartbeat_no_events"
        mock_llm.assert_not_called()


@pytest.mark.asyncio
@given(payload=st.sampled_from([{"has_events": True}, {"pending_events": ["x"]}, {"event_count": 1}, {"event_count": 1.5}]))
@settings(deadline=None)
async def test_property_heartbeat_with_events_runs_loop(payload: dict[str, object]) -> None:
    """Property 15: heartbeat run proceeds when event markers exist."""
    with TemporaryDirectory() as tmp, patch(
        "owlclaw.agent.runtime.runtime.llm_integration.acompletion"
    ) as mock_llm, patch(
        "owlclaw.agent.runtime.runtime.HeartbeatChecker.check_events",
        new_callable=AsyncMock,
        return_value=False,
    ) as mock_check_events:
        mock_llm.return_value = _make_llm_response("ok")
        rt = AgentRuntime(agent_id="bot", app_dir=_make_app_dir(Path(tmp)))
        await rt.setup()
        result = await rt.trigger_event("heartbeat", payload=payload)
        assert result["status"] == "completed"
        mock_llm.assert_called_once()
        if "has_events" in payload or "pending_events" in payload or payload.get("event_count", 0) > 0:
            mock_check_events.assert_not_called()


@pytest.mark.asyncio
@given(run_timeout=st.floats(min_value=0.001, max_value=0.02, allow_nan=False, allow_infinity=False))
@settings(deadline=None)
async def test_property_run_timeout_control(run_timeout: float) -> None:
    """Property 16: run timeout terminates execution and reports failure."""
    with TemporaryDirectory() as tmp:
        rt = AgentRuntime(
            agent_id="bot",
            app_dir=_make_app_dir(Path(tmp)),
            config={"run_timeout_seconds": run_timeout},
        )
        await rt.setup()

        async def _slow_loop(_: AgentRunContext) -> dict[str, object]:
            await asyncio.sleep(0.05)
            return {"iterations": 1, "final_response": "late", "tool_calls_total": 0}

        rt._decision_loop = _slow_loop  # type: ignore[method-assign]
        result = await rt.run(AgentRunContext(agent_id="bot", trigger="cron"))
        assert result["status"] == "failed"
        assert "timed out" in result["error"]
