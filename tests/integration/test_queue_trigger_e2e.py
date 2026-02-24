from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from owlclaw.integrations.queue_adapters import MockQueueAdapter
from owlclaw.triggers.queue import MockIdempotencyStore, QueueTrigger, QueueTriggerConfig, RawMessage


class _RuntimeRecorder:
    def __init__(self, fail_times: int = 0) -> None:
        self.fail_times = fail_times
        self.calls: list[dict[str, object]] = []

    async def trigger_event(
        self,
        *,
        event_name: str,
        payload: dict[str, object],
        focus: str | None = None,
        tenant_id: str = "default",
    ) -> dict[str, object]:
        self.calls.append(
            {
                "event_name": event_name,
                "payload": payload,
                "focus": focus,
                "tenant_id": tenant_id,
            }
        )
        if self.fail_times > 0:
            self.fail_times -= 1
            raise RuntimeError("runtime transient failure")
        return {"run_id": f"run-{len(self.calls)}"}


class _GovernanceRecorder:
    def __init__(self, allow: bool = True, reason: str = "") -> None:
        self.allow = allow
        self.reason = reason
        self.calls: list[dict[str, object]] = []

    async def check_permission(self, context: dict[str, object]) -> dict[str, object]:
        self.calls.append(context)
        if self.allow:
            return {"allowed": True}
        return {"allowed": False, "reason": self.reason or "blocked-by-governance"}


class _LedgerRecorder:
    def __init__(self) -> None:
        self.records: list[dict[str, object]] = []

    async def record_execution(self, **kwargs: object) -> None:
        self.records.append(kwargs)


def _raw_message(
    *,
    message_id: str,
    body: bytes,
    headers: dict[str, str] | None = None,
) -> RawMessage:
    return RawMessage(
        message_id=message_id,
        body=body,
        headers=headers or {},
        timestamp=datetime.now(timezone.utc),
        metadata={},
    )


