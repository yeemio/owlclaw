"""Tests for LangChainAdapter."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from owlclaw.integrations.langchain.adapter import LangChainAdapter, RunnableConfig
from owlclaw.integrations.langchain.config import LangChainConfig


@pytest.fixture(autouse=True)
def _mock_langchain_version_check(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "owlclaw.integrations.langchain.adapter.check_langchain_version",
        lambda **kwargs: None,
    )


class DummyRegistry:
    def __init__(self) -> None:
        self.handlers: dict[str, Any] = {}

    def register_handler(self, name: str, handler: Any) -> None:
        if name in self.handlers:
            raise ValueError(f"duplicate handler: {name}")
        self.handlers[name] = handler


class DummyApp:
    def __init__(self) -> None:
        self.registry = DummyRegistry()


class AsyncRunnable:
    async def ainvoke(self, data: dict[str, Any]) -> dict[str, Any]:
        return {"echo": data}


class SyncRunnable:
    def invoke(self, data: dict[str, Any]) -> dict[str, Any]:
        return {"sync": data}


class InvalidRunnable:
    pass


def _config(name: str = "demo") -> RunnableConfig:
    return RunnableConfig(
        name=name,
        description="Demo runnable",
        input_schema={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    )


@given(st.one_of(st.integers(), st.text(), st.lists(st.integers()), st.dictionaries(st.text(), st.integers())))
def test_register_runnable_rejects_non_runnable_types(value: Any) -> None:
    app = DummyApp()
    adapter = LangChainAdapter(app, LangChainConfig())

    with pytest.raises(TypeError, match=r"invoke\(\) or ainvoke\(\)"):
        adapter.register_runnable(value, _config())


def test_register_runnable_duplicate_registration_has_clear_error() -> None:
    app = DummyApp()
    adapter = LangChainAdapter(app, LangChainConfig())

    adapter.register_runnable(AsyncRunnable(), _config(name="dup"))
    with pytest.raises(ValueError, match="duplicate handler"):
        adapter.register_runnable(AsyncRunnable(), _config(name="dup"))


@pytest.mark.asyncio
async def test_execute_prefers_async_ainvoke() -> None:
    app = DummyApp()
    adapter = LangChainAdapter(app, LangChainConfig())
    runnable = AsyncRunnable()

    result = await adapter.execute(runnable, {"text": "hello"}, None, _config())

    assert result["echo"]["text"] == "hello"


@pytest.mark.asyncio
async def test_execute_falls_back_to_sync_invoke() -> None:
    app = DummyApp()
    adapter = LangChainAdapter(app, LangChainConfig())
    runnable = SyncRunnable()

    result = await adapter.execute(runnable, {"text": "hello"}, None, _config())

    assert result["sync"]["text"] == "hello"


@pytest.mark.asyncio
async def test_execute_returns_validation_error_payload() -> None:
    app = DummyApp()
    adapter = LangChainAdapter(app, LangChainConfig())

    result = await adapter.execute(AsyncRunnable(), {"text": 123}, None, _config())

    assert result["error"]["type"] in {"ValidationError", "InternalError"}
    assert result["error"]["status_code"] in {400, 500}


@pytest.mark.asyncio
async def test_execute_with_timeout_raises_timeout() -> None:
    class SlowRunnable:
        async def ainvoke(self, data: dict[str, Any]) -> dict[str, Any]:
            await asyncio.sleep(0.05)
            return data

    app = DummyApp()
    adapter = LangChainAdapter(app, LangChainConfig())

    with pytest.raises(asyncio.TimeoutError):
        await adapter._execute_with_timeout(SlowRunnable(), {"text": "x"}, timeout_seconds=0)


def test_register_runnable_attaches_handler_to_registry() -> None:
    app = DummyApp()
    adapter = LangChainAdapter(app, LangChainConfig())
    adapter.register_runnable(AsyncRunnable(), _config(name="registered"))

    assert "registered" in app.registry.handlers


def test_invalid_runnable_class_rejected() -> None:
    app = DummyApp()
    adapter = LangChainAdapter(app, LangChainConfig())

    with pytest.raises(TypeError):
        adapter.register_runnable(InvalidRunnable(), _config())
