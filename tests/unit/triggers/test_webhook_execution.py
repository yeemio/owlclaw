from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import pytest

from owlclaw.triggers.webhook import AgentInput, ExecutionOptions, ExecutionTrigger, RetryPolicy


@dataclass
class _Runtime:
    handler: Callable[[AgentInput], Awaitable[dict[str, Any]]]
    calls: int = 0

    async def trigger(self, input_data: AgentInput) -> dict[str, Any]:
        self.calls += 1
        return await self.handler(input_data)


def _input() -> AgentInput:
    return AgentInput(agent_id="agent-1", parameters={"v": 1})


@pytest.mark.asyncio
async def test_execution_trigger_concurrent_idempotency() -> None:
    async def _ok(input_data: AgentInput) -> dict[str, Any]:  # noqa: ARG001
        await asyncio.sleep(0.01)
        return {"execution_id": "exec-1", "status": "completed", "output": {"ok": True}}

    runtime = _Runtime(handler=_ok)
    trigger = ExecutionTrigger(runtime)
    options = ExecutionOptions(mode="sync", idempotency_key="idem-1")

    results = await asyncio.gather(trigger.trigger(_input(), options), trigger.trigger(_input(), options))
    assert runtime.calls == 1
    assert results[0].execution_id == results[1].execution_id


@pytest.mark.asyncio
async def test_execution_trigger_retry_delay_backoff() -> None:
    attempts = 0
    delays: list[float] = []

    async def _flaky(input_data: AgentInput) -> dict[str, Any]:  # noqa: ARG001
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionError("temporary")
        return {"execution_id": "exec-2", "status": "completed", "output": {"ok": True}}

    async def _sleep(delay: float) -> None:
        delays.append(delay)

    runtime = _Runtime(handler=_flaky)
    trigger = ExecutionTrigger(runtime, sleeper=_sleep)
    options = ExecutionOptions(
        mode="sync",
        retry_policy=RetryPolicy(max_attempts=3, initial_delay_ms=100, max_delay_ms=400, backoff_multiplier=2.0),
    )

    result = await trigger.trigger(_input(), options)
    assert result.status == "completed"
    assert delays == [0.1, 0.2]


@pytest.mark.asyncio
async def test_execution_trigger_sync_timeout() -> None:
    async def _slow(input_data: AgentInput) -> dict[str, Any]:  # noqa: ARG001
        await asyncio.sleep(0.2)
        return {"execution_id": "exec-timeout", "status": "completed"}

    runtime = _Runtime(handler=_slow)
    trigger = ExecutionTrigger(runtime)
    options = ExecutionOptions(mode="sync", timeout_seconds=0.01, retry_policy=RetryPolicy(max_attempts=1))

    result = await trigger.trigger(_input(), options)
    assert result.status == "failed"
    assert result.error is not None
    assert result.error["status_code"] == 503


@pytest.mark.asyncio
async def test_execution_trigger_execution_result_cache() -> None:
    async def _ok(input_data: AgentInput) -> dict[str, Any]:  # noqa: ARG001
        return {"execution_id": "exec-cache", "status": "completed", "output": {"value": 42}}

    runtime = _Runtime(handler=_ok)
    trigger = ExecutionTrigger(runtime)
    options = ExecutionOptions(mode="sync")

    result = await trigger.trigger(_input(), options)
    cached = await trigger.get_execution_status(result.execution_id)
    assert cached is not None
    assert cached.execution_id == "exec-cache"
    assert cached.output == {"value": 42}
