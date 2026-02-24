"""Property tests for HatchetRuntimeBridge (agent-runtime task 9)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.agent.runtime.hatchet_bridge import HatchetRuntimeBridge


class _HatchetStub:
    def __init__(self) -> None:
        self.task_kwargs: dict[str, object] | None = None
        self.run_task_now = AsyncMock(return_value="run-x")
        self.schedule_task = AsyncMock(return_value="schedule-x")
        self.schedule_cron = AsyncMock(return_value="cron-x")

    def task(self, **kwargs):  # type: ignore[no-untyped-def]
        self.task_kwargs = dict(kwargs)

        def _decorator(func):  # type: ignore[no-untyped-def]
            return func

        return _decorator


class _RuntimeStub:
    def __init__(self) -> None:
        self.trigger_event = AsyncMock(return_value={"status": "completed", "run_id": "r"})


@given(retries=st.integers(min_value=0, max_value=10))
@settings(deadline=None)
def test_property_hatchet_retry_forwarding(retries: int) -> None:
    """Property 17: Hatchet retries are configurable and forwarded to task registration."""
    hatchet = _HatchetStub()
    bridge = HatchetRuntimeBridge(_RuntimeStub(), hatchet, retries=retries)
    bridge.register_task()
    assert hatchet.task_kwargs is not None
    assert hatchet.task_kwargs["retries"] == retries


@pytest.mark.asyncio
@given(
    event_name=st.text(min_size=1, max_size=20).filter(lambda s: s.strip() != ""),
    tenant_id=st.text(min_size=1, max_size=20).filter(lambda s: s.strip() != ""),
)
@settings(deadline=None)
async def test_property_hatchet_payload_parsing(event_name: str, tenant_id: str) -> None:
    """Property: valid Hatchet payload fields are forwarded to runtime.trigger_event."""
    runtime = _RuntimeStub()
    bridge = HatchetRuntimeBridge(runtime, _HatchetStub())
    payload = {
        "event_name": event_name.strip(),
        "tenant_id": tenant_id.strip(),
        "payload": {"k": "v"},
    }
    await bridge.run_payload(payload)
    runtime.trigger_event.assert_awaited_once_with(
        event_name.strip(),
        focus=None,
        payload={"k": "v"},
        tenant_id=tenant_id.strip(),
    )
