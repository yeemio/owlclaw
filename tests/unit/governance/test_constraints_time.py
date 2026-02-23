"""Unit tests for TimeConstraint."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from owlclaw.governance.constraints.time import TimeConstraint
from owlclaw.governance.visibility import CapabilityView, RunContext


@pytest.mark.asyncio
async def test_time_no_trading_hours_only_visible():
    """When capability has no trading_hours_only, always visible."""
    c = TimeConstraint({})
    cap = CapabilityView("x", constraints={})
    ctx = RunContext(tenant_id="t1")
    r = await c.evaluate(cap, "agent1", ctx)
    assert r.visible is True


@pytest.mark.asyncio
async def test_time_trading_hours_only_outside_weekdays():
    """When trading_hours_only and current weekday not in weekdays, hidden."""
    c = TimeConstraint(
        {"timezone": "Asia/Shanghai", "trading_hours": {"weekdays": [5, 6]}}
    )
    # Wednesday 2026-02-11
    c._now_cb = lambda: datetime(
        2026, 2, 11, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai")
    )
    cap = CapabilityView("x", constraints={"trading_hours_only": True})
    ctx = RunContext(tenant_id="t1")
    r = await c.evaluate(cap, "agent1", ctx)
    assert r.visible is False
    assert "weekdays" in r.reason.lower() or "trading" in r.reason.lower()


@pytest.mark.asyncio
async def test_time_trading_hours_only_inside_window():
    """When trading_hours_only and inside start-end and weekday, visible."""
    c = TimeConstraint(
        {
            "timezone": "Asia/Shanghai",
            "trading_hours": {
                "start": "09:30",
                "end": "15:00",
                "weekdays": [0, 1, 2, 3, 4],
            },
        }
    )
    # Wednesday 10:00
    c._now_cb = lambda: datetime(
        2026, 2, 11, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai")
    )
    cap = CapabilityView("x", constraints={"trading_hours_only": True})
    ctx = RunContext(tenant_id="t1")
    r = await c.evaluate(cap, "agent1", ctx)
    assert r.visible is True


@pytest.mark.asyncio
async def test_time_trading_hours_only_outside_time():
    """When trading_hours_only and time outside 09:30-15:00, hidden."""
    c = TimeConstraint(
        {
            "timezone": "Asia/Shanghai",
            "trading_hours": {
                "start": "09:30",
                "end": "15:00",
                "weekdays": [0, 1, 2, 3, 4],
            },
        }
    )
    c._now_cb = lambda: datetime(
        2026, 2, 11, 20, 0, tzinfo=ZoneInfo("Asia/Shanghai")
    )
    cap = CapabilityView("x", constraints={"trading_hours_only": True})
    ctx = RunContext(tenant_id="t1")
    r = await c.evaluate(cap, "agent1", ctx)
    assert r.visible is False
    assert "hours" in r.reason.lower() or "trading" in r.reason.lower()


def test_time_constraint_invalid_timezone_falls_back_to_utc():
    c = TimeConstraint({"timezone": "Invalid/Timezone"})
    assert c.timezone == ZoneInfo("UTC")
