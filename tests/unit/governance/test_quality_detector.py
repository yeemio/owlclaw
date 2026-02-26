"""Unit tests for quality trend detector."""

from datetime import datetime, timedelta, timezone

import pytest

from owlclaw.governance.quality_detector import (
    detect_degradation,
    notify_quality_degradation,
    suggest_improvements,
)
from owlclaw.governance.quality_store import SkillQualitySnapshot
from owlclaw.triggers.signal import SignalType


def _snapshot(*, score: float, at: datetime) -> SkillQualitySnapshot:
    return SkillQualitySnapshot(
        tenant_id="default",
        skill_name="inventory-monitor",
        window_start=at - timedelta(days=7),
        window_end=at,
        metrics={},
        quality_score=score,
        computed_at=at,
    )


def test_detect_degradation_true_for_three_consecutive_drops() -> None:
    now = datetime.now(timezone.utc)
    snapshots = [
        _snapshot(score=0.95, at=now - timedelta(days=21)),
        _snapshot(score=0.84, at=now - timedelta(days=14)),
        _snapshot(score=0.70, at=now - timedelta(days=7)),
    ]
    assert detect_degradation(snapshots) is True


def test_detect_degradation_false_when_not_continuous() -> None:
    now = datetime.now(timezone.utc)
    snapshots = [
        _snapshot(score=0.95, at=now - timedelta(days=21)),
        _snapshot(score=0.90, at=now - timedelta(days=14)),
        _snapshot(score=0.89, at=now - timedelta(days=7)),
    ]
    assert detect_degradation(snapshots) is False


def test_suggest_improvements_prefers_low_metrics() -> None:
    snapshot = SkillQualitySnapshot(
        tenant_id="default",
        skill_name="inventory-monitor",
        window_start=datetime.now(timezone.utc) - timedelta(days=7),
        window_end=datetime.now(timezone.utc),
        metrics={
            "success_rate": 0.5,
            "intervention_rate": 0.7,
            "consistency": 0.6,
            "avg_latency_ms": 5000,
            "avg_cost": 0.5,
        },
        quality_score=0.4,
        computed_at=datetime.now(timezone.utc),
    )
    suggestions = suggest_improvements(snapshot)
    assert any("Improve success rate" in text for text in suggestions)
    assert any("Reduce manual intervention" in text for text in suggestions)


@pytest.mark.asyncio
async def test_notify_quality_degradation_dispatches_signal() -> None:
    class _Router:
        def __init__(self) -> None:
            self.signal = None

        async def dispatch(self, signal):  # type: ignore[no-untyped-def]
            self.signal = signal
            return None

    router = _Router()
    await notify_quality_degradation(
        router=router,  # type: ignore[arg-type]
        tenant_id="default",
        agent_id="agent-1",
        skill_name="inventory-monitor",
        score=0.52,
    )
    assert router.signal is not None
    assert router.signal.type == SignalType.INSTRUCT
    assert "inventory-monitor" in router.signal.message
