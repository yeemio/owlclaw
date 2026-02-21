"""Integration tests for VisibilityFilter with multiple constraints.

Covers: all constraints working together, parallel evaluation behavior,
and exception handling (fail-open).
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest

from owlclaw.governance.constraints.budget import BudgetConstraint
from owlclaw.governance.constraints.time import TimeConstraint
from owlclaw.governance.ledger import CostSummary, Ledger
from owlclaw.governance.visibility import (
    CapabilityView,
    FilterResult,
    RunContext,
    VisibilityFilter,
)


# ---- 2.5.1 All constraints working together ----


@pytest.mark.asyncio
async def test_visibility_filter_all_constraints_combined():
    """Multiple evaluators: only capabilities that pass all constraints are visible."""
    # TimeConstraint: only allow if trading_hours_only and inside window (we control via _now_cb)
    time_c = TimeConstraint(
        {
            "timezone": "Asia/Shanghai",
            "trading_hours": {
                "start": "09:30",
                "end": "15:00",
                "weekdays": [0, 1, 2, 3, 4],
            },
        }
    )
    # Wednesday 10:00 -> inside window
    time_c._now_cb = lambda: datetime(
        2026, 2, 11, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai")
    )

    # BudgetConstraint: mock ledger so agent1 has budget exhausted, agent2 has remaining
    ledger = AsyncMock(spec=Ledger)
    ledger.get_cost_summary = AsyncMock(
        return_value=CostSummary(total_cost=Decimal("100"))
    )
    budget_c = BudgetConstraint(
        ledger,
        {"budget_limits": {"agent1": "100"}, "high_cost_threshold": "0.5"},
    )

    # Cap A: no time constraint, low cost -> visible
    # Cap B: trading_hours_only (passes time), high cost + budget exhausted -> hidden
    # Cap C: no budget limit for agent (e.g. different agent) -> we use agent1 so B is hidden
    vf = VisibilityFilter()
    vf.register_evaluator(time_c)
    vf.register_evaluator(budget_c)

    caps = [
        CapabilityView("A", constraints={}),  # no trading_hours_only, no high cost
        CapabilityView(
            "B",
            constraints={"trading_hours_only": True, "estimated_cost": "1.0"},
        ),
        CapabilityView("C", constraints={"estimated_cost": "0.01"}),  # low cost
    ]
    ctx = RunContext(tenant_id="t1")
    out = await vf.filter_capabilities(caps, "agent1", ctx)
    names = [c.name for c in out]
    assert "A" in names
    assert "C" in names
    assert "B" not in names


# ---- 2.5.2 Parallel evaluation (all evaluators must pass) ----


@pytest.mark.asyncio
async def test_visibility_filter_evaluators_both_must_pass():
    """Two evaluators: capability is visible only when both return visible=True."""

    class First:
        async def evaluate(self, capability, agent_id, context):
            return FilterResult(visible=capability.name != "hide-first")

    class Second:
        async def evaluate(self, capability, agent_id, context):
            return FilterResult(visible=capability.name != "hide-second")

    vf = VisibilityFilter()
    vf.register_evaluator(First())
    vf.register_evaluator(Second())

    caps = [
        CapabilityView("pass-both"),
        CapabilityView("hide-first"),
        CapabilityView("hide-second"),
    ]
    ctx = RunContext(tenant_id="t1")
    out = await vf.filter_capabilities(caps, "agent1", ctx)
    assert len(out) == 1
    assert out[0].name == "pass-both"


# ---- 2.5.3 Exception handling (fail-open) ----


@pytest.mark.asyncio
async def test_visibility_filter_fail_open_with_real_constraint():
    """When a real constraint (e.g. BudgetConstraint) raises, capability remains visible."""
    ledger = AsyncMock(spec=Ledger)
    ledger.get_cost_summary = AsyncMock(side_effect=RuntimeError("DB unavailable"))

    budget_c = BudgetConstraint(
        ledger,
        {"budget_limits": {"agent1": "100"}, "high_cost_threshold": "0.1"},
    )
    vf = VisibilityFilter()
    vf.register_evaluator(budget_c)

    cap = CapabilityView("expensive", constraints={"estimated_cost": "0.5"})
    ctx = RunContext(tenant_id="t1")
    out = await vf.filter_capabilities([cap], "agent1", ctx)
    assert len(out) == 1
    assert out[0].name == "expensive"
