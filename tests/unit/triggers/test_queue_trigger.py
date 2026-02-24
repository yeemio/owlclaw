from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import pytest

from owlclaw.integrations.queue_adapters import MockQueueAdapter
from owlclaw.triggers.queue import MockIdempotencyStore, QueueTrigger, QueueTriggerConfig, RawMessage


class _FakeRuntime:
    def __init__(self, *, should_fail: bool = False, fail_times: int = 0) -> None:
        self.calls: list[dict[str, object]] = []
        self.should_fail = should_fail
        self.fail_times = fail_times

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
        if self.fail_times > 0:
            self.fail_times -= 1
            raise RuntimeError("runtime unavailable")
        return {"run_id": "run-1"}


class _CapturingStore(MockIdempotencyStore):
    def __init__(self) -> None:
        super().__init__()
        self.last_ttl: int | None = None

    async def set(self, key: str, value: object, ttl: int) -> None:
        self.last_ttl = ttl
        await super().set(key, value, ttl)


class _ExistsFailStore(MockIdempotencyStore):
    async def exists(self, key: str) -> bool:
        raise RuntimeError(f"exists failed: {key}")


class _FakeGovernance:
    def __init__(self, result: object) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []
        self.raise_error = False

    async def check_permission(self, context: dict[str, object]) -> object:
        self.calls.append(context)
        if self.raise_error:
            raise RuntimeError("governance offline")
        return self.result


class _FakeLedger:
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
    payload = runtime.calls[0]["payload"]
    assert isinstance(payload, dict)
    assert payload["message_id"] == "m-1"
    assert payload["source"] == "orders"
    assert payload["trace_id"] == "queue-m-1"
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
async def test_queue_trigger_retries_then_succeeds() -> None:
    adapter = MockQueueAdapter()
    runtime = _FakeRuntime(fail_times=2)
    trigger = QueueTrigger(
        config=QueueTriggerConfig(
            queue_name="orders",
            consumer_group="g1",
            max_retries=2,
            retry_backoff_base=0.001,
        ),
        adapter=adapter,
        agent_runtime=runtime,
    )
    msg = _raw_message(message_id="m-retry", body=b'{"id":"1"}')

    adapter.enqueue(msg)
    await trigger.start()
    await _flush_queue(adapter)
    await trigger.stop()

    assert len(runtime.calls) == 3
    assert adapter.get_acked() == ["m-retry"]


@pytest.mark.asyncio
async def test_queue_trigger_retry_exhausted_routes_by_ack_policy() -> None:
    adapter = MockQueueAdapter()
    runtime = _FakeRuntime(should_fail=True)
    trigger = QueueTrigger(
        config=QueueTriggerConfig(
            queue_name="orders",
            consumer_group="g1",
            max_retries=2,
            retry_backoff_base=0.001,
            ack_policy="dlq",
        ),
        adapter=adapter,
        agent_runtime=runtime,
    )
    msg = _raw_message(message_id="m-dlq", body=b'{"id":"1"}')

    adapter.enqueue(msg)
    await trigger.start()
    await _flush_queue(adapter)
    await trigger.stop()

    assert len(runtime.calls) == 3
    assert adapter.get_dlq()
    assert adapter.get_dlq()[0][0] == "m-dlq"


@pytest.mark.asyncio
async def test_queue_trigger_retry_logs_each_retry(caplog: pytest.LogCaptureFixture) -> None:
    adapter = MockQueueAdapter()
    runtime = _FakeRuntime(should_fail=True)
    trigger = QueueTrigger(
        config=QueueTriggerConfig(
            queue_name="orders",
            consumer_group="g1",
            max_retries=2,
            retry_backoff_base=0.001,
            ack_policy="ack",
        ),
        adapter=adapter,
        agent_runtime=runtime,
    )
    msg = _raw_message(message_id="m-log", body=b'{"id":"1"}')

    caplog.set_level(logging.WARNING)
    adapter.enqueue(msg)
    await trigger.start()
    await _flush_queue(adapter)
    await trigger.stop()

    retry_logs = [r for r in caplog.records if "trigger retry" in r.message]
    assert len(retry_logs) == 2


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


