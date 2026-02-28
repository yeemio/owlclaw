"""Tests for article direction selection from real metrics."""

from __future__ import annotations

from scripts.content.select_article_direction import choose_direction


def test_choose_direction_prefers_governance_when_cost_reduction_stronger() -> None:
    decision = choose_direction(
        {
            "llm": {"delta_cost_pct": "-55.0%"},
            "scheduler": {
                "delta_success_rate_pct": "2.0%",
                "delta_recovery_seconds_pct": "-5.0%",
            },
        }
    )
    assert decision.direction == "A"


def test_choose_direction_prefers_scheduler_when_recovery_signal_stronger() -> None:
    decision = choose_direction(
        {
            "llm": {"delta_cost_pct": "-10.0%"},
            "scheduler": {
                "delta_success_rate_pct": "8.0%",
                "delta_recovery_seconds_pct": "-60.0%",
            },
        }
    )
    assert decision.direction == "B"


def test_choose_direction_falls_back_to_c_when_no_strong_signal() -> None:
    decision = choose_direction(
        {
            "llm": {"delta_cost_pct": "n/a"},
            "scheduler": {
                "delta_success_rate_pct": "n/a",
                "delta_recovery_seconds_pct": "n/a",
            },
        }
    )
    assert decision.direction == "C"
