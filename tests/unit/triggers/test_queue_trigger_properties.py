from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.integrations.queue_adapters import MockQueueAdapter
from owlclaw.triggers.queue import MockIdempotencyStore, QueueTrigger, QueueTriggerConfig, RawMessage


class _CountingRuntime:
    def __init__(self) -> None:
        self.calls = 0

    async def trigger_event(self, **_: object) -> dict[str, object]:
        self.calls += 1
        return {"run_id": f"run-{self.calls}"}


class _RejectGovernance:
    async def check_permission(self, context: dict[str, object]) -> dict[str, object]:
        return {"allowed": False, "reason": f"blocked:{context['message_id']}"}


class _FailNTimesRuntime:
    def __init__(self, fail_times: int) -> None:
        self.fail_times = fail_times
        self.calls = 0

    async def trigger_event(self, **_: object) -> dict[str, object]:
        self.calls += 1
        if self.fail_times > 0:
            self.fail_times -= 1
            raise RuntimeError("transient failure")
        return {"run_id": f"run-{self.calls}"}


class _CaptureRuntime:
    def __init__(self) -> None:
        self.last_event_name: str | None = None
        self.last_payload: dict[str, object] | None = None
        self.last_tenant_id: str | None = None

    async def trigger_event(
        self,
        *,
        event_name: str,
        payload: dict[str, object],
        focus: str | None = None,
        tenant_id: str = "default",
    ) -> dict[str, object]:
        self.last_event_name = event_name
        self.last_payload = payload
        self.last_tenant_id = tenant_id
        return {"run_id": "run-1", "focus": focus}


class _AlwaysFailRuntime:
    async def trigger_event(self, **_: object) -> dict[str, object]:
        raise RuntimeError("boom")


class _AllowGovernance:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def check_permission(self, context: dict[str, object]) -> dict[str, object]:
        self.calls.append(context)
        return {"allowed": True}


class _CollectLedger:
    def __init__(self) -> None:
        self.records: list[dict[str, object]] = []

    async def record_execution(self, **kwargs: object) -> None:
        self.records.append(kwargs)


def _raw_message(message_id: str, body: bytes, headers: dict[str, str] | None = None) -> RawMessage:
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


@given(
    actions=st.lists(st.sampled_from(["pause", "resume"]), min_size=1, max_size=8),
)
@settings(max_examples=20, deadline=None)
def test_property_queue_lifecycle_state_transitions(actions: list[str]) -> None:
    """Feature: triggers-queue, Property 6: 生命周期状态转换."""

    async def _run() -> None:
        trigger = QueueTrigger(
            config=QueueTriggerConfig(queue_name="q", consumer_group="g"),
            adapter=MockQueueAdapter(),
        )
        await trigger.start()
        for action in actions:
            if action == "pause":
                await trigger.pause()
            else:
                await trigger.resume()
        status = await trigger.health_check()
        assert status["running"] is True
        await trigger.stop()
        stopped = await trigger.health_check()
        assert stopped["running"] is False

    asyncio.run(_run())


@given(
    invalid_payload=st.binary(min_size=1).filter(lambda data: data[:1] != b"{"),
)
@settings(max_examples=20, deadline=None)
def test_property_parse_failure_routes_to_dlq(invalid_payload: bytes) -> None:
    """Feature: triggers-queue, Property 4: 解析失败路由到死信."""

    async def _run() -> None:
        adapter = MockQueueAdapter()
        trigger = QueueTrigger(
            config=QueueTriggerConfig(queue_name="q", consumer_group="g", parser_type="json"),
            adapter=adapter,
        )
        adapter.enqueue(_raw_message("bad", invalid_payload))
        await trigger.start()
        await _flush_queue(adapter)
        await trigger.stop()
        assert adapter.get_dlq()
        assert adapter.get_dlq()[0][0] == "bad"

    asyncio.run(_run())


@given(good_payload=st.dictionaries(st.text(min_size=1, max_size=8), st.integers(), max_size=3))
@settings(max_examples=20, deadline=None)
def test_property_error_recovery_continues_processing(good_payload: dict[str, int]) -> None:
    """Feature: triggers-queue, Property 7: 错误恢复与继续处理."""

    async def _run() -> None:
        adapter = MockQueueAdapter()
        trigger = QueueTrigger(
            config=QueueTriggerConfig(queue_name="q", consumer_group="g", parser_type="json"),
            adapter=adapter,
        )
        adapter.enqueue(_raw_message("bad", b"broken-json"))
        import json

        adapter.enqueue(_raw_message("good", json.dumps(good_payload).encode("utf-8")))
        await trigger.start()
        await _flush_queue(adapter)
        await trigger.stop()

        dlq_ids = [message_id for message_id, _ in adapter.get_dlq()]
        ack_ids = adapter.get_acked()
        assert "bad" in dlq_ids
        assert "good" in ack_ids

    asyncio.run(_run())


