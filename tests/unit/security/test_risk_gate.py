"""Unit tests for RiskGate."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from owlclaw.security.risk_gate import RiskDecision, RiskGate
from owlclaw.security.audit import SecurityAuditLog


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


@pytest.mark.parametrize(
    ("risk_level", "budget_ratio", "requires_confirmation", "expected"),
    [
        ("low", 0.0, False, RiskDecision.EXECUTE),
        ("medium", 0.2, False, RiskDecision.EXECUTE),
        ("high", 0.5, False, RiskDecision.EXECUTE),
        ("high", 0.8, False, RiskDecision.PAUSE),
        ("critical", 0.0, False, RiskDecision.PAUSE),
        ("low", 0.0, True, RiskDecision.PAUSE),
        ("unknown", 0.0, False, RiskDecision.REJECT),
    ],
)
def test_risk_gate_decision_matrix(
    risk_level: str,
    budget_ratio: float,
    requires_confirmation: bool,
    expected: RiskDecision,
) -> None:
    gate = RiskGate()
    decision, _ = gate.evaluate(
        "trade.execute",
        risk_level=risk_level,
        budget_ratio=budget_ratio,
        requires_confirmation=requires_confirmation,
    )
    assert decision == expected


def test_risk_gate_confirm_and_reject() -> None:
    gate = RiskGate()
    _, op = gate.evaluate("trade.execute", risk_level="critical")
    assert op is not None
    assert gate.confirm(op) is True
    assert gate.confirm(op) is False

    _, op2 = gate.evaluate("trade.execute", risk_level="critical")
    assert op2 is not None
    assert gate.reject(op2) is True
    assert gate.reject(op2) is False


def test_risk_gate_timeout_expiration() -> None:
    gate = RiskGate(confirmation_timeout_seconds=1)
    _, op = gate.evaluate("trade.execute", risk_level="critical")
    assert op is not None
    gate._pending[op].created_at = datetime.now(timezone.utc) - timedelta(seconds=5)  # type: ignore[misc]
    assert gate.pending_count() == 0
    assert gate.confirm(op) is False
    assert gate.reject(op) is False


def test_risk_gate_writes_audit_events() -> None:
    audit = SecurityAuditLog()
    gate = RiskGate(audit_log=audit)
    decision, op = gate.evaluate("trade.execute", risk_level="critical")
    assert decision == RiskDecision.PAUSE
    assert op is not None
    assert gate.confirm(op) is True
    event_types = [e.event_type for e in audit.list_events()]
    assert "risk_paused" in event_types
    assert "risk_confirmed" in event_types
