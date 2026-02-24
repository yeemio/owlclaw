from __future__ import annotations

from datetime import datetime

from owlclaw.triggers.queue import JSONParser, MessageEnvelope, QueueTriggerConfig, RawMessage, validate_config


def test_message_envelope_from_raw_message_extracts_headers() -> None:
    raw = RawMessage(
        message_id="m-1",
        body=b'{"foo":"bar"}',
        headers={
            "x-dedup-key": "k-1",
            "x-event-name": "order_created",
            "x-tenant-id": "tenant-a",
        },
        timestamp=datetime(2026, 2, 24, 12, 0, 0),
        metadata={},
    )

    envelope = MessageEnvelope.from_raw_message(raw, source="orders-queue", parser=JSONParser())

    assert envelope.message_id == "m-1"
    assert envelope.source == "orders-queue"
    assert envelope.payload == {"foo": "bar"}
    assert envelope.dedup_key == "k-1"
    assert envelope.event_name == "order_created"
    assert envelope.tenant_id == "tenant-a"
    assert envelope.received_at.tzinfo is not None


def test_validate_config_reports_invalid_values() -> None:
    config = QueueTriggerConfig(
        queue_name="",
        consumer_group="",
        concurrency=0,
        max_retries=-1,
        retry_backoff_base=0.0,
        retry_backoff_multiplier=0.5,
        idempotency_window=0,
    )
    errors = validate_config(config)
    assert len(errors) >= 7