@given(
    dedup_keys=st.lists(st.text(min_size=1, max_size=8), min_size=1, max_size=20),
)
@settings(max_examples=20, deadline=None)
def test_property_dedup_counter_matches_duplicate_count(dedup_keys: list[str]) -> None:
    """Feature: triggers-queue, Property 15+17: 幂等性保证与去重计数准确性."""

    async def _run() -> None:
        adapter = MockQueueAdapter()
        runtime = _CountingRuntime()
        trigger = QueueTrigger(
            config=QueueTriggerConfig(queue_name="q", consumer_group="g", parser_type="json"),
            adapter=adapter,
            agent_runtime=runtime,
            idempotency_store=MockIdempotencyStore(),
        )

        for idx, key in enumerate(dedup_keys):
            adapter.enqueue(
                _raw_message(
                    message_id=f"m-{idx}",
                    body=b'{"id":1}',
                    headers={"x-dedup-key": key},
                )
            )

        await trigger.start()
        await _flush_queue(adapter)
        await trigger.stop()

        unique_count = len(set(dedup_keys))
        duplicate_count = len(dedup_keys) - unique_count
        health = await trigger.health_check()
        assert runtime.calls == unique_count
        assert health["dedup_hits"] == duplicate_count

    asyncio.run(_run())


@given(policy=st.sampled_from(["ack", "nack", "requeue", "dlq"]))
@settings(max_examples=20, deadline=None)
def test_property_governance_rejection_respects_ack_policy(policy: str) -> None:
    """Feature: triggers-queue, Property 10: 治理层拒绝处理遵循 ack_policy."""

    async def _run() -> None:
        adapter = MockQueueAdapter()
        trigger = QueueTrigger(
            config=QueueTriggerConfig(queue_name="q", consumer_group="g", ack_policy=policy),
            adapter=adapter,
            governance=_RejectGovernance(),
        )
        adapter.enqueue(_raw_message("gov-1", b'{"id":1}'))
        await trigger.start()
        await _flush_queue(adapter)
        await trigger.stop()

        if policy == "ack":
            assert adapter.get_acked() == ["gov-1"]
        elif policy == "nack":
            assert adapter.get_nacked() == [("gov-1", False)]
        elif policy == "requeue":
            assert ("gov-1", True) in adapter.get_nacked()
        else:
            assert adapter.get_dlq() == [("gov-1", "blocked:gov-1")]

    asyncio.run(_run())


@given(
    fail_times=st.integers(min_value=0, max_value=5),
    max_retries=st.integers(min_value=0, max_value=5),
)
@settings(max_examples=20, deadline=None)
def test_property_retry_attempts_are_bounded(fail_times: int, max_retries: int) -> None:
    """Feature: triggers-queue, Property 12: 重试次数有界且符合配置."""

    async def _run() -> None:
        adapter = MockQueueAdapter()
        runtime = _FailNTimesRuntime(fail_times=fail_times)
        trigger = QueueTrigger(
            config=QueueTriggerConfig(
                queue_name="q",
                consumer_group="g",
                max_retries=max_retries,
                retry_backoff_base=0.0001,
            ),
            adapter=adapter,
            agent_runtime=runtime,
        )

        adapter.enqueue(_raw_message("retry-1", b'{"id":1}'))
        await trigger.start()
        await _flush_queue(adapter)
        await trigger.stop()

        expected_attempts = min(max_retries + 1, fail_times + 1)
        assert runtime.calls == expected_attempts

    asyncio.run(_run())


@given(
    event_name=st.one_of(st.none(), st.text(min_size=1, max_size=12)),
    tenant_id=st.one_of(st.none(), st.text(min_size=1, max_size=12)),
)
@settings(max_examples=20, deadline=None)
def test_property_trigger_event_context_and_routing(event_name: str | None, tenant_id: str | None) -> None:
    """Feature: triggers-queue, Property 8+9: 上下文传递与事件路由正确性."""

    async def _run() -> None:
        adapter = MockQueueAdapter()
        runtime = _CaptureRuntime()
        headers: dict[str, str] = {}
        if event_name is not None:
            headers["x-event-name"] = event_name
        if tenant_id is not None:
            headers["x-tenant-id"] = tenant_id

        trigger = QueueTrigger(
            config=QueueTriggerConfig(queue_name="q", consumer_group="g"),
            adapter=adapter,
            agent_runtime=runtime,
        )
        adapter.enqueue(_raw_message("ctx-1", b'{"id":1}', headers=headers))
        await trigger.start()
        await _flush_queue(adapter)
        await trigger.stop()

        assert runtime.last_payload is not None
        assert runtime.last_payload["message_id"] == "ctx-1"
        assert runtime.last_payload["source"] == "q"
        assert "received_at" in runtime.last_payload
        assert runtime.last_event_name == (event_name if event_name is not None else "queue_message")
        assert runtime.last_tenant_id == (tenant_id if tenant_id is not None else "default")

    asyncio.run(_run())


