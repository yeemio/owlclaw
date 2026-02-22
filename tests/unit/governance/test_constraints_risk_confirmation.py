"""Unit tests for RiskConfirmationConstraint."""

import pytest

from owlclaw.governance.constraints.risk_confirmation import RiskConfirmationConstraint
from owlclaw.governance.visibility import CapabilityView, RunContext


@pytest.mark.asyncio
async def test_low_risk_without_confirmation_visible():
    c = RiskConfirmationConstraint()
    cap = CapabilityView("read-market", risk_level="low", requires_confirmation=False)
    out = await c.evaluate(cap, "agent1", RunContext(tenant_id="t1"))
    assert out.visible is True


@pytest.mark.asyncio
async def test_high_risk_hidden_without_confirmation():
    c = RiskConfirmationConstraint()
    cap = CapabilityView("place-order", risk_level="high", requires_confirmation=False)
    out = await c.evaluate(cap, "agent1", RunContext(tenant_id="t1"))
    assert out.visible is False
    assert out.reason == "requires_confirmation"


@pytest.mark.asyncio
async def test_high_risk_visible_when_confirmed():
    c = RiskConfirmationConstraint()
    cap = CapabilityView("place-order", risk_level="high", requires_confirmation=False)
    ctx = RunContext(tenant_id="t1", confirmed_capabilities={"place-order"})
    out = await c.evaluate(cap, "agent1", ctx)
    assert out.visible is True


@pytest.mark.asyncio
async def test_explicit_requires_confirmation_takes_effect_for_low_risk():
    c = RiskConfirmationConstraint()
    cap = CapabilityView("write-config", risk_level="low", requires_confirmation=True)
    out = await c.evaluate(cap, "agent1", RunContext(tenant_id="t1"))
    assert out.visible is False


@pytest.mark.asyncio
async def test_high_risk_enforcement_can_be_disabled():
    c = RiskConfirmationConstraint({"enforce_high_risk_confirmation": False})
    cap = CapabilityView("place-order", risk_level="high", requires_confirmation=False)
    out = await c.evaluate(cap, "agent1", RunContext(tenant_id="t1"))
    assert out.visible is True

