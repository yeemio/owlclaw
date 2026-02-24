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
