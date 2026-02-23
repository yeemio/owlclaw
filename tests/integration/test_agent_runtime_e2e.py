"""End-to-end style tests for AgentRuntime (task 17)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlclaw.agent.runtime.config import load_runtime_config
from owlclaw.agent.runtime.context import AgentRunContext
from owlclaw.agent.runtime.memory import MemorySystem
from owlclaw.agent.runtime.runtime import AgentRuntime


def _make_app_dir(tmp_path: Path) -> str:
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "SOUL.md").write_text("You are a helpful assistant.", encoding="utf-8")
    (tmp_path / "IDENTITY.md").write_text("## My Capabilities\n- market_scan\n", encoding="utf-8")
    return str(tmp_path)


def _make_tool_call(name: str, arguments: dict[str, object]) -> MagicMock:
    tc = MagicMock()
    tc.id = "tc_1"
    tc.function.name = name
    tc.function.arguments = json.dumps(arguments)
    return tc


def _make_llm_response(content: str = "ok", tool_calls: list[MagicMock] | None = None) -> MagicMock:
    message = MagicMock()
    message.content = content
    message.tool_calls = tool_calls or []
    message.model_dump.return_value = {"role": "assistant", "content": content, "tool_calls": tool_calls or []}
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    usage = MagicMock()
    usage.prompt_tokens = 1
    usage.completion_tokens = 1
    response.usage = usage
    return response


@pytest.mark.asyncio
@patch("owlclaw.agent.runtime.runtime.llm_integration.acompletion")
async def test_e2e_full_run_flow(mock_llm, tmp_path: Path) -> None:
    tc = _make_tool_call("market_scan", {"symbol": "AAPL"})
    mock_llm.side_effect = [_make_llm_response(tool_calls=[tc]), _make_llm_response("done")]
    registry = MagicMock()
    registry.handlers = {"market_scan": MagicMock()}
    registry.list_capabilities.return_value = [{"name": "market_scan", "description": "scan"}]
    registry.invoke_handler = AsyncMock(return_value={"price": 180})
    rt = AgentRuntime(agent_id="bot", app_dir=_make_app_dir(tmp_path), registry=registry)
    await rt.setup()
    result = await rt.run(AgentRunContext(agent_id="bot", trigger="cron"))
    assert result["status"] == "completed"
    assert result["tool_calls_total"] == 1


@pytest.mark.asyncio
@patch("owlclaw.agent.runtime.runtime.llm_integration.acompletion")
async def test_e2e_heartbeat_behavior(mock_llm, tmp_path: Path) -> None:
    mock_llm.return_value = _make_llm_response("ok")
    rt = AgentRuntime(agent_id="bot", app_dir=_make_app_dir(tmp_path))
    await rt.setup()
    skipped = await rt.trigger_event("heartbeat", payload={})
    ran = await rt.trigger_event("heartbeat", payload={"has_events": True})
    assert skipped["status"] == "skipped"
    assert ran["status"] == "completed"


def test_e2e_hot_reload_config(tmp_path: Path) -> None:
    app_dir = Path(_make_app_dir(tmp_path / "app"))
    cfg_path = app_dir / "runtime.yaml"
    cfg_path.write_text("runtime:\n  model: gpt-4o-mini\n  max_function_calls: 2\n", encoding="utf-8")
    rt = AgentRuntime(agent_id="bot", app_dir=str(app_dir))
    first = rt.load_config_file(str(cfg_path))
    cfg_path.write_text("runtime:\n  model: gpt-4o\n  max_function_calls: 4\n", encoding="utf-8")
    second = rt.reload_config()
    assert first["max_function_calls"] == 2
    assert second["max_function_calls"] == 4
    assert load_runtime_config(cfg_path)["model"] == "gpt-4o"


def test_e2e_memory_round_trip() -> None:
    memory = MemorySystem()
    memory.write("remember this incident", tags=["incident"])
    recalled = memory.recall_relevant("remember", limit=1)
    assert recalled and "remember" in recalled[0]


@pytest.mark.asyncio
@patch("owlclaw.agent.runtime.runtime.llm_integration.acompletion")
async def test_e2e_error_recovery_with_fallback(mock_llm, tmp_path: Path) -> None:
    mock_llm.side_effect = [RuntimeError("primary down"), _make_llm_response("ok")]
    rt = AgentRuntime(
        agent_id="bot",
        app_dir=_make_app_dir(tmp_path),
        model="primary-model",
        config={"llm_retry_attempts": 1, "llm_fallback_models": ["fallback-model"]},
    )
    await rt.setup()
    result = await rt.run(AgentRunContext(agent_id="bot", trigger="cron"))
    assert result["status"] == "completed"
