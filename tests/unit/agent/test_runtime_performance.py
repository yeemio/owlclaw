"""Performance-oriented tests for AgentRuntime caches and resource limits (task 14)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlclaw.agent.runtime.context import AgentRunContext
from owlclaw.agent.runtime.runtime import AgentRuntime


def _make_app_dir(tmp_path):
    (tmp_path / "SOUL.md").write_text("You are a helpful assistant.", encoding="utf-8")
    (tmp_path / "IDENTITY.md").write_text("## My Capabilities\n- market_scan\n", encoding="utf-8")
    return str(tmp_path)


def _make_llm_response(content="Done.", tool_calls=None):
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


def _make_tool_call(name: str, arguments: dict):
    tc = MagicMock()
    tc.id = "tc_1"
    tc.function.name = name
    tc.function.arguments = json.dumps(arguments)
    return tc


def test_skills_context_cache_hits(tmp_path) -> None:
    rt = AgentRuntime(agent_id="bot", app_dir=_make_app_dir(tmp_path))
    rt.registry = MagicMock()
    rt.registry.handlers = {"skill-a": MagicMock()}
    rt.knowledge_injector = MagicMock()
    mock_report = MagicMock()
    mock_report.content = "skills"
    mock_report.total_tokens = 10
    mock_report.selected_skill_names = ["skill-a"]
    mock_report.dropped_skill_names = []
    mock_report.per_skill_tokens = {"skill-a": 10}
    rt.knowledge_injector.get_skills_knowledge_report.return_value = mock_report
    ctx = AgentRunContext(agent_id="bot", trigger="cron")
    first = rt._build_skills_context(ctx)
    second = rt._build_skills_context(ctx)
    assert first == "skills" and second == "skills"
    rt.knowledge_injector.get_skills_knowledge_report.assert_called_once()
    metrics = rt.get_performance_metrics()
    assert metrics["skills_cache_hits"] >= 1


@pytest.mark.asyncio
async def test_visible_tools_resource_limit(tmp_path) -> None:
    rt = AgentRuntime(
        agent_id="bot",
        app_dir=_make_app_dir(tmp_path),
        config={"performance": {"max_visible_tools": 1}},
    )
    rt.registry = MagicMock()
    rt.registry.list_capabilities.return_value = [
        {"name": "a", "description": "A"},
        {"name": "b", "description": "B"},
    ]
    rt.visibility_filter = None
    out = await rt._get_visible_tools(AgentRunContext(agent_id="bot", trigger="cron"))
    assert len(out) == 1


@pytest.mark.asyncio
@patch("owlclaw.agent.runtime.runtime.llm_integration.acompletion")
async def test_metrics_track_llm_and_tool_calls(mock_llm, tmp_path) -> None:
    tc = _make_tool_call("market_scan", {"symbol": "AAPL"})
    mock_llm.side_effect = [_make_llm_response(tool_calls=[tc]), _make_llm_response("ok")]
    registry = MagicMock()
    registry.handlers = {"market_scan": MagicMock()}
    registry.list_capabilities.return_value = [{"name": "market_scan", "description": "scan"}]
    registry.invoke_handler = AsyncMock(return_value={"ok": True})
    rt = AgentRuntime(agent_id="bot", app_dir=_make_app_dir(tmp_path), registry=registry)
    await rt.setup()
    result = await rt.run(AgentRunContext(agent_id="bot", trigger="cron"))
    assert result["status"] == "completed"
    metrics = rt.get_performance_metrics()
    assert metrics["llm_calls"] >= 1
    assert metrics["tool_calls"] >= 1
    assert metrics["llm_time_ms_total"] >= 0
