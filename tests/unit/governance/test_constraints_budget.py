"""Unit tests for BudgetConstraint."""

import asyncio
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


@pytest.mark.asyncio
async def test_budget_invalid_budget_limit_does_not_crash():
    ledger = AsyncMock(spec=Ledger)
    ledger.get_cost_summary = AsyncMock(
        return_value=CostSummary(total_cost=Decimal("1"))
    )
    c = BudgetConstraint(
        ledger,
        {"budget_limits": {"agent1": "bad-limit"}, "high_cost_threshold": "0.1"},
    )
    cap = CapabilityView("x", constraints={"estimated_cost": "0.2"})
    ctx = RunContext(tenant_id="t1")
    r = await c.evaluate(cap, "agent1", ctx)
    assert r.visible is False


@pytest.mark.asyncio
async def test_budget_invalid_estimated_cost_uses_default():
    ledger = AsyncMock(spec=Ledger)
    ledger.get_cost_summary = AsyncMock(
        return_value=CostSummary(total_cost=Decimal("100"))
    )
    c = BudgetConstraint(
        ledger,
        {"budget_limits": {"agent1": "100"}, "high_cost_threshold": "bad-threshold"},
    )
    cap = CapabilityView("x", constraints={"estimated_cost": "not-a-number"})
    ctx = RunContext(tenant_id="t1")
    r = await c.evaluate(cap, "agent1", ctx)
    assert r.visible is True


@pytest.mark.asyncio
async def test_budget_constraint_atomic_reservation_blocks_second_concurrent_high_cost_request() -> None:
    ledger = AsyncMock(spec=Ledger)
    ledger.get_cost_summary = AsyncMock(return_value=CostSummary(total_cost=Decimal("0.00")))
    constraint = BudgetConstraint(
        ledger,
        {"budget_limits": {"agent1": "0.15"}, "high_cost_threshold": "0.01"},
    )
    cap = CapabilityView("x", constraints={"estimated_cost": "0.10"})
    ctx = RunContext(tenant_id="t1")

    first, second = await asyncio.gather(
        constraint.evaluate(cap, "agent1", ctx),
        constraint.evaluate(cap, "agent1", ctx),
    )
    visible_count = int(first.visible) + int(second.visible)
    assert visible_count == 1


@pytest.mark.asyncio
async def test_budget_constraint_refund_reservation_restores_capacity() -> None:
    ledger = AsyncMock(spec=Ledger)
    ledger.get_cost_summary = AsyncMock(return_value=CostSummary(total_cost=Decimal("0.00")))
    constraint = BudgetConstraint(
        ledger,
        {"budget_limits": {"agent1": "0.10"}, "high_cost_threshold": "0.01"},
    )
    cap = CapabilityView("x", constraints={"estimated_cost": "0.10"})
    ctx = RunContext(tenant_id="t1")

    first = await constraint.evaluate(cap, "agent1", ctx)
    second = await constraint.evaluate(cap, "agent1", ctx)
    assert first.visible is True
    assert second.visible is False

    await constraint.refund_reservation("t1", "agent1", Decimal("0.10"))
    third = await constraint.evaluate(cap, "agent1", ctx)
    assert third.visible is True
