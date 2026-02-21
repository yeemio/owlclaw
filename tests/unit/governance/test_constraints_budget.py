"""Unit tests for BudgetConstraint."""

from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from owlclaw.governance.constraints.budget import BudgetConstraint
from owlclaw.governance.ledger import CostSummary, Ledger
from owlclaw.governance.visibility import CapabilityView, RunContext


@pytest.mark.asyncio
async def test_budget_no_limit_always_visible():
    """When no budget_limits, capability is always visible."""
    ledger = AsyncMock(spec=Ledger)
    c = BudgetConstraint(ledger, {})
    cap = CapabilityView("x", constraints={"estimated_cost": "0.2"})
    ctx = RunContext(tenant_id="t1")
    r = await c.evaluate(cap, "agent1", ctx)
    assert r.visible is True
    ledger.get_cost_summary.assert_not_called()


@pytest.mark.asyncio
async def test_budget_remaining_positive_visible():
    """When remaining budget > 0, capability is visible."""
    ledger = AsyncMock(spec=Ledger)
    ledger.get_cost_summary = AsyncMock(
        return_value=CostSummary(total_cost=Decimal("10"))
    )
    c = BudgetConstraint(
        ledger,
        {"budget_limits": {"agent1": "100"}, "high_cost_threshold": "0.1"},
    )
    cap = CapabilityView("x", constraints={})
    ctx = RunContext(tenant_id="t1")
    r = await c.evaluate(cap, "agent1", ctx)
    assert r.visible is True


@pytest.mark.asyncio
async def test_budget_exhausted_high_cost_hidden():
    """When budget exhausted and capability is high-cost, hidden."""
    ledger = AsyncMock(spec=Ledger)
    ledger.get_cost_summary = AsyncMock(
        return_value=CostSummary(total_cost=Decimal("100"))
    )
    c = BudgetConstraint(
        ledger,
        {"budget_limits": {"agent1": "100"}, "high_cost_threshold": "0.1"},
    )
    cap = CapabilityView("x", constraints={"estimated_cost": "0.5"})
    ctx = RunContext(tenant_id="t1")
    r = await c.evaluate(cap, "agent1", ctx)
    assert r.visible is False
    assert "Budget exhausted" in r.reason


@pytest.mark.asyncio
async def test_budget_exhausted_low_cost_visible():
    """When budget exhausted but capability is low-cost, still visible."""
    ledger = AsyncMock(spec=Ledger)
    ledger.get_cost_summary = AsyncMock(
        return_value=CostSummary(total_cost=Decimal("100"))
    )
    c = BudgetConstraint(
        ledger,
        {"budget_limits": {"agent1": "100"}, "high_cost_threshold": "0.5"},
    )
    cap = CapabilityView("x", constraints={"estimated_cost": "0.05"})
    ctx = RunContext(tenant_id="t1")
    r = await c.evaluate(cap, "agent1", ctx)
    assert r.visible is True
