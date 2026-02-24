from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import pytest

from owlclaw.integrations.queue_adapters import MockQueueAdapter
from owlclaw.triggers.queue import (
    QueueTrigger,
    QueueTriggerConfig,
    RawMessage,
    SensitiveDataLogFilter,
    redact_error_message,
    redact_sensitive_data,
)


class _FailRuntime:
    async def trigger_event(self, **_: object) -> dict[str, object]:
        raise RuntimeError("token=abc123 password=topsecret Authorization=Bearer abc123")


def _raw_message(message_id: str) -> RawMessage:
    return RawMessage(
        message_id=message_id,
        body=b'{"id":1}',
        headers={},
        timestamp=datetime.now(timezone.utc),
        metadata={},
    )


async def _flush_queue(adapter: MockQueueAdapter) -> None:
    for _ in range(80):
        if adapter.pending_count() == 0:
            break
        await asyncio.sleep(0.01)
    await asyncio.sleep(0.05)


def test_redact_sensitive_data_masks_sensitive_keys() -> None:
    payload = {
        "password": "p@ss",
        "nested": {"api_key": "sk-abcdef", "x": "ok", "token_hint": "should-hide"},
        "note": "Authorization=Bearer token-value",
    }

    redacted = redact_sensitive_data(payload)

    assert redacted["password"] == "***"
    assert redacted["nested"]["api_key"] == "***"
    assert redacted["nested"]["token_hint"] == "***"
    assert redacted["note"] == "Authorization=Bearer ***"


def test_queue_config_repr_redacts_adapter_credentials() -> None:
    config = QueueTriggerConfig(
        queue_name="orders",
        consumer_group="workers",
        adapter_config={
            "connection": {
                "username": "owlclaw",
                "password": "super-secret",
                "token": "abc123",
            }
        },
    )

    rendered = repr(config)

    assert "super-secret" not in rendered
    assert "abc123" not in rendered
    assert "***" in rendered


def test_sensitive_log_filter_redacts_message_args(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("tests.queue.security")
    logger.setLevel(logging.WARNING)
    log_filter = SensitiveDataLogFilter()
    logger.addFilter(log_filter)

    caplog.set_level(logging.WARNING, logger="tests.queue.security")
    logger.warning("failed token=%s password=%s", "abc123", "secret")

    assert caplog.records
    message = caplog.records[-1].message
    assert "abc123" not in message
    assert "secret" not in message
    assert "***" in message

    logger.removeFilter(log_filter)


def test_redact_error_message_masks_credential_patterns() -> None:
    raw = "failed with token=abc123 api_key=sk-abcdef Authorization=Bearer abc123"
    redacted = redact_error_message(raw)

    assert "abc123" not in redacted
    assert "sk-abcdef" not in redacted
    assert "token=***" in redacted
    assert "api_key=***" in redacted


@pytest.mark.asyncio
async def test_queue_trigger_error_and_dlq_reason_are_redacted(caplog: pytest.LogCaptureFixture) -> None:
    adapter = MockQueueAdapter()
    trigger = QueueTrigger(
        config=QueueTriggerConfig(queue_name="orders", consumer_group="g1", max_retries=0, ack_policy="dlq"),
        adapter=adapter,
        agent_runtime=_FailRuntime(),
    )
    adapter.enqueue(_raw_message("m-sec"))

    caplog.set_level(logging.WARNING)
    await trigger.start()
    await _flush_queue(adapter)
    await trigger.stop()

    assert adapter.get_dlq()
    dlq_reason = adapter.get_dlq()[0][1]
    assert "abc123" not in dlq_reason
    assert "topsecret" not in dlq_reason
    assert "***" in dlq_reason

    log_messages = "\n".join(record.message for record in caplog.records)
    assert "abc123" not in log_messages
    assert "topsecret" not in log_messages