@pytest.mark.asyncio
async def test_queue_trigger_dedup_key_falls_back_to_message_id() -> None:
    adapter = MockQueueAdapter()
    runtime = _FakeRuntime()
    store = MockIdempotencyStore()
    trigger = QueueTrigger(
        config=QueueTriggerConfig(queue_name="orders", consumer_group="g1"),
        adapter=adapter,
        agent_runtime=runtime,
        idempotency_store=store,
    )

    msg = _raw_message(message_id="same-id", body=b'{"id":"1"}')
    adapter.enqueue(msg)
    adapter.enqueue(msg)
    await trigger.start()
    await _flush_queue(adapter)
    await trigger.stop()

    assert len(runtime.calls) == 1
    assert await store.exists("same-id") is True
    assert adapter.get_acked() == ["same-id", "same-id"]


@pytest.mark.asyncio
async def test_queue_trigger_idempotency_exists_failure_degrades_to_processing() -> None:
    adapter = MockQueueAdapter()
    runtime = _FakeRuntime()
    trigger = QueueTrigger(
        config=QueueTriggerConfig(queue_name="orders", consumer_group="g1"),
        adapter=adapter,
        agent_runtime=runtime,
        idempotency_store=_ExistsFailStore(),
    )
    msg = _raw_message(message_id="m-1", body=b'{"id":"1"}')

    adapter.enqueue(msg)
    await trigger.start()
    await _flush_queue(adapter)
    await trigger.stop()

    assert len(runtime.calls) == 1
    assert adapter.get_acked() == ["m-1"]


@pytest.mark.asyncio
async def test_queue_trigger_idempotency_record_uses_config_ttl() -> None:
    adapter = MockQueueAdapter()
    runtime = _FakeRuntime()
    store = _CapturingStore()
    trigger = QueueTrigger(
        config=QueueTriggerConfig(queue_name="orders", consumer_group="g1", idempotency_window=123),
        adapter=adapter,
        agent_runtime=runtime,
        idempotency_store=store,
    )
    msg = _raw_message(message_id="ttl-1", body=b'{"id":"1"}')

    adapter.enqueue(msg)
    await trigger.start()
    await _flush_queue(adapter)
    await trigger.stop()

    assert store.last_ttl == 123


def test_queue_trigger_backoff_formula() -> None:
    trigger = QueueTrigger(
        config=QueueTriggerConfig(
            queue_name="orders",
            consumer_group="g1",
            retry_backoff_base=0.5,
            retry_backoff_multiplier=3.0,
        ),
        adapter=MockQueueAdapter(),
    )
    assert trigger._compute_backoff_seconds(0) == pytest.approx(0.5)
    assert trigger._compute_backoff_seconds(1) == pytest.approx(1.5)
    assert trigger._compute_backoff_seconds(2) == pytest.approx(4.5)


@pytest.mark.asyncio
async def test_queue_trigger_governance_reject_routes_to_dlq_and_records_ledger() -> None:
    adapter = MockQueueAdapter()
    runtime = _FakeRuntime()
    governance = _FakeGovernance({"allowed": False, "reason": "blocked-by-policy"})
    ledger = _FakeLedger()
    trigger = QueueTrigger(
        config=QueueTriggerConfig(queue_name="orders", consumer_group="g1", ack_policy="dlq"),
        adapter=adapter,
        agent_runtime=runtime,
        governance=governance,
        ledger=ledger,
    )
    msg = _raw_message(message_id="g-1", body=b'{"id":"1"}')

    adapter.enqueue(msg)
    await trigger.start()
    await _flush_queue(adapter)
    await trigger.stop()

    assert len(runtime.calls) == 0
    assert adapter.get_dlq() == [("g-1", "blocked-by-policy")]
    assert len(governance.calls) == 1
    assert governance.calls[0]["queue"] == "orders"
    assert len(ledger.records) == 1
    assert ledger.records[0]["status"] == "blocked"


