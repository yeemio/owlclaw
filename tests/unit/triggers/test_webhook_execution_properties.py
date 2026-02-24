from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.triggers.webhook import AgentInput, ExecutionOptions, ExecutionTrigger, RetryPolicy


@dataclass
class _Runtime:
    result: dict[str, Any]
    error_until_attempt: int = 0
    error: Exception | None = None
    calls: int = 0

    async def trigger(self, input_data: AgentInput) -> dict[str, Any]:  # noqa: ARG002
        self.calls += 1
        if self.error is not None and self.calls <= self.error_until_attempt:
            raise self.error
        return self.result


def _input() -> AgentInput:
    return AgentInput(agent_id="agent-prop", parameters={"k": "v"})


@given(execution_id=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-", min_size=1, max_size=24))
@settings(max_examples=30, deadline=None)
def test_property_validation_passed_triggers_execution(execution_id: str) -> None:
    """Feature: triggers-webhook, Property 11: 验证通过后触发代理执行."""

    async def _run() -> None:
        runtime = _Runtime(result={"execution_id": execution_id, "status": "completed"})
        trigger = ExecutionTrigger(runtime)
        result = await trigger.trigger(_input(), ExecutionOptions(mode="sync"))
        assert runtime.calls == 1
        assert result.execution_id == execution_id

    asyncio.run(_run())


@given(execution_id=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-", min_size=1, max_size=24))
@settings(max_examples=30, deadline=None)
def test_property_execution_start_returns_execution_info(execution_id: str) -> None:
    """Feature: triggers-webhook, Property 12: 执行启动返回执行信息."""

    async def _run() -> None:
        runtime = _Runtime(result={"execution_id": execution_id, "status": "completed"})
        trigger = ExecutionTrigger(runtime)
        result = await trigger.trigger(_input(), ExecutionOptions(mode="sync"))
        assert result.execution_id == execution_id
        assert result.started_at is not None

    asyncio.run(_run())


@given(message=st.text(min_size=1, max_size=30))
@settings(max_examples=25, deadline=None)
def test_property_runtime_unavailable_returns_service_unavailable(message: str) -> None:
    """Feature: triggers-webhook, Property 14: 运行时不可用返回 503."""

    async def _run() -> None:
        runtime = _Runtime(result={}, error_until_attempt=1, error=ConnectionError(message))
        trigger = ExecutionTrigger(runtime)
        result = await trigger.trigger(_input(), ExecutionOptions(mode="sync", retry_policy=RetryPolicy(max_attempts=1)))
        assert result.status == "failed"
        assert result.error is not None
        assert result.error["status_code"] == 503

    asyncio.run(_run())


@given(execution_id=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-", min_size=1, max_size=24))
@settings(max_examples=25, deadline=None)
def test_property_sync_mode_waits_for_completion(execution_id: str) -> None:
    """Feature: triggers-webhook, Property 17: 同步模式等待完成."""

    async def _run() -> None:
        runtime = _Runtime(result={"execution_id": execution_id, "status": "completed", "output": {"done": True}})
        trigger = ExecutionTrigger(runtime)
        result = await trigger.trigger(_input(), ExecutionOptions(mode="sync"))
        assert result.status == "completed"
        assert result.completed_at is not None

    asyncio.run(_run())


@given(execution_id=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-", min_size=1, max_size=24))
@settings(max_examples=25, deadline=None)
def test_property_async_mode_returns_immediately(execution_id: str) -> None:
    """Feature: triggers-webhook, Property 18: 异步模式立即返回."""

    async def _run() -> None:
        runtime = _Runtime(result={"execution_id": execution_id, "status": "running"})
        trigger = ExecutionTrigger(runtime)
        result = await trigger.trigger(_input(), ExecutionOptions(mode="async"))
        assert result.status == "accepted"
        assert result.completed_at is None

    asyncio.run(_run())


@given(idem_key=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-", min_size=1, max_size=24))
@settings(max_examples=25, deadline=None)
def test_property_idempotency_key_check(idem_key: str) -> None:
    """Feature: triggers-webhook, Property 27: 幂等性键检查."""

    async def _run() -> None:
        runtime = _Runtime(result={"execution_id": "idem-exec", "status": "completed"})
        trigger = ExecutionTrigger(runtime)
        options = ExecutionOptions(mode="sync", idempotency_key=idem_key)
        await trigger.trigger(_input(), options)
        cached = await trigger.check_idempotency(idem_key)
        assert cached is not None
        assert cached.execution_id == "idem-exec"

    asyncio.run(_run())


@given(idem_key=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-", min_size=1, max_size=24))
@settings(max_examples=25, deadline=None)
def test_property_idempotency_guarantee(idem_key: str) -> None:
    """Feature: triggers-webhook, Property 28: 幂等性保证."""

    async def _run() -> None:
        runtime = _Runtime(result={"execution_id": "idem-exec", "status": "completed"})
        trigger = ExecutionTrigger(runtime)
        options = ExecutionOptions(mode="sync", idempotency_key=idem_key)
        first = await trigger.trigger(_input(), options)
        second = await trigger.trigger(_input(), options)
        assert runtime.calls == 1
        assert first.execution_id == second.execution_id

    asyncio.run(_run())


@given(max_attempts=st.integers(min_value=2, max_value=4))
@settings(max_examples=20, deadline=None)
def test_property_failure_retries_automatically(max_attempts: int) -> None:
    """Feature: triggers-webhook, Property 29: 失败自动重试."""

    async def _run() -> None:
        runtime = _Runtime(
            result={"execution_id": "retry-ok", "status": "completed"},
            error_until_attempt=max_attempts - 1,
            error=ConnectionError("temporary"),
        )
        trigger = ExecutionTrigger(runtime)
        result = await trigger.trigger(
            _input(),
            ExecutionOptions(
                mode="sync",
                retry_policy=RetryPolicy(
                    max_attempts=max_attempts,
                    initial_delay_ms=1,
                    max_delay_ms=10,
                    backoff_multiplier=2.0,
                ),
            ),
        )
        assert result.status == "completed"
        assert runtime.calls == max_attempts

    asyncio.run(_run())
