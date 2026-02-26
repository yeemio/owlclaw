"""Checks for gateway runtime ops rollout policy baseline."""

from __future__ import annotations

from pathlib import Path


def test_gateway_rollout_policy_contains_required_sections() -> None:
    payload = Path("docs/ops/gateway-rollout-policy.md").read_text(encoding="utf-8")
    assert "## 1. Rollout Ratios" in payload
    assert "## 2. Observation Windows" in payload
    assert "## 3. Promotion and Block Conditions" in payload


def test_gateway_runbook_and_slo_baseline_sections_exist() -> None:
    runbook = Path("docs/ops/gateway-runbook.md").read_text(encoding="utf-8")
    assert "## 1. Automatic Rollback Thresholds" in runbook
    assert "## 2. Manual Rollback Triggers" in runbook
    assert "## 3. Post-rollback Verification" in runbook
    assert "## 4. T+0 ~ T+15 Operational Playbook" in runbook

    slo = Path("docs/ops/gateway-slo.md").read_text(encoding="utf-8")
    assert "## 1. SLO Indicators" in slo
    assert "## 2. Error Budget Policy" in slo
    assert "## 4. Acceptance Matrix" in slo
