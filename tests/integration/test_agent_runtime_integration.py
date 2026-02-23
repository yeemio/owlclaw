"""Integration tests for AgentRuntime external integrations (task 16)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlclaw.agent.runtime.context import AgentRunContext
from owlclaw.agent.runtime.hatchet_bridge import HatchetRuntimeBridge
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
async def test_hatchet_bridge_integration(tmp_path: Path) -> None:
    class _HatchetStub:
        def task(self, **kwargs):  # type: ignore[no-untyped-def]
            self.kwargs = kwargs
            return lambda fn: fn

    rt = AgentRuntime(agent_id="bot", app_dir=_make_app_dir(tmp_path))
    rt.trigger_event = AsyncMock(return_value={"status": "completed", "run_id": "r1"})  # type: ignore[method-assign]
    bridge = HatchetRuntimeBridge(rt, _HatchetStub(), task_name="agent-run", retries=2)
    handler = bridge.register_task()
    result = await handler({"event_name": "cron_tick", "payload": {"x": 1}})
    assert result["status"] == "completed"


@pytest.mark.asyncio
@patch("owlclaw.agent.runtime.runtime.llm_integration.acompletion")
async def test_litellm_integration_via_runtime(mock_llm, tmp_path: Path) -> None:
    mock_llm.return_value = _make_llm_response("done")
    rt = AgentRuntime(agent_id="bot", app_dir=_make_app_dir(tmp_path))
    await rt.setup()
    result = await rt.run(AgentRunContext(agent_id="bot", trigger="cron"))
    assert result["status"] == "completed"
    assert result["final_response"] == "done"


def test_vector_memory_integration_round_trip() -> None:
    class _Index:
        def __init__(self) -> None:
            self.payloads: list[dict[str, object]] = []

        def upsert(self, payload):  # type: ignore[no-untyped-def]
            self.payloads.append(payload)

    index = _Index()
    memory = MemorySystem(vector_index=index)
    memory.write("apple trading note", tags=["market"])
    hits = memory.search("apple", limit=1)
    assert hits
    assert index.payloads


@pytest.mark.asyncio
@patch("owlclaw.agent.runtime.runtime.llm_integration.acompletion")
async def test_langfuse_integration_via_runtime(mock_llm, tmp_path: Path) -> None:
    class _Trace:
        def __init__(self) -> None:
            self.updates: list[dict[str, object]] = []

        def update(self, **kwargs: object) -> None:
            self.updates.append(dict(kwargs))

    class _Client:
        def __init__(self) -> None:
            self.traces: list[_Trace] = []

        def trace(self, **_: object) -> _Trace:
            trace = _Trace()
            self.traces.append(trace)
            return trace

    mock_llm.return_value = _make_llm_response("ok")
    client = _Client()
    rt = AgentRuntime(
        agent_id="bot",
        app_dir=_make_app_dir(tmp_path),
        config={"langfuse": {"enabled": True, "client": client}},
    )
    await rt.setup()
    result = await rt.run(AgentRunContext(agent_id="bot", trigger="cron"))
    assert result["status"] == "completed"
    assert client.traces
