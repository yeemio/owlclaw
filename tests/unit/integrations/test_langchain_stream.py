"""Tests for LangChain streaming execution."""

from __future__ import annotations

from typing import Any

import pytest

from owlclaw.integrations.langchain.adapter import LangChainAdapter, RunnableConfig
from owlclaw.integrations.langchain.config import LangChainConfig


class DummyRegistry:
    def register_handler(self, name: str, handler: Any) -> None:
        return None


class DummyApp:
    def __init__(self) -> None:
        self.registry = DummyRegistry()


class AsyncStreamRunnable:
    async def astream(self, data: dict[str, Any]):
        yield "hello"
        yield "world"


class BrokenAsyncStreamRunnable:
    async def astream(self, data: dict[str, Any]):
        yield "hello"
        raise RuntimeError("stream broken")


@pytest.fixture(autouse=True)
def _mock_langchain_version_check(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "owlclaw.integrations.langchain.adapter.check_langchain_version",
        lambda **kwargs: None,
    )


def _config() -> RunnableConfig:
    return RunnableConfig(
        name="stream",
        description="stream",
        input_schema={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    )


@pytest.mark.asyncio
async def test_execute_stream_yields_chunks_and_final() -> None:
    adapter = LangChainAdapter(DummyApp(), LangChainConfig())

    events = [event async for event in adapter.execute_stream(AsyncStreamRunnable(), {"text": "x"}, None, _config())]

    chunk_events = [event for event in events if event["type"] == "chunk"]
    final_events = [event for event in events if event["type"] == "final"]
    assert len(chunk_events) == 2
    assert chunk_events[0]["data"] == "hello"
    assert chunk_events[1]["data"] == "world"
    assert len(final_events) == 1


@pytest.mark.asyncio
async def test_execute_stream_handles_interrupt() -> None:
    adapter = LangChainAdapter(DummyApp(), LangChainConfig())

    events = [
        event
        async for event in adapter.execute_stream(
            BrokenAsyncStreamRunnable(),
            {"text": "x"},
            None,
            _config(),
        )
    ]

    assert any(event["type"] == "chunk" for event in events)
    error_events = [event for event in events if event["type"] == "error"]
    assert len(error_events) == 1
    assert error_events[0]["error"]["status_code"] in {500, 504}
