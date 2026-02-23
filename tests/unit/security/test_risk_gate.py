"""Unit tests for RiskGate."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from owlclaw.security.risk_gate import RiskDecision, RiskGate


def test_risk_gate_execute_low_risk() -> None:
    gate = RiskGate()
    decision, operation_id = gate.evaluate("tool.x", risk_level="low")
    assert decision == RiskDecision.EXECUTE
    assert operation_id is None


def test_risk_gate_pause_for_critical_or_high_budget() -> None:
    gate = RiskGate()
    decision1, op1 = gate.evaluate("trade.execute", risk_level="critical")
    assert decision1 == RiskDecision.PAUSE
    assert op1 is not None

    decision2, op2 = gate.evaluate("trade.execute", risk_level="high", budget_ratio=0.9)
    assert decision2 == RiskDecision.PAUSE
    assert op2 is not None


def test_risk_gate_confirm_and_reject() -> None:
    gate = RiskGate()
    _, op = gate.evaluate("trade.execute", risk_level="critical")
    assert op is not None
    assert gate.confirm(op) is True
    assert gate.confirm(op) is False

    _, op2 = gate.evaluate("trade.execute", risk_level="critical")
    assert op2 is not None
    assert gate.reject(op2) is True


def test_risk_gate_timeout_expiration() -> None:
    gate = RiskGate(confirmation_timeout_seconds=1)
    _, op = gate.evaluate("trade.execute", risk_level="critical")
    assert op is not None
    gate._pending[op].created_at = datetime.now(timezone.utc) - timedelta(seconds=5)  # type: ignore[misc]
    assert gate.pending_count() == 0
