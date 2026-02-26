"""Unit tests for migration risk assessor."""

from __future__ import annotations

from owlclaw.governance.risk_assessor import RiskAssessor


def test_infer_operation_type_from_http_method() -> None:
    assessor = RiskAssessor()
    assert assessor.infer_operation_type({"binding": {"method": "GET"}}) == "read"
    assert assessor.infer_operation_type({"binding": {"method": "POST"}}) == "write"
    assert assessor.infer_operation_type({"binding": {"method": "DELETE"}}) == "delete"


def test_assess_returns_bounded_risk_score() -> None:
    assessor = RiskAssessor()
    breakdown = assessor.assess(
        {
            "binding": {"method": "POST"},
            "impact_scope": "batch",
            "amount": 3000,
            "reversibility": "partially_reversible",
        }
    )
    assert 0.0 <= breakdown.total <= 1.0
    assert breakdown.operation_type > 0.0
    assert breakdown.impact_scope == 0.5
    assert breakdown.amount == 0.5


def test_skill_risk_override_parsing_and_application() -> None:
    assessor = RiskAssessor()
    skill_owlclaw = {
        "risk": {
            "operation_type": "payment",
            "impact_scope": "global",
            "reversibility": "irreversible",
            "amount": 12000,
        }
    }
    breakdown = assessor.assess({"binding": {"method": "GET"}}, skill_owlclaw=skill_owlclaw)
    assert breakdown.operation_type == 1.0
    assert breakdown.impact_scope == 1.0
    assert breakdown.reversibility == 1.0
    assert breakdown.amount == 1.0
    assert breakdown.total == 1.0
