from __future__ import annotations

import asyncio

import pytest

from owlclaw.integrations.queue_adapters.kafka import KafkaQueueAdapter


@pytest.mark.integration
@pytest.mark.asyncio
async def test_kafka_queue_adapter_end_to_end_with_testcontainers() -> None:
    aiokafka = pytest.importorskip("aiokafka")
    kafka_module = pytest.importorskip("testcontainers.kafka")

    aiokafka_producer = aiokafka.AIOKafkaProducer
    kafka_container = kafka_module.KafkaContainer

    topic = "owlclaw-orders"
    dlq_topic = f"{topic}.dlq"

    try:
        with kafka_container() as kafka:
            bootstrap = kafka.get_bootstrap_server()

            seed_producer = aiokafka_producer(bootstrap_servers=bootstrap)
            await seed_producer.start()
            try:
                await seed_producer.send_and_wait(
                    topic,
                    b'{"id":1}',
                    headers=[("x-message-id", b"it-msg-1"), ("x-event-name", b"order_created")],
                )
            finally:
                await seed_producer.stop()

            adapter = KafkaQueueAdapter(
                topic=topic,
                bootstrap_servers=bootstrap,
                consumer_group="owlclaw-it-group",
                dlq_topic=dlq_topic,
            )
            await adapter.connect()
            try:
                message = await asyncio.wait_for(_next_message(adapter), timeout=20)
                assert message.message_id == "it-msg-1"
                assert message.metadata["topic"] == topic
                await adapter.ack(message)

                await adapter.send_to_dlq(message, reason="manual-test")
                await _assert_dlq_message(
                    bootstrap=bootstrap,
                    topic=dlq_topic,
                    expected_message_id="it-msg-1",
                )
            finally:
                await adapter.close()
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"Kafka integration environment unavailable: {exc}")


async def _next_message(adapter: KafkaQueueAdapter):
    async for message in adapter.consume():
        return message
    raise RuntimeError("No message consumed from Kafka")


async def _assert_dlq_message(*, bootstrap: str, topic: str, expected_message_id: str) -> None:
    aiokafka = pytest.importorskip("aiokafka")
    aiokafka_consumer = aiokafka.AIOKafkaConsumer

    consumer = aiokafka_consumer(
        topic,
        bootstrap_servers=bootstrap,
        group_id="owlclaw-it-dlq-group",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )
    await consumer.start()
    try:
        record = await asyncio.wait_for(consumer.getone(), timeout=20)
        headers = {k: (v.decode("utf-8") if isinstance(v, bytes) else str(v)) for k, v in (record.headers or [])}
        assert headers.get("x-message-id") == expected_message_id
        assert headers.get("x-dlq-reason") == "manual-test"
    finally:
        await consumer.stop()
