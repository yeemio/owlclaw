"""Unit tests for RateLimitConstraint."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from owlclaw.governance.constraints.rate_limit import RateLimitConstraint
from owlclaw.governance.ledger import Ledger, LedgerRecord
from owlclaw.governance.visibility import CapabilityView, RunContext


@pytest.mark.asyncio
async def test_rate_limit_no_constraints_visible():
    """When capability has no max_daily_calls or cooldown, visible."""
    ledger = AsyncMock(spec=Ledger)
    c = RateLimitConstraint(ledger)
    cap = CapabilityView("x", constraints={})
    ctx = RunContext(tenant_id="t1")
    r = await c.evaluate(cap, "agent1", ctx)
    assert r.visible is True


@pytest.mark.asyncio
async def test_rate_limit_under_daily_limit_visible():
    """When daily calls under limit, visible."""
    ledger = AsyncMock(spec=Ledger)
    ledger.query_records = AsyncMock(return_value=[])  # 0 calls today
    c = RateLimitConstraint(ledger)
    cap = CapabilityView("x", constraints={"max_daily_calls": 10})
    ctx = RunContext(tenant_id="t1")
    r = await c.evaluate(cap, "agent1", ctx)
    assert r.visible is True


@pytest.mark.asyncio
async def test_rate_limit_over_daily_limit_hidden():
    """When daily calls >= max_daily_calls, hidden."""
    ledger = AsyncMock(spec=Ledger)
    ledger.query_records = AsyncMock(return_value=[1, 2, 3, 4, 5])  # 5 records
    c = RateLimitConstraint(ledger)
    cap = CapabilityView("x", constraints={"max_daily_calls": 5})
    ctx = RunContext(tenant_id="t1")
    r = await c.evaluate(cap, "agent1", ctx)
    assert r.visible is False
    assert "limit" in r.reason.lower() or "5" in r.reason


@pytest.mark.asyncio
async def test_rate_limit_cooldown_elapsed_visible():
    """When cooldown_seconds set but no recent call, visible."""
    ledger = AsyncMock(spec=Ledger)
    ledger.query_records = AsyncMock(return_value=[])
    c = RateLimitConstraint(ledger)
    cap = CapabilityView("x", constraints={"cooldown_seconds": 60})
    ctx = RunContext(tenant_id="t1")
    r = await c.evaluate(cap, "agent1", ctx)
    assert r.visible is True


@pytest.mark.asyncio
async def test_rate_limit_cooldown_active_hidden():
    """When last call was recent (within cooldown), hidden."""
    ledger = AsyncMock(spec=Ledger)
    rec = LedgerRecord(
        tenant_id="t1",
        agent_id="agent1",
        run_id="r1",
        capability_name="x",
        task_type="t1",
        input_params={},
        output_result=None,
        decision_reasoning=None,
        execution_time_ms=0,
        llm_model="gpt-4",
        llm_tokens_input=0,
        llm_tokens_output=0,
        estimated_cost=__import__("decimal").Decimal("0"),
        status="success",
        error_message=None,
    )
    rec.created_at = datetime.now(timezone.utc)
    ledger.query_records = AsyncMock(return_value=[rec])
    c = RateLimitConstraint(ledger)
    cap = CapabilityView("x", constraints={"cooldown_seconds": 300})
    ctx = RunContext(tenant_id="t1")
    r = await c.evaluate(cap, "agent1", ctx)
    assert r.visible is False
    assert "Cooldown" in r.reason or "remaining" in r.reason


@pytest.mark.asyncio
async def test_rate_limit_parses_numeric_string_constraints():
    ledger = AsyncMock(spec=Ledger)
    ledger.query_records = AsyncMock(return_value=[1, 2, 3, 4, 5])
    c = RateLimitConstraint(ledger)
    cap = CapabilityView("x", constraints={"max_daily_calls": "5"})
    ctx = RunContext(tenant_id="t1")
    r = await c.evaluate(cap, "agent1", ctx)
    assert r.visible is False


@pytest.mark.asyncio
async def test_rate_limit_ignores_invalid_constraint_values():
    ledger = AsyncMock(spec=Ledger)
    ledger.query_records = AsyncMock(return_value=[1, 2, 3, 4, 5])
    c = RateLimitConstraint(ledger)
    cap = CapabilityView("x", constraints={"max_daily_calls": "bad", "cooldown_seconds": -1})
    ctx = RunContext(tenant_id="t1")
    r = await c.evaluate(cap, "agent1", ctx)
    assert r.visible is True