@pytest.mark.asyncio
async def test_queue_trigger_governance_unavailable_fails_open() -> None:
    adapter = MockQueueAdapter()
    runtime = _FakeRuntime()
    governance = _FakeGovernance({"allowed": True})
    governance.raise_error = True
    trigger = QueueTrigger(
        config=QueueTriggerConfig(queue_name="orders", consumer_group="g1"),
        adapter=adapter,
        agent_runtime=runtime,
        governance=governance,
    )
    msg = _raw_message(message_id="g-open", body=b'{"id":"1"}')

    adapter.enqueue(msg)
    await trigger.start()
    await _flush_queue(adapter)
    await trigger.stop()

    assert len(runtime.calls) == 1
    assert adapter.get_acked() == ["g-open"]


@pytest.mark.asyncio
async def test_queue_trigger_records_success_ledger_fields() -> None:
    adapter = MockQueueAdapter()
    runtime = _FakeRuntime()
    ledger = _FakeLedger()
    trigger = QueueTrigger(
        config=QueueTriggerConfig(queue_name="orders", consumer_group="g1"),
        adapter=adapter,
        agent_runtime=runtime,
        ledger=ledger,
    )
    msg = _raw_message(
        message_id="s-1",
        body=b'{"id":"1"}',
        headers={"x-event-name": "order_created", "x-tenant-id": "tenant-a"},
    )

    adapter.enqueue(msg)
    await trigger.start()
    await _flush_queue(adapter)
    await trigger.stop()

    assert len(ledger.records) == 1
    record = ledger.records[0]
    assert record["status"] == "success"
    assert record["tenant_id"] == "tenant-a"
    assert record["run_id"] == "queue-s-1"
    assert record["execution_time_ms"] >= 0
    input_params = record["input_params"]
    assert isinstance(input_params, dict)
    assert input_params["trace_id"] == "queue-s-1"
    assert input_params["message_id"] == "s-1"
    output_result = record["output_result"]
    assert isinstance(output_result, dict)
    assert output_result["agent_run_id"] == "run-1"


@pytest.mark.asyncio
async def test_queue_trigger_metrics_and_trace_logs(caplog: pytest.LogCaptureFixture) -> None:
    adapter = MockQueueAdapter()
    runtime = _FakeRuntime(should_fail=True)
    trigger = QueueTrigger(
        config=QueueTriggerConfig(
            queue_name="orders",
            consumer_group="g1",
            max_retries=1,
            retry_backoff_base=0.001,
            ack_policy="ack",
        ),
        adapter=adapter,
        agent_runtime=runtime,
    )
    caplog.set_level(logging.INFO)
    adapter.enqueue(_raw_message(message_id="m-log-2", body=b'{"id":"1"}'))
    await trigger.start()
    await _flush_queue(adapter)
    await trigger.stop()

    status = await trigger.health_check()
    metrics = status["metrics"]
    assert isinstance(metrics, dict)
    assert metrics["failed_total"] >= 1
    assert metrics["retries_total"] == 1
    assert any("trace_id=queue-m-log-2" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_queue_trigger_multi_tenant_propagation() -> None:
    adapter = MockQueueAdapter()
    runtime = _FakeRuntime()
    governance = _FakeGovernance({"allowed": True})
    ledger = _FakeLedger()
    trigger = QueueTrigger(
        config=QueueTriggerConfig(queue_name="orders", consumer_group="g1"),
        adapter=adapter,
        agent_runtime=runtime,
        governance=governance,
        ledger=ledger,
    )

    adapter.enqueue(
        _raw_message(
            message_id="mt-1",
            body=b'{"id":"1"}',
            headers={"x-tenant-id": "tenant-1"},
        )
    )
    adapter.enqueue(
        _raw_message(
            message_id="mt-2",
            body=b'{"id":"2"}',
            headers={"x-tenant-id": "tenant-2"},
        )
    )
    await trigger.start()
    await _flush_queue(adapter)
    await trigger.stop()

    runtime_tenants = {str(call["tenant_id"]) for call in runtime.calls}
    governance_tenants = {str(call["tenant_id"]) for call in governance.calls}
    ledger_tenants = {str(record["tenant_id"]) for record in ledger.records if record["status"] == "success"}

    assert runtime_tenants == {"tenant-1", "tenant-2"}
    assert governance_tenants == {"tenant-1", "tenant-2"}
    assert ledger_tenants == {"tenant-1", "tenant-2"}
