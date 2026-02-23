"""Unit tests for HatchetRuntimeBridge (agent-runtime task 9)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from owlclaw.agent.runtime.hatchet_bridge import HatchetRuntimeBridge


class _HatchetStub:
    def __init__(self) -> None:
        self.task_calls: list[dict[str, object]] = []
        self.run_task_now = AsyncMock(return_value="run-1")
        self.schedule_task = AsyncMock(return_value="scheduled-1")
        self.schedule_cron = AsyncMock(return_value="cron-1")
        self.send_signal = AsyncMock(return_value={"ok": True})

    def task(self, **kwargs):  # type: ignore[no-untyped-def]
        self.task_calls.append(dict(kwargs))

        def _decorator(func):  # type: ignore[no-untyped-def]
            self._handler = func
            return func

        return _decorator


@pytest.fixture
def runtime_mock():
    class _Runtime:
        def __init__(self) -> None:
            self.trigger_event = AsyncMock(
                return_value={"status": "completed", "run_id": "r-1"}
            )

    return _Runtime()


def test_register_task_forwards_retries(runtime_mock) -> None:
    hatchet = _HatchetStub()
    bridge = HatchetRuntimeBridge(runtime_mock, hatchet, task_name="agent-run", retries=5)
    bridge.register_task()
    assert hatchet.task_calls[0]["name"] == "agent-run"
    assert hatchet.task_calls[0]["retries"] == 5


@pytest.mark.asyncio
async def test_registered_handler_parses_payload(runtime_mock) -> None:
    hatchet = _HatchetStub()
    bridge = HatchetRuntimeBridge(runtime_mock, hatchet)
    handler = bridge.register_task()
    result = await handler(
        {
            "event_name": "cron_tick",
            "focus": "inventory_monitor",
            "payload": {"x": 1},
            "tenant_id": "tenant-a",
        }
    )
    assert result["status"] == "completed"
    runtime_mock.trigger_event.assert_awaited_once_with(
        "cron_tick",
        focus="inventory_monitor",
        payload={"x": 1},
        tenant_id="tenant-a",
    )


@pytest.mark.asyncio
async def test_run_payload_defaults(runtime_mock) -> None:
    hatchet = _HatchetStub()
    bridge = HatchetRuntimeBridge(runtime_mock, hatchet)
    await bridge.run_payload(None)
    runtime_mock.trigger_event.assert_awaited_once_with(
        "hatchet_task",
        focus=None,
        payload={},
        tenant_id="default",
    )


@pytest.mark.asyncio
async def test_schedule_and_run_now_proxy(runtime_mock) -> None:
    hatchet = _HatchetStub()
    bridge = HatchetRuntimeBridge(runtime_mock, hatchet, task_name="agent-run")
    run_id = await bridge.run_now(tenant_id="default")
    schedule_id = await bridge.schedule_task(30, tenant_id="default")
    cron_id = await bridge.schedule_cron("cron-a", "*/5 * * * *", {"tenant_id": "default"})
    assert run_id == "run-1"
    assert schedule_id == "scheduled-1"
    assert cron_id == "cron-1"
    hatchet.run_task_now.assert_awaited_once_with("agent-run", tenant_id="default")
    hatchet.schedule_task.assert_awaited_once_with("agent-run", 30, tenant_id="default")


@pytest.mark.asyncio
async def test_send_signal_proxy(runtime_mock) -> None:
    hatchet = _HatchetStub()
    bridge = HatchetRuntimeBridge(runtime_mock, hatchet)
    result = await bridge.send_signal("run-1", "pause", {"reason": "manual"})
    assert result == {"ok": True}
    hatchet.send_signal.assert_awaited_once_with(
        run_id="run-1", signal_name="pause", payload={"reason": "manual"}
    )


@pytest.mark.asyncio
async def test_concurrency_limit_serializes_execution(runtime_mock) -> None:
    order: list[str] = []

    async def _slow_trigger(event_name: str, **_: object) -> dict[str, str]:
        order.append(f"start:{event_name}")
        await asyncio.sleep(0.01)
        order.append(f"end:{event_name}")
        return {"status": "completed", "run_id": event_name}

    runtime_mock.trigger_event = AsyncMock(side_effect=_slow_trigger)
    bridge = HatchetRuntimeBridge(runtime_mock, _HatchetStub(), max_concurrency=1)
    await asyncio.gather(
        bridge.run_payload({"event_name": "a"}),
        bridge.run_payload({"event_name": "b"}),
    )
    assert order[0] == "start:a"
    assert order[1] == "end:a"
