"""Unit tests for gateway_ops_gate helpers."""

from __future__ import annotations

from scripts.gateway_ops_gate import GateInput, evaluate_gate, execute_rollback


def test_evaluate_gate_rollback_on_error_rate_threshold() -> None:
    result = evaluate_gate(
        GateInput(
            error_rate=0.03,
            p95_latency_increase=0.10,
            has_critical_alert=False,
            metrics_available=True,
        )
    )
    assert result.decision == "rollback"
    assert result.should_rollback is True


def test_evaluate_gate_promotes_when_slo_green() -> None:
    result = evaluate_gate(
        GateInput(
            error_rate=0.005,
            p95_latency_increase=0.10,
            has_critical_alert=False,
            metrics_available=True,
        )
    )
    assert result.decision == "promote"
    assert result.should_rollback is False


def test_execute_rollback_returns_execution_payload() -> None:
    payload = execute_rollback(target_version="v1.0.0", current_version="v1.1.0")
    assert payload["action"] == "rollback"
    assert payload["status"] == "executed"
