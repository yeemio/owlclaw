"""Cutover helpers for APScheduler -> Hatchet migration."""

from __future__ import annotations

from typing import Literal


SchedulerBackend = Literal["apscheduler", "dual", "hatchet"]


def normalize_scheduler_backend(value: str) -> SchedulerBackend:
    """Normalize scheduler backend value with strict validation."""
    normalized = value.strip().lower()
    if normalized not in {"apscheduler", "dual", "hatchet"}:
        raise ValueError("scheduler backend must be one of: apscheduler, dual, hatchet")
    return normalized  # type: ignore[return-value]


def build_cutover_decision(*, match_rate: float, mismatch_count: int) -> dict[str, object]:
    """Build a deterministic cutover decision from replay consistency metrics."""
    safe_match = max(0.0, min(1.0, float(match_rate)))
    mismatches = max(0, int(mismatch_count))
    if mismatches == 0 and safe_match >= 1.0:
        return {
            "recommended_backend": "hatchet",
            "reason": "replay_consistent",
            "allow_disable_apscheduler": True,
        }
    return {
        "recommended_backend": "dual",
        "reason": "replay_mismatch_detected",
        "allow_disable_apscheduler": False,
    }
