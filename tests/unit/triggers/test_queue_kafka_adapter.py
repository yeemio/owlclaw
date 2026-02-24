from __future__ import annotations

from types import SimpleNamespace

import pytest

from owlclaw.integrations.queue_adapters.kafka import KafkaQueueAdapter
from owlclaw.triggers.queue import RawMessage


class _FakeTopicPartition:
    def __init__(self, topic: str, partition: int) -> None:
        self.topic = topic
        self.partition = partition

    def __hash__(self) -> int:
        return hash((self.topic, self.partition))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _FakeTopicPartition):
            return False
        return self.topic == other.topic and self.partition == other.partition


class _FakeConsumer:
    def __init__(self, records: list[SimpleNamespace] | None = None) -> None:
        self.records = records or []
        self.started = False
        self.stopped = False
        self.commit_calls: list[dict[_FakeTopicPartition, int]] = []
        self.seek_calls: list[tuple[_FakeTopicPartition, int]] = []

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True

    def __aiter__(self) -> _FakeConsumer:
        return self

    async def __anext__(self) -> SimpleNamespace:
        if not self.records:
            raise StopAsyncIteration
        return self.records.pop(0)

    async def commit(self, offsets: dict[_FakeTopicPartition, int]) -> None:
        self.commit_calls.append(offsets)

    async def seek(self, topic_partition: _FakeTopicPartition, offset: int) -> None:
        self.seek_calls.append((topic_partition, offset))


class _FakeProducer:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False
        self.sent: list[dict[str, object]] = []

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True

    async def send_and_wait(
        self,
        topic: str,
        body: bytes,
        *,
        key: bytes | None = None,
        headers: list[tuple[str, bytes]] | None = None,
    ) -> None:
        self.sent.append({"topic": topic, "body": body, "key": key, "headers": headers or []})


def _record(
    *,
    value: bytes,
    topic: str = "orders",
    partition: int = 0,
    offset: int = 0,
    key: bytes | None = None,
    headers: list[tuple[str, bytes]] | None = None,
    timestamp: int = 1_700_000_000_000,
) -> SimpleNamespace:
    return SimpleNamespace(
        topic=topic,
        partition=partition,
        offset=offset,
        key=key,
        value=value,
        headers=headers or [],
        timestamp=timestamp,
    )


@pytest.mark.asyncio
async def test_kafka_queue_adapter_consume_and_ack() -> None:
    consumer = _FakeConsumer(records=[_record(value=b'{"ok":1}', offset=12, headers=[("x-message-id", b"m-1")])])
    producer = _FakeProducer()

    adapter = KafkaQueueAdapter(
        topic="orders",
        bootstrap_servers="localhost:9092",
        consumer_group="g1",
        consumer=consumer,
        producer=producer,
    )
    adapter._topic_partition_type = _FakeTopicPartition

    await adapter.connect()
    consumed = [message async for message in adapter.consume()]

    assert len(consumed) == 1
    assert consumed[0].message_id == "m-1"
    assert consumed[0].metadata["offset"] == 12

    await adapter.ack(consumed[0])
    assert consumer.commit_calls
    commit_map = consumer.commit_calls[0]
    [(topic_partition, committed_offset)] = list(commit_map.items())
    assert topic_partition.topic == "orders"
    assert topic_partition.partition == 0
    assert committed_offset == 13


@pytest.mark.asyncio
async def test_kafka_queue_adapter_nack_requeue_and_dlq() -> None:
    rec = _record(value=b"hello", topic="orders", partition=1, offset=5, headers=[("k", b"v")])
    consumer = _FakeConsumer(records=[rec])
    producer = _FakeProducer()

    adapter = KafkaQueueAdapter(
        topic="orders",
        bootstrap_servers="localhost:9092",
        consumer_group="g1",
        consumer=consumer,
        producer=producer,
        dlq_topic="orders.dead",
    )
    adapter._topic_partition_type = _FakeTopicPartition

    await adapter.connect()
    message = [item async for item in adapter.consume()][0]

    await adapter.nack(message, requeue=True)
    assert producer.sent
    assert producer.sent[0]["topic"] == "orders"
    assert consumer.seek_calls == [(_FakeTopicPartition("orders", 1), 5)]

    await adapter.send_to_dlq(message, reason="parse-error")
    assert producer.sent[1]["topic"] == "orders.dead"
    headers = dict(producer.sent[1]["headers"])
    assert headers["x-dlq-reason"] == b"parse-error"


@pytest.mark.asyncio
async def test_kafka_queue_adapter_health_and_close() -> None:
    consumer = _FakeConsumer()
    producer = _FakeProducer()
    adapter = KafkaQueueAdapter(
        topic="orders",
        bootstrap_servers="localhost:9092",
        consumer_group="g1",
        consumer=consumer,
        producer=producer,
    )
    adapter._topic_partition_type = _FakeTopicPartition

    assert await adapter.health_check() is False
    await adapter.connect()
    assert await adapter.health_check() is True

    await adapter.close()
    assert await adapter.health_check() is False
    assert consumer.stopped is True
    assert producer.stopped is True


@pytest.mark.asyncio
async def test_kafka_queue_adapter_requires_aiokafka(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_import_error() -> tuple[type[object], type[object], type[object]]:
        raise RuntimeError("Kafka adapter requires aiokafka. Install with: poetry add aiokafka")

    monkeypatch.setattr("owlclaw.integrations.queue_adapters.kafka._import_aiokafka", _raise_import_error)
    adapter = KafkaQueueAdapter(topic="orders", bootstrap_servers="localhost:9092", consumer_group="g1")

    with pytest.raises(RuntimeError, match="poetry add aiokafka"):
        await adapter.connect()


def test_kafka_queue_adapter_message_id_fallback_to_topic_partition_offset() -> None:
    adapter = KafkaQueueAdapter(
        topic="orders",
        bootstrap_servers="localhost:9092",
        consumer_group="g1",
        consumer=_FakeConsumer(),
        producer=_FakeProducer(),
    )
    record = _record(value=b"body", topic="orders", partition=2, offset=9)

    message = adapter._record_to_raw_message(record)

    assert message.message_id == "orders:2:9"
    assert isinstance(message, RawMessage)