async def _flush_queue(adapter: MockQueueAdapter) -> None:
    for _ in range(80):
        if adapter.pending_count() == 0:
            break
        await asyncio.sleep(0.01)
    await asyncio.sleep(0.05)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_queue_trigger_e2e_full_processing_flow() -> None:
    """Task 21.1: 完整链路（解析→幂等→治理→触发→Ledger→ACK）。"""
    adapter = MockQueueAdapter()
    runtime = _RuntimeRecorder()
    governance = _GovernanceRecorder(allow=True)
    ledger = _LedgerRecorder()
    store = MockIdempotencyStore()

    trigger = QueueTrigger(
        config=QueueTriggerConfig(queue_name="orders", consumer_group="g1"),
        adapter=adapter,
        agent_runtime=runtime,
        governance=governance,
        ledger=ledger,
        idempotency_store=store,
    )

    adapter.enqueue(
        _raw_message(
            message_id="e2e-1",
            body=b'{"order_id": 1}',
            headers={
                "x-dedup-key": "dup-e2e-1",
                "x-event-name": "order_created",
                "x-tenant-id": "tenant-a",
            },
        )
    )

    await trigger.start()
    await _flush_queue(adapter)
    await trigger.stop()

    assert len(runtime.calls) == 1
    assert runtime.calls[0]["event_name"] == "order_created"
    assert runtime.calls[0]["tenant_id"] == "tenant-a"
    assert governance.calls and governance.calls[0]["tenant_id"] == "tenant-a"
    assert adapter.get_acked() == ["e2e-1"]
    assert await store.exists("dup-e2e-1") is True
    assert ledger.records and ledger.records[-1]["status"] == "success"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_queue_trigger_e2e_idempotency_only_executes_once() -> None:
    """Task 21.2: 重复消息只执行一次，并记录去重命中。"""
    adapter = MockQueueAdapter()
    runtime = _RuntimeRecorder()
    trigger = QueueTrigger(
        config=QueueTriggerConfig(queue_name="orders", consumer_group="g1"),
        adapter=adapter,
        agent_runtime=runtime,
        idempotency_store=MockIdempotencyStore(),
    )

    msg = _raw_message(
        message_id="dup-msg",
        body=b'{"order_id": 2}',
        headers={"x-dedup-key": "dedup-key-2"},
    )
    adapter.enqueue(msg)
    adapter.enqueue(msg)

    await trigger.start()
    await _flush_queue(adapter)
    await trigger.stop()

    status = await trigger.health_check()
    assert len(runtime.calls) == 1
    assert status["dedup_hits"] == 1
    assert adapter.get_acked() == ["dup-msg", "dup-msg"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_queue_trigger_e2e_retry_flow_and_exhausted_to_dlq(monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 21.3: 失败重试、退避时序、耗尽后 DLQ。"""
    sleep_delays: list[float] = []

    original_sleep = asyncio.sleep

    async def _fake_sleep(delay: float) -> None:
        sleep_delays.append(delay)
        await original_sleep(0)

    monkeypatch.setattr("owlclaw.triggers.queue.trigger.asyncio.sleep", _fake_sleep)

    adapter = MockQueueAdapter()
    runtime = _RuntimeRecorder(fail_times=10)
    trigger = QueueTrigger(
        config=QueueTriggerConfig(
            queue_name="orders",
            consumer_group="g1",
            max_retries=2,
            retry_backoff_base=0.25,
            retry_backoff_multiplier=2.0,
            ack_policy="dlq",
        ),
        adapter=adapter,
        agent_runtime=runtime,
    )

    adapter.enqueue(_raw_message(message_id="retry-msg", body=b'{"order_id": 3}'))

    await trigger.start()
    await _flush_queue(adapter)
    await trigger.stop()

    assert len(runtime.calls) == 3
    retry_delays = [delay for delay in sleep_delays if delay >= 0.1]
    assert retry_delays[:2] == [0.25, 0.5]
    assert adapter.get_dlq() and adapter.get_dlq()[0][0] == "retry-msg"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_queue_trigger_e2e_error_scenarios_keep_system_running() -> None:
    """Task 21.4: 解析失败/治理拒绝/执行失败后系统继续处理后续消息。"""
    adapter = MockQueueAdapter()
    runtime = _RuntimeRecorder(fail_times=1)
    governance = _GovernanceRecorder(allow=True)
    ledger = _LedgerRecorder()
    trigger = QueueTrigger(
        config=QueueTriggerConfig(
            queue_name="orders",
            consumer_group="g1",
            ack_policy="ack",
            max_retries=0,
        ),
        adapter=adapter,
        agent_runtime=runtime,
        governance=governance,
        ledger=ledger,
    )

    # Parse error
    adapter.enqueue(_raw_message(message_id="bad-json", body=b"not-json"))

    # Governance reject
    async def _reject_once(context: dict[str, object]) -> dict[str, object]:
        governance.calls.append(context)
        if context["message_id"] == "blocked":
            return {"allowed": False, "reason": "policy"}
        return {"allowed": True}

    governance.check_permission = _reject_once  # type: ignore[method-assign]
    adapter.enqueue(_raw_message(message_id="blocked", body=b'{"order_id": 4}'))

    # Runtime failure then continue
    adapter.enqueue(_raw_message(message_id="runtime-fail", body=b'{"order_id": 5}'))
    adapter.enqueue(_raw_message(message_id="ok-after-fail", body=b'{"order_id": 6}'))

    await trigger.start()
    await _flush_queue(adapter)
    await trigger.stop()

    dlq_ids = [message_id for message_id, _ in adapter.get_dlq()]
    assert "bad-json" in dlq_ids
    assert "blocked" in adapter.get_acked()
    assert "runtime-fail" in adapter.get_acked()
    assert "ok-after-fail" in adapter.get_acked()
    blocked_records = [record for record in ledger.records if record.get("status") == "blocked"]
    assert blocked_records
