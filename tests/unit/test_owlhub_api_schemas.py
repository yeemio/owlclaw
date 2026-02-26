"""Unit tests for OwlHub API schemas and app foundation."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
from pydantic import ValidationError

from owlclaw.owlhub.api import create_app
from owlclaw.owlhub.api.schemas import (
    AppealRequest,
    PublishRequest,
    RejectRequest,
    ReviewRecordResponse,
    SkillDetail,
    SkillSearchItem,
    SkillSearchResponse,
    SkillStatisticsResponse,
    UpdateStateRequest,
    VersionInfo,
)


def test_schema_validation_with_valid_data() -> None:
    version = VersionInfo(version="1.0.0", version_state="released")
    item = SkillSearchItem(
        name="entry-monitor",
        publisher="acme",
        version="1.0.0",
        description="Monitor entries",
        tags=["trading"],
    )
    response = SkillSearchResponse(total=1, page=1, page_size=20, items=[item])
    detail = SkillDetail(
        name="entry-monitor",
        publisher="acme",
        description="Monitor entries",
        tags=["trading"],
        versions=[version],
        statistics={"total_downloads": 10},
    )
    stats_response = SkillStatisticsResponse(
        skill_name="entry-monitor",
        publisher="acme",
        total_downloads=10,
        downloads_last_30d=5,
        total_installs=8,
        active_installs=3,
        last_updated=datetime.now(timezone.utc),
    )
    publish = PublishRequest(
        publisher="acme",
        skill_name="entry-monitor",
        version="1.0.0",
        metadata={"license": "MIT"},
    )
    reject = RejectRequest(reason="policy violation")
    appeal = AppealRequest(reason="please review again")
    review = ReviewRecordResponse(
        review_id="acme-entry-monitor-1.0.0",
        skill_name="entry-monitor",
        version="1.0.0",
        publisher="acme",
        status="pending",
        comments="ok",
        reviewed_at=datetime.now(timezone.utc),
    )
    update_state = UpdateStateRequest(state="released")
    assert response.total == 1
    assert detail.versions[0].version == "1.0.0"
    assert publish.publisher == "acme"
    assert update_state.state == "released"
    assert stats_response.skill_name == "entry-monitor"
    assert reject.reason
    assert appeal.reason
    assert review.review_id


def test_schema_validation_with_invalid_data() -> None:
    try:
        SkillSearchResponse(total="invalid", page=1, page_size=20, items=[])  # type: ignore[arg-type]
        raise AssertionError("expected validation error")
    except ValidationError:
        pass


def test_schema_serialization_round_trip() -> None:
    item = SkillSearchItem(
        name="entry-monitor",
        publisher="acme",
        version="1.0.0",
        description="Monitor entries",
    )
    payload = item.model_dump()
    restored = SkillSearchItem.model_validate(payload)
    assert restored == item


def test_app_health_and_search_endpoints() -> None:
    app = create_app()
    client = TestClient(app)
    health = client.get("/health")
    search = client.get("/api/v1/skills")
    metrics = client.get("/metrics")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert "checks" in health.json()
    assert search.status_code == 200
    assert search.json()["total"] == 0
    assert metrics.status_code == 200
    assert "owlhub_api_requests_total" in metrics.text
    assert "owlhub_api_error_rate" in metrics.text

