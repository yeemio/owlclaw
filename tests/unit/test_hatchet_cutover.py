"""Unit tests for migration cutover helpers."""

from __future__ import annotations

import pytest

from owlclaw.integrations.hatchet_cutover import build_cutover_decision, normalize_scheduler_backend


def test_normalize_scheduler_backend_accepts_supported_values() -> None:
    assert normalize_scheduler_backend("apscheduler") == "apscheduler"
    assert normalize_scheduler_backend(" dual ") == "dual"
    assert normalize_scheduler_backend("HATCHET") == "hatchet"


def test_normalize_scheduler_backend_rejects_invalid_value() -> None:
    with pytest.raises(ValueError, match="scheduler backend must be one of"):
        normalize_scheduler_backend("cron")


def test_build_cutover_decision_recommends_hatchet_on_full_match() -> None:
    decision = build_cutover_decision(match_rate=1.0, mismatch_count=0)
    assert decision["recommended_backend"] == "hatchet"
    assert decision["allow_disable_apscheduler"] is True


def test_build_cutover_decision_recommends_dual_on_mismatch() -> None:
    decision = build_cutover_decision(match_rate=0.9, mismatch_count=1)
    assert decision["recommended_backend"] == "dual"
    assert decision["allow_disable_apscheduler"] is False


def test_build_cutover_decision_rejects_invalid_match_rate() -> None:
    with pytest.raises(ValueError, match="match_rate must be a finite value"):
        build_cutover_decision(match_rate=1.2, mismatch_count=0)
