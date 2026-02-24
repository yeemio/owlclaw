from __future__ import annotations

import json
from typing import Any

import pytest

from owlclaw.capabilities.bindings import CredentialResolver, QueueBindingConfig, QueueBindingExecutor


class _FakePublisher:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def publish(self, topic: str, message: bytes, headers: dict[str, str] | None = None) -> None:
        self.calls.append({"topic": topic, "message": message, "headers": dict(headers or {})})


@pytest.mark.asyncio
async def test_queue_executor_active_publish_with_headers_mapping() -> None:
    publisher = _FakePublisher()

    def factory(provider: str, connection: str, topic: str) -> _FakePublisher:
        assert provider == "kafka"
        assert connection == "kafka://localhost:9092"
        assert topic == "orders"
        return publisher

    executor = QueueBindingExecutor(
        credential_resolver=CredentialResolver(config_secrets={"QUEUE_CONN": "kafka://localhost:9092"}),
        adapter_factory=factory,
    )
    config = QueueBindingConfig(
        provider="kafka",
        connection="${QUEUE_CONN}",
        topic="orders",
        headers_mapping={"x-user": "{user_id}", "x-kind": "order"},
    )

    result = await executor.execute(config, {"user_id": 42, "order_id": "o-1"})
    assert result["status"] == "ok"
    assert result["sent"] is True
    assert publisher.calls[0]["headers"] == {"x-user": "42", "x-kind": "order"}
    assert json.loads(publisher.calls[0]["message"].decode("utf-8")) == {"user_id": 42, "order_id": "o-1"}


@pytest.mark.asyncio
async def test_queue_executor_shadow_mode_does_not_publish() -> None:
    called = {"value": False}

    class _Publisher(_FakePublisher):
        async def publish(self, topic: str, message: bytes, headers: dict[str, str] | None = None) -> None:
            called["value"] = True
            await super().publish(topic, message, headers=headers)

    publisher = _Publisher()
    executor = QueueBindingExecutor(adapter_factory=lambda provider, connection, topic: publisher)
    config = QueueBindingConfig(
        provider="kafka",
        mode="shadow",
        connection="kafka://localhost:9092",
        topic="orders",
    )
    result = await executor.execute(config, {"order_id": "o-1"})
    assert result["status"] == "shadow"
    assert result["sent"] is False
    assert called["value"] is False


def test_queue_executor_validate_config() -> None:
    executor = QueueBindingExecutor()
    errors = executor.validate_config({"provider": "smtp", "connection": "", "topic": ""})
    assert "Queue binding requires 'connection' field" in errors
    assert "Queue binding requires 'topic' field" in errors
    assert "Unsupported queue provider: smtp" in errors
