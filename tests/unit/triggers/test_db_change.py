from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any

import pytest

from owlclaw.triggers.db_change import (
    DBChangeEvent,
    DBChangeTriggerConfig,
    DBChangeTriggerManager,
    EventAggregator,
    PostgresNotifyAdapter,
)


@pytest.mark.asyncio
async def test_event_aggregator_modes() -> None:
    flushed: list[list[DBChangeEvent]] = []

    async def _on_flush(events: list[DBChangeEvent]) -> None:
        flushed.append(events)

    event = DBChangeEvent(channel="ch", payload={"x": 1}, timestamp=__import__("datetime").datetime.now(__import__("datetime").timezone.utc))

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

    async def trigger_event(self, event_name: str, payload: dict[str, Any], focus: str | None = None, tenant_id: str = "default") -> None:  # noqa: ARG002
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
    await adapter.callback(DBChangeEvent(channel="orders", payload={"id": 1}, timestamp=__import__("datetime").datetime.now(__import__("datetime").timezone.utc)))
    await asyncio.sleep(0)
    assert runtime.calls == 0
    assert ledger.records == 1

    await manager.stop()
    assert not adapter.started