@given(policy=st.sampled_from(["ack", "nack", "requeue", "dlq"]))
@settings(max_examples=20, deadline=None)
def test_property_processing_error_respects_ack_policy(policy: str) -> None:
    """Feature: triggers-queue, Property 11+13: 错误策略与重试耗尽处理."""

    async def _run() -> None:
        adapter = MockQueueAdapter()
        trigger = QueueTrigger(
            config=QueueTriggerConfig(
                queue_name="q",
                consumer_group="g",
                ack_policy=policy,
                max_retries=0,
            ),
            adapter=adapter,
            agent_runtime=_AlwaysFailRuntime(),
        )
        adapter.enqueue(_raw_message("err-1", b'{"id":1}'))
        await trigger.start()
        await _flush_queue(adapter)
        await trigger.stop()

        if policy == "ack":
            assert adapter.get_acked() == ["err-1"]
        elif policy == "nack":
            assert adapter.get_nacked() == [("err-1", False)]
        elif policy == "requeue":
            assert ("err-1", True) in adapter.get_nacked()
        else:
            assert adapter.get_dlq()
            assert adapter.get_dlq()[0][0] == "err-1"

    asyncio.run(_run())


@given(
    tenant_id=st.text(min_size=1, max_size=12),
    event_name=st.text(min_size=1, max_size=12),
)
@settings(max_examples=20, deadline=None)
def test_property_ledger_success_record_completeness(tenant_id: str, event_name: str) -> None:
    """Feature: triggers-queue, Property 18+19: Ledger 记录与指标字段完整性."""

    async def _run() -> None:
        adapter = MockQueueAdapter()
        ledger = _CollectLedger()
        trigger = QueueTrigger(
            config=QueueTriggerConfig(queue_name="q", consumer_group="g"),
            adapter=adapter,
            agent_runtime=_CaptureRuntime(),
            ledger=ledger,
        )
        adapter.enqueue(
            _raw_message(
                "ledger-1",
                b'{"id":1}',
                headers={"x-tenant-id": tenant_id, "x-event-name": event_name},
            )
        )
        await trigger.start()
        await _flush_queue(adapter)
        await trigger.stop()

        assert ledger.records
        record = ledger.records[-1]
        assert record["status"] == "success"
        assert record["tenant_id"] == tenant_id
        assert record["run_id"] == "queue-ledger-1"
        assert record["execution_time_ms"] >= 0
        status = await trigger.health_check()
        assert status["metrics"]["processed_total"] >= 1

    asyncio.run(_run())


@given(
    tenant_a=st.text(min_size=1, max_size=8),
    tenant_b=st.text(min_size=1, max_size=8).filter(lambda t: t.strip() != ""),
)
@settings(max_examples=20, deadline=None)
def test_property_multi_tenant_isolation_propagation(tenant_a: str, tenant_b: str) -> None:
    """Feature: triggers-queue, Property 20: 多租户隔离透传."""

    async def _run() -> None:
        tenant_b_local = f"{tenant_b}-b" if tenant_a == tenant_b else tenant_b

        adapter = MockQueueAdapter()
        governance = _AllowGovernance()
        ledger = _CollectLedger()
        runtime = _CaptureRuntime()
        trigger = QueueTrigger(
            config=QueueTriggerConfig(queue_name="q", consumer_group="g"),
            adapter=adapter,
            agent_runtime=runtime,
            governance=governance,
            ledger=ledger,
        )
        adapter.enqueue(_raw_message("t-1", b'{"id":1}', headers={"x-tenant-id": tenant_a}))
        adapter.enqueue(_raw_message("t-2", b'{"id":2}', headers={"x-tenant-id": tenant_b_local}))
        await trigger.start()
        await _flush_queue(adapter)
        await trigger.stop()

        governance_tenants = {str(call["tenant_id"]) for call in governance.calls}
        ledger_tenants = {str(record["tenant_id"]) for record in ledger.records if record["status"] == "success"}
        assert governance_tenants == {tenant_a, tenant_b_local}
        assert ledger_tenants == {tenant_a, tenant_b_local}

    asyncio.run(_run())
