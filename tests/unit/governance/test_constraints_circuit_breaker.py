"""Unit tests for CircuitBreakerConstraint."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from owlclaw.governance.constraints.circuit_breaker import (
    CircuitBreakerConstraint,
    CircuitState,
)
from owlclaw.governance.ledger import Ledger, LedgerRecord
from owlclaw.governance.visibility import CapabilityView, RunContext


def _record(status: str) -> LedgerRecord:
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
        status=status,
        error_message=None,
    )
    rec.created_at = datetime.now(timezone.utc)
    return rec


@pytest.mark.asyncio
async def test_circuit_no_failures_visible():
    """When no recent failures, capability visible."""
    ledger = AsyncMock(spec=Ledger)
    ledger.query_records = AsyncMock(return_value=[])
    c = CircuitBreakerConstraint(ledger, {"failure_threshold": 3})
    cap = CapabilityView("x", constraints={})
    ctx = RunContext(tenant_id="t1")
    r = await c.evaluate(cap, "agent1", ctx)
    assert r.visible is True


@pytest.mark.asyncio
async def test_circuit_failures_below_threshold_visible():
    """When failures below threshold, visible."""
    ledger = AsyncMock(spec=Ledger)
    ledger.query_records = AsyncMock(
        return_value=[_record("failure"), _record("failure")]
    )
    c = CircuitBreakerConstraint(ledger, {"failure_threshold": 3})
    cap = CapabilityView("x", constraints={})
    ctx = RunContext(tenant_id="t1")
    r = await c.evaluate(cap, "agent1", ctx)
    assert r.visible is True


@pytest.mark.asyncio
async def test_circuit_failures_at_threshold_opens():
    """When consecutive failures >= threshold, hidden."""
    ledger = AsyncMock(spec=Ledger)
    ledger.query_records = AsyncMock(
        return_value=[
            _record("failure"),
            _record("failure"),
            _record("failure"),
        ]
    )
    c = CircuitBreakerConstraint(ledger, {"failure_threshold": 3})
    cap = CapabilityView("x", constraints={})
    ctx = RunContext(tenant_id="t1")
    r = await c.evaluate(cap, "agent1", ctx)
    assert r.visible is False
    assert "Circuit" in r.reason or "failure" in r.reason


@pytest.mark.asyncio
async def test_circuit_on_success_resets():
    """on_capability_success resets circuit to CLOSED."""
    ledger = AsyncMock(spec=Ledger)
    c = CircuitBreakerConstraint(ledger, {"failure_threshold": 2})
    cap = CapabilityView("x", constraints={})
    ctx = RunContext(tenant_id="t1")
    ledger.query_records = AsyncMock(
        return_value=[_record("failure"), _record("failure")]
    )
    r1 = await c.evaluate(cap, "agent1", ctx)
    assert r1.visible is False
    await c.on_capability_success("agent1", "x")
    ledger.query_records = AsyncMock(return_value=[])
    r2 = await c.evaluate(cap, "agent1", ctx)
    assert r2.visible is True
