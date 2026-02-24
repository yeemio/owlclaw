from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from owlclaw.integrations.queue_adapters import MockQueueAdapter
from owlclaw.triggers.queue import MockIdempotencyStore, QueueTrigger, QueueTriggerConfig, RawMessage


class _FakeRuntime:
    def __init__(self, *, should_fail: bool = False) -> None:
        self.calls: list[dict[str, object]] = []
        self.should_fail = should_fail

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
        if self.should_fail:
            raise RuntimeError("runtime unavailable")
        return {"run_id": "run-1"}


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
    for _ in range(50):
        if adapter.pending_count() == 0:
            break
        await asyncio.sleep(0.01)
    await asyncio.sleep(0.02)


@pytest.mark.asyncio
async def test_queue_trigger_lifecycle_health() -> None:
    adapter = MockQueueAdapter()
    trigger = QueueTrigger(
        config=QueueTriggerConfig(queue_name="q1", consumer_group="g1"),
        adapter=adapter,
    )

    await trigger.start()
    status = await trigger.health_check()
    assert status["running"] is True
    assert status["paused"] is False
    assert status["active_workers"] == 1

    await trigger.pause()
    status = await trigger.health_check()
    assert status["paused"] is True

    await trigger.resume()
    status = await trigger.health_check()
    assert status["paused"] is False

    await trigger.stop()
    status = await trigger.health_check()
    assert status["running"] is False


@pytest.mark.asyncio
async def test_queue_trigger_process_and_dedup() -> None:
    adapter = MockQueueAdapter()
    runtime = _FakeRuntime()
    store = MockIdempotencyStore()
    trigger = QueueTrigger(
        config=QueueTriggerConfig(queue_name="orders", consumer_group="g1", focus="ops"),
        adapter=adapter,
        agent_runtime=runtime,
        idempotency_store=store,
    )

    msg = _raw_message(
        message_id="m-1",
        body=b'{"id":"1"}',
        headers={"x-dedup-key": "dedup-1", "x-event-name": "order_created", "x-tenant-id": "t-1"},
    )
    adapter.enqueue(msg)
    await trigger.start()
    await _flush_queue(adapter)
    await trigger.stop()

    assert len(runtime.calls) == 1
    assert runtime.calls[0]["event_name"] == "order_created"
    assert runtime.calls[0]["focus"] == "ops"
    assert runtime.calls[0]["tenant_id"] == "t-1"
    assert adapter.get_acked() == ["m-1"]

    adapter.enqueue(msg)
    await trigger.start()
    await _flush_queue(adapter)
    await trigger.stop()

    assert len(runtime.calls) == 1


@pytest.mark.asyncio
async def test_queue_trigger_parse_failure_routes_to_dlq() -> None:
    adapter = MockQueueAdapter()
    trigger = QueueTrigger(
        config=QueueTriggerConfig(queue_name="orders", consumer_group="g1", parser_type="json"),
        adapter=adapter,
    )
    bad = _raw_message(message_id="bad-1", body=b"not-json")

    adapter.enqueue(bad)
    await trigger.start()
    await _flush_queue(adapter)
    await trigger.stop()

    assert adapter.get_dlq()
    assert adapter.get_dlq()[0][0] == "bad-1"


@pytest.mark.asyncio
async def test_queue_trigger_ack_policy_requeue_on_runtime_error() -> None:
    adapter = MockQueueAdapter()
    runtime = _FakeRuntime(should_fail=True)
    trigger = QueueTrigger(
        config=QueueTriggerConfig(queue_name="orders", consumer_group="g1", ack_policy="requeue"),
        adapter=adapter,
        agent_runtime=runtime,
    )
    msg = _raw_message(message_id="m-requeue", body=b'{"id":"1"}')

    adapter.enqueue(msg)
    await trigger.start()
    await _flush_queue(adapter)
    await trigger.stop()

    assert ("m-requeue", True) in adapter.get_nacked()


@pytest.mark.asyncio
async def test_queue_trigger_init_rejects_invalid_config() -> None:
    with pytest.raises(ValueError, match="Invalid QueueTriggerConfig"):
        QueueTrigger(
            config=QueueTriggerConfig(queue_name="", consumer_group="g1"),
            adapter=MockQueueAdapter(),
        )


@pytest.mark.asyncio
async def test_queue_trigger_consume_loop_recovers_after_process_exception() -> None:
    adapter = MockQueueAdapter()
    trigger = QueueTrigger(
        config=QueueTriggerConfig(queue_name="orders", consumer_group="g1"),
        adapter=adapter,
    )
    first = _raw_message(message_id="m-1", body=b'{"id":"1"}')
    second = _raw_message(message_id="m-2", body=b'{"id":"2"}')
    adapter.enqueue(first)
    adapter.enqueue(second)

    calls = {"count": 0}

    async def flaky_process(raw_message: RawMessage) -> object:
        calls["count"] += 1
        if raw_message.message_id == "m-1":
            raise RuntimeError("boom")
        return object()

    trigger._process_message = flaky_process  # type: ignore[method-assign]

    await trigger.start()
    await _flush_queue(adapter)
    await trigger.stop()

    assert calls["count"] >= 2
