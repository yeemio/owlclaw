"""Unit tests for OwlHub API schemas and app foundation."""

from __future__ import annotations

from fastapi.testclient import TestClient
from pydantic import ValidationError

from owlclaw.owlhub.api import create_app
from owlclaw.owlhub.api.schemas import (
    PublishRequest,
    SkillDetail,
    SkillSearchItem,
    SkillSearchResponse,
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
    publish = PublishRequest(
        publisher="acme",
        skill_name="entry-monitor",
        version="1.0.0",
        metadata={"license": "MIT"},
    )
    assert response.total == 1
    assert detail.versions[0].version == "1.0.0"
    assert publish.publisher == "acme"


def test_schema_validation_with_invalid_data() -> None:
    try:
        SkillSearchResponse(total="invalid", page=1, page_size=20, items=[])
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
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert search.status_code == 200
    assert search.json()["total"] == 0
