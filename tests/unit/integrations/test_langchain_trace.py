"""Tests for TraceManager and TraceSpan."""

from __future__ import annotations

import time

from hypothesis import given
from hypothesis import strategies as st

from owlclaw.integrations.langchain.config import LangChainConfig
from owlclaw.integrations.langchain.trace import TraceManager


class DummyLangfuse:
    """Minimal langfuse stub for trace API."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def trace(self, **kwargs):
        self.calls.append(kwargs)
        return DummySpan()


class DummySpan:
    """Minimal span stub for update API."""

    def __init__(self) -> None:
        self.updates: list[dict] = []

    def update(self, **kwargs) -> None:
        self.updates.append(kwargs)


@given(st.text(min_size=1, max_size=32))
def test_create_span_generates_ids(name: str) -> None:
    manager = TraceManager(LangChainConfig())

    span = manager.create_span(name=name)

    assert span.trace_id.startswith("lc_")
    assert len(span.span_id) == 32


def test_create_span_uses_context_trace_id_when_present() -> None:
    manager = TraceManager(LangChainConfig())

    span = manager.create_span(name="test", context={"trace_id": "external-trace"})

    assert span.trace_id == "external-trace"


def test_create_langfuse_span_when_enabled() -> None:
    config = LangChainConfig()
    config.tracing.langfuse_integration = True
    client = DummyLangfuse()
    manager = TraceManager(config, langfuse_client=client)

    manager.create_span(name="summarize", input_data={"text": "hello"}, context={"agent_id": "agent-1"})

    assert len(client.calls) == 1
    assert client.calls[0]["name"] == "summarize"


def test_trace_span_end_returns_duration_payload() -> None:
    manager = TraceManager(LangChainConfig())
    span = manager.create_span(name="qa")
    time.sleep(0.001)

    result = span.end(output={"answer": "ok"})

    assert result["name"] == "qa"
    assert result["duration_ms"] >= 0
    assert result["output"] == {"answer": "ok"}
