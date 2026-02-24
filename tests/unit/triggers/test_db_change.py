from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import pytest

from owlclaw.app import OwlClaw
from owlclaw.triggers.db_change import (
    DBChangeEvent,
    DBChangeTriggerConfig,
    DBChangeTriggerManager,
    DBChangeTriggerRegistration,
    DebeziumConfig,
    EventAggregator,
    PostgresNotifyAdapter,
    db_change,
)


@pytest.mark.asyncio
async def test_event_aggregator_modes() -> None:
    flushed: list[list[DBChangeEvent]] = []

    async def _on_flush(events: list[DBChangeEvent]) -> None:
        flushed.append(events)

    event = DBChangeEvent(channel="ch", payload={"x": 1}, timestamp=datetime.now(timezone.utc))

    passthrough = EventAggregator(mode="passthrough", on_flush=_on_flush)
    await passthrough.push(event)
    assert len(flushed) == 1

    flushed.clear()
    batch = EventAggregator(mode="batch", on_flush=_on_flush, batch_size=2)
    await batch.push(event)
    await batch.push(event)
    assert len(flushed) == 1
    assert len(flushed[0]) == 2

    flushed.clear()
    debounce = EventAggregator(mode="debounce", on_flush=_on_flush, debounce_seconds=0.01)
    await debounce.push(event)
    await asyncio.sleep(0.02)
    assert len(flushed) == 1

    flushed.clear()
    hybrid = EventAggregator(mode="hybrid", on_flush=_on_flush, debounce_seconds=0.05, batch_size=2)
    await hybrid.push(event)
    await hybrid.push(event)
    assert len(flushed) == 1


@pytest.mark.asyncio
async def test_postgres_notify_adapter_payload_parsing() -> None:
    adapter = PostgresNotifyAdapter(dsn="postgresql://invalid")
    received: list[DBChangeEvent] = []

    async def _cb(event: DBChangeEvent) -> None:
        received.append(event)

    adapter.on_event(_cb)
    await adapter._on_notify(None, 1, "orders", json.dumps({"id": 1}))
    await adapter._on_notify(None, 1, "orders", "")
    await adapter._on_notify(None, 1, "orders", "{bad-json")
    await asyncio.sleep(0)

    assert received[0].payload == {"id": 1}
    assert received[1].payload == {}
    assert received[2].payload.get("parse_error") is True


@dataclass
class _Adapter:
    callback: Any = None
    channels: list[str] = field(default_factory=list)
    started: bool = False

    def on_event(self, callback: Any) -> None:
        self.callback = callback

    async def start(self, channels: list[str]) -> None:
        self.channels = channels
        self.started = True

    async def stop(self) -> None:
        self.started = False


@dataclass
class _Governance:
    allowed: bool

    async def allow_trigger(self, event_name: str, tenant_id: str) -> bool:  # noqa: ARG002
        return self.allowed


@dataclass
class _Runtime:
    calls: int = 0
    fail_until: int = 0

    async def trigger_event(self, event_name: str, payload: dict[str, Any], focus: str | None = None, tenant_id: str = "default") -> None:  # noqa: ARG002
        if self.calls < self.fail_until:
            self.calls += 1
            raise RuntimeError("runtime unavailable")
        self.calls += 1


@dataclass
class _Ledger:
    records: int = 0

    async def record_execution(self, **kwargs: Any) -> None:  # noqa: ANN401
        self.records += 1


@pytest.mark.asyncio
async def test_db_change_trigger_manager_register_trigger_governance_block() -> None:
    adapter = _Adapter()
    runtime = _Runtime()
    ledger = _Ledger()
    manager = DBChangeTriggerManager(
        adapter=adapter,
        governance=_Governance(allowed=False),
        agent_runtime=runtime,
        ledger=ledger,
    )
    config = DBChangeTriggerConfig(channel="orders", event_name="order_changed", agent_id="agent-1")
    manager.register(config)
    await manager.start()
    assert adapter.started
    assert adapter.channels == ["orders"]

    assert adapter.callback is not None
    await adapter.callback(DBChangeEvent(channel="orders", payload={"id": 1}, timestamp=datetime.now(timezone.utc)))
    await asyncio.sleep(0)
    assert runtime.calls == 0
    assert ledger.records == 1

    await manager.stop()
    assert not adapter.started


