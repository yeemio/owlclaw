"""Integration tests for runtime + langfuse tracing paths."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlclaw.agent.runtime.context import AgentRunContext
from owlclaw.agent.runtime.runtime import AgentRuntime
from owlclaw.integrations.langfuse import LangfuseClient, LangfuseConfig, LLMSpanData, ToolSpanData


def _make_app_dir(tmp_path):
    (tmp_path / "SOUL.md").write_text("You are helpful.", encoding="utf-8")
    (tmp_path / "IDENTITY.md").write_text("## Capabilities\n- market_scan\n", encoding="utf-8")
    return str(tmp_path)


def _make_llm_response(content="Done.", tool_calls=None, *, prompt_tokens=0, completion_tokens=0):
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
    usage = MagicMock()
    usage.prompt_tokens = prompt_tokens
    usage.completion_tokens = completion_tokens
    usage.total_tokens = prompt_tokens + completion_tokens
    response.usage = usage
    return response


def _make_tool_call(name: str, arguments: dict[str, object]):
    tc = MagicMock()
    tc.id = "call_1"
    tc.function.name = name
    tc.function.arguments = json.dumps(arguments)
    return tc


class _FakeObs:
    def __init__(self, obs_id: str) -> None:
        self.id = obs_id
        self.updates: list[dict[str, object]] = []

    def update(self, **kwargs: object) -> None:
        self.updates.append(dict(kwargs))

    def end(self, **kwargs: object) -> None:
        self.updates.append(dict(kwargs))


class _FakeTrace:
    def __init__(self) -> None:
        self.id = "trace-int-1"
        self.updates: list[dict[str, object]] = []
        self.generations: list[dict[str, object]] = []
        self.spans: list[_FakeObs] = []

    def update(self, **kwargs: object) -> None:
        self.updates.append(dict(kwargs))

    def generation(self, **kwargs: object) -> _FakeObs:
        self.generations.append(dict(kwargs))
        return _FakeObs("gen-1")

    def span(self, **kwargs: object) -> _FakeObs:
        obs = _FakeObs("span-1")
        self.spans.append(obs)
        return obs


class _FakeLangfuse:
    def __init__(self) -> None:
        self.traces: list[_FakeTrace] = []

    def trace(self, **kwargs: object) -> _FakeTrace:
        trace = _FakeTrace()
        self.traces.append(trace)
        return trace


@pytest.mark.asyncio
@patch("litellm.acompletion", new_callable=AsyncMock)
async def test_agent_run_trace_llm_and_tool_spans(mock_llm, tmp_path) -> None:
    tc = _make_tool_call("market_scan", {"symbol": "AAPL"})
    mock_llm.side_effect = [
        _make_llm_response(tool_calls=[tc], prompt_tokens=10, completion_tokens=5),
        _make_llm_response("ok", prompt_tokens=5, completion_tokens=2),
    ]

    registry = MagicMock()
    registry.handlers = {"market_scan": MagicMock()}
    registry.list_capabilities.return_value = [{"name": "market_scan", "description": "scan"}]
    registry.invoke_handler = AsyncMock(return_value={"price": 1})

    lf = _FakeLangfuse()
    rt = AgentRuntime(
        agent_id="bot",
        app_dir=_make_app_dir(tmp_path),
        registry=registry,
        config={"langfuse": {"enabled": True, "client": lf}},
    )
    await rt.setup()
    result = await rt.run(AgentRunContext(agent_id="bot", trigger="cron"))
    assert result["status"] == "completed"
    assert len(lf.traces) == 1
    assert len(lf.traces[0].generations) >= 1
    assert len(lf.traces[0].spans) >= 1
    assert len(lf.traces[0].updates) >= 1
    assert any(update.get("status") == "success" for update in lf.traces[0].updates)


def test_langfuse_masking_integration() -> None:
    class _Sdk:
        def __init__(self) -> None:
            self.generation_calls: list[dict[str, object]] = []
            self.span_calls: list[dict[str, object]] = []

        def generation(self, **kwargs: object):
            self.generation_calls.append(dict(kwargs))
            return _FakeObs("gen-1")

        def span(self, **kwargs: object):
            self.span_calls.append(dict(kwargs))
            return _FakeObs("span-1")

    sdk = _Sdk()
    client = LangfuseClient(
        LangfuseConfig(
            enabled=True,
            client=sdk,
            mask_inputs=True,
            mask_outputs=True,
        )
    )
    client.create_llm_span(
        "trace-1",
        "llm",
        LLMSpanData(
            model="gpt-4o-mini",
            prompt=[{"role": "user", "content": "email me at a@b.com"}],
            response="my phone is 123-456-7890",
            prompt_tokens=1,
            completion_tokens=1,
            total_tokens=2,
            cost_usd=0.0,
            latency_ms=10.0,
            status="success",
        ),
    )
    client.create_tool_span(
        "trace-1",
        "tool",
        ToolSpanData(
            tool_name="remember",
            arguments={"token": "sk-abcdef123456"},
            result={"email": "a@b.com"},
            duration_ms=10.0,
            status="success",
        ),
    )
    assert "[MASKED_EMAIL]" in str(sdk.generation_calls[0]["input"])
    assert "[MASKED_PHONE]" in str(sdk.generation_calls[0]["output"])
    assert "[MASKED_API_KEY]" in str(sdk.span_calls[0]["input"])


@pytest.mark.asyncio
@patch("litellm.acompletion", new_callable=AsyncMock)
async def test_runtime_degrades_when_langfuse_fails(mock_llm, tmp_path) -> None:
    class _FailingLangfuse:
        def trace(self, **kwargs: object):
            raise RuntimeError("langfuse down")

    mock_llm.return_value = _make_llm_response("ok", prompt_tokens=3, completion_tokens=2)
    rt = AgentRuntime(
        agent_id="bot",
        app_dir=_make_app_dir(tmp_path),
        config={"langfuse": {"enabled": True, "client": _FailingLangfuse()}},
    )
    await rt.setup()
    result = await rt.run(AgentRunContext(agent_id="bot", trigger="cron"))
    assert result["status"] == "completed"
