"""Unit tests for quality snapshot store."""

from datetime import datetime, timedelta, timezone

from owlclaw.governance.quality_store import InMemoryQualityStore, SkillQualitySnapshot


def _snapshot(*, skill: str, score: float, at: datetime, tenant: str = "default") -> SkillQualitySnapshot:
    return SkillQualitySnapshot(
        tenant_id=tenant,
        skill_name=skill,
        window_start=at - timedelta(days=7),
        window_end=at,
        metrics={"success_rate": score},
        quality_score=score,
        computed_at=at,
    )


def test_inmemory_quality_store_list_and_latest() -> None:
    store = InMemoryQualityStore()
    now = datetime.now(timezone.utc)
    store.save(_snapshot(skill="inventory-monitor", score=0.7, at=now - timedelta(days=1)))
    store.save(_snapshot(skill="inventory-monitor", score=0.8, at=now))
    rows = store.list_for_skill(tenant_id="default", skill_name="inventory-monitor")
    assert [r.quality_score for r in rows] == [0.7, 0.8]
    latest = store.latest_for_skill(tenant_id="default", skill_name="inventory-monitor")
    assert latest is not None
    assert latest.quality_score == 0.8


def test_inmemory_quality_store_all_latest_grouped_by_skill() -> None:
    store = InMemoryQualityStore()
    now = datetime.now(timezone.utc)
    store.save(_snapshot(skill="inventory-monitor", score=0.6, at=now - timedelta(days=1)))
    store.save(_snapshot(skill="inventory-monitor", score=0.9, at=now))
    store.save(_snapshot(skill="report-generator", score=0.5, at=now))
    store.save(_snapshot(skill="inventory-monitor", score=0.95, at=now, tenant="other"))

    rows = store.all_latest(tenant_id="default")
    assert [r.skill_name for r in rows] == ["inventory-monitor", "report-generator"]
    assert rows[0].quality_score == 0.9
    assert rows[1].quality_score == 0.5