@pytest.mark.asyncio
async def test_event_aggregator_memory_bound_drops_oldest() -> None:
    flushed: list[list[DBChangeEvent]] = []

    async def _on_flush(events: list[DBChangeEvent]) -> None:
        flushed.append(events)

    aggregator = EventAggregator(mode="batch", batch_size=10, max_buffer_events=2, on_flush=_on_flush)
    await aggregator.push(DBChangeEvent(channel="a", payload={"id": 1}, timestamp=datetime.now(timezone.utc)))
    await aggregator.push(DBChangeEvent(channel="a", payload={"id": 2}, timestamp=datetime.now(timezone.utc)))
    await aggregator.push(DBChangeEvent(channel="a", payload={"id": 3}, timestamp=datetime.now(timezone.utc)))
    await aggregator.flush()
    assert aggregator.dropped_events == 1
    assert [e.payload["id"] for e in flushed[0]] == [2, 3]


@pytest.mark.asyncio
async def test_manager_drops_oversized_payload() -> None:
    adapter = _Adapter()
    runtime = _Runtime()
    manager = DBChangeTriggerManager(
        adapter=adapter,
        governance=_Governance(allowed=True),
        agent_runtime=runtime,
    )
    manager.register(DBChangeTriggerConfig(channel="orders", event_name="order_changed", agent_id="agent-1", max_payload_bytes=128))
    await manager.start()
    assert adapter.callback is not None
    await adapter.callback(DBChangeEvent(channel="orders", payload={"body": "x" * 500}, timestamp=datetime.now(timezone.utc)))
    await asyncio.sleep(0)
    assert runtime.calls == 0
    await manager.stop()


@pytest.mark.asyncio
async def test_manager_local_retry_queue_when_runtime_unavailable() -> None:
    adapter = _Adapter()
    runtime = _Runtime(fail_until=1)
    manager = DBChangeTriggerManager(
        adapter=adapter,
        governance=_Governance(allowed=True),
        agent_runtime=runtime,
        retry_interval_seconds=0.01,
        local_queue_max_size=4,
    )
    manager.register(DBChangeTriggerConfig(channel="orders", event_name="order_changed", agent_id="agent-1", batch_size=1))
    await manager.start()
    assert adapter.callback is not None
    await adapter.callback(DBChangeEvent(channel="orders", payload={"id": 1}, timestamp=datetime.now(timezone.utc)))
    await asyncio.sleep(0.05)
    assert runtime.calls >= 2
    await manager.stop()


def test_db_change_function_api_registration_payload() -> None:
    registration = db_change(channel="orders", event_name="order_changed", agent_id="agent-1")
    assert isinstance(registration, DBChangeTriggerRegistration)
    assert registration.config.channel == "orders"
    assert registration.config.event_name == "order_changed"


def test_app_db_change_decorator_and_trigger_function_style(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OWLCLAW_DATABASE_URL", "postgresql://user:pwd@localhost:5432/owlclaw")
    app = OwlClaw("agent-a")
    app.configure(triggers={"db_change": {"reconnect_interval": 5}})

    @app.db_change(channel="orders", event_name="order_changed")
    async def _fallback(events: list[DBChangeEvent]) -> None:  # noqa: ARG001
        return None

    app.trigger(db_change(channel="positions", event_name="position_changed", agent_id=app.name))
    assert app.db_change_manager is not None
    assert "orders" in app.db_change_manager._states  # noqa: SLF001
    assert "positions" in app.db_change_manager._states  # noqa: SLF001


def test_debezium_config_validation() -> None:
    cfg = DebeziumConfig(
        enabled=True,
        source_url="kafka://localhost:9092",
        connector_name="orders-cdc",
        topic_prefix="dbserver1",
    )
    assert cfg.enabled is True
