"""Tests for governance and ledger integration in LangChainAdapter."""

from __future__ import annotations

from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from owlclaw.integrations.langchain.adapter import LangChainAdapter, RunnableConfig
from owlclaw.integrations.langchain.config import LangChainConfig


class AsyncRunnable:
    async def ainvoke(self, data: dict[str, Any]) -> dict[str, Any]:
        return {"result": data["text"].upper()}


class FailingRunnable:
    async def ainvoke(self, data: dict[str, Any]) -> dict[str, Any]:
        raise ValueError("boom")


class GovernedApp:
    def __init__(self, decision: dict[str, Any] | None = None) -> None:
        self.registry = type("Registry", (), {"register_handler": lambda self, name, handler: None})()
        self._decision = decision or {"allowed": True}
        self.records: list[dict[str, Any]] = []

    async def validate_capability_execution(self, **kwargs: Any) -> dict[str, Any]:
        return self._decision

    async def record_langchain_execution(self, payload: dict[str, Any]) -> None:
        self.records.append(payload)


def _config() -> RunnableConfig:
    return RunnableConfig(
        name="governed",
        description="governed runnable",
        input_schema={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    )


@pytest.mark.asyncio
async def test_governance_allow_executes_runnable() -> None:
    app = GovernedApp(decision={"allowed": True})
    adapter = LangChainAdapter(app, LangChainConfig())

    result = await adapter.execute(AsyncRunnable(), {"text": "hello"}, {"user_id": "u1"}, _config())

    assert result["result"] == "HELLO"
    assert app.records[-1]["status"] == "success"


@given(st.text(min_size=1, max_size=40))
@pytest.mark.asyncio
async def test_governance_denied_returns_403(reason: str) -> None:
    app = GovernedApp(decision={"allowed": False, "reason": reason, "status_code": 403})
    adapter = LangChainAdapter(app, LangChainConfig())

    result = await adapter.execute(AsyncRunnable(), {"text": "hello"}, {"user_id": "u1"}, _config())

    assert result["error"]["status_code"] == 403
    assert reason in result["error"]["message"]


@pytest.mark.asyncio
async def test_governance_rate_limit_returns_429_with_headers() -> None:
    app = GovernedApp(
        decision={
            "allowed": False,
            "reason": "too many requests",
            "status_code": 429,
            "headers": {"X-RateLimit-Remaining": "0"},
        }
    )
    adapter = LangChainAdapter(app, LangChainConfig())

    result = await adapter.execute(AsyncRunnable(), {"text": "hello"}, {"user_id": "u1"}, _config())

    assert result["error"]["status_code"] == 429
    assert result.get("headers", {}).get("X-RateLimit-Remaining") == "0"


@pytest.mark.asyncio
async def test_ledger_records_failure_payload() -> None:
    app = GovernedApp(decision={"allowed": True})
    adapter = LangChainAdapter(app, LangChainConfig())

    result = await adapter.execute(FailingRunnable(), {"text": "hello"}, {"user_id": "u1"}, _config())

    assert "error" in result
    record = app.records[-1]
    assert record["status"] == "error"
    assert record["error_message"]


@given(st.text(min_size=1, max_size=20))
@pytest.mark.asyncio
async def test_ledger_record_contains_required_fields(text: str) -> None:
    app = GovernedApp(decision={"allowed": True})
    adapter = LangChainAdapter(app, LangChainConfig())

    await adapter.execute(AsyncRunnable(), {"text": text}, {"user_id": "u1", "agent_id": "a1"}, _config())

    record = app.records[-1]
    required_fields = {
        "event_type",
        "capability_name",
        "status",
        "duration_ms",
        "input",
        "trace_id",
    }
    assert required_fields.issubset(set(record.keys()))
