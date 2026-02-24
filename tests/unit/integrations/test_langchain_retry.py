"""Tests for retry policy and adapter retry behavior."""

from __future__ import annotations

from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from owlclaw.integrations.langchain.adapter import LangChainAdapter, RunnableConfig
from owlclaw.integrations.langchain.config import LangChainConfig
from owlclaw.integrations.langchain.retry import RetryPolicy, calculate_backoff_delay, should_retry


class TimeoutError(Exception):
    """Test-only timeout error class."""


class DummyRegistry:
    def register_handler(self, name: str, handler: Any) -> None:
        return None


class DummyApp:
    def __init__(self) -> None:
        self.registry = DummyRegistry()


class FlakyRunnable:
    def __init__(self, fail_times: int) -> None:
        self._fail_times = fail_times
        self.calls = 0

    async def ainvoke(self, data: dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        if self.calls <= self._fail_times:
            raise TimeoutError("temporary timeout")
        return {"ok": data}


@given(st.integers(min_value=1, max_value=6))
def test_calculate_backoff_delay_is_non_decreasing(attempt: int) -> None:
    policy = RetryPolicy(initial_delay_ms=50, max_delay_ms=1000, backoff_multiplier=2.0)

    current = calculate_backoff_delay(attempt, policy)
    nxt = calculate_backoff_delay(attempt + 1, policy)

    assert current <= nxt
    assert nxt <= policy.max_delay_ms / 1000.0


def test_should_retry_respects_attempt_limit_and_error_type() -> None:
    policy = RetryPolicy(max_attempts=3, retryable_errors=["TimeoutError"])

    assert should_retry(TimeoutError("x"), attempt=1, policy=policy) is True
    assert should_retry(ValueError("x"), attempt=1, policy=policy) is False
    assert should_retry(TimeoutError("x"), attempt=3, policy=policy) is False


@pytest.mark.asyncio
async def test_adapter_retries_and_succeeds() -> None:
    adapter = LangChainAdapter(DummyApp(), LangChainConfig())
    runnable = FlakyRunnable(fail_times=2)
    config = RunnableConfig(
        name="retry-demo",
        description="Retry demo",
        input_schema={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
        retry_policy={
            "max_attempts": 3,
            "initial_delay_ms": 0,
            "max_delay_ms": 0,
            "backoff_multiplier": 2.0,
            "retryable_errors": ["TimeoutError"],
        },
    )

    result = await adapter.execute(runnable, {"text": "hi"}, None, config)

    assert result["ok"]["text"] == "hi"
    assert runnable.calls == 3


@pytest.mark.asyncio
async def test_adapter_stops_retry_when_non_retryable() -> None:
    class BadRunnable:
        async def ainvoke(self, data: dict[str, Any]) -> dict[str, Any]:
            raise ValueError("bad input")

    adapter = LangChainAdapter(DummyApp(), LangChainConfig())
    config = RunnableConfig(
        name="non-retry",
        description="non-retry",
        input_schema={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
        retry_policy={
            "max_attempts": 3,
            "initial_delay_ms": 0,
            "max_delay_ms": 0,
            "backoff_multiplier": 2.0,
            "retryable_errors": ["TimeoutError"],
        },
    )

    result = await adapter.execute(BadRunnable(), {"text": "hi"}, None, config)

    assert result["error"]["status_code"] in {400, 500}
