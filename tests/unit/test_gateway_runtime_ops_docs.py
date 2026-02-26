"""Checks for gateway runtime ops rollout policy baseline."""

from __future__ import annotations

from pathlib import Path


def test_gateway_rollout_policy_contains_required_sections() -> None:
    payload = Path("docs/ops/gateway-rollout-policy.md").read_text(encoding="utf-8")
    assert "## 1. Rollout Ratios" in payload
    assert "## 2. Observation Windows" in payload
    assert "## 3. Promotion and Block Conditions" in payload
