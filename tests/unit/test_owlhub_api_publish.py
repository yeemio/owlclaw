"""Unit and property tests for OwlHub publish/state API endpoints."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.owlhub.api import create_app
from owlclaw.owlhub.api.routes.skills import _load_index

_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_ENV_KEYS = ("OWLHUB_INDEX_PATH", "OWLHUB_AUDIT_LOG", "OWLHUB_REVIEW_DIR")


def _issue_token(client: TestClient, *, code: str, role: str = "publisher") -> str:
    response = client.post("/api/v1/auth/token", json={"github_code": code, "role": role})
    assert response.status_code == 200
    return response.json()["access_token"]


def _set_env(root: Path) -> dict[str, str | None]:
    old = {key: os.getenv(key) for key in _ENV_KEYS}
    index_payload = {
        "version": "1.0",
        "generated_at": "2026-02-24T00:00:00+00:00",
        "total_skills": 0,
        "skills": [],
    }
    index_path = root / "index.json"
    index_path.write_text(json.dumps(index_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.environ["OWLHUB_INDEX_PATH"] = str(index_path)
    os.environ["OWLHUB_AUDIT_LOG"] = str(root / ".owlhub" / "audit.log.jsonl")
    os.environ["OWLHUB_REVIEW_DIR"] = str(root / ".owlhub" / "reviews")
    _load_index.cache_clear()
    return old


def _restore_env(old: dict[str, str | None]) -> None:
    for key, value in old.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    _load_index.cache_clear()


def test_successful_skill_publication_and_audit_query(tmp_path: Path) -> None:
    old = _set_env(tmp_path)
    try:
        client = TestClient(create_app())
        token = _issue_token(client, code="gho_acme1234")

        publish = client.post(
            "/api/v1/skills",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "publisher": "acme1234",
                "skill_name": "entry-monitor",
                "version": "1.0.0",
                "metadata": {"description": "Entry monitor skill", "license": "MIT", "tags": ["trading"]},
            },
        )
        assert publish.status_code == 200
        payload = publish.json()
        assert payload["accepted"] is True
        assert payload["status"] == "pending"

        detail = client.get("/api/v1/skills/acme1234/entry-monitor")
        assert detail.status_code == 200
        assert detail.json()["name"] == "entry-monitor"

        admin_token = _issue_token(client, code="gho_admin9999", role="admin")
        audit = client.get(
            "/api/v1/audit",
            params={"event_type": "publish", "limit": 10},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert audit.status_code == 200
        assert len(audit.json()) >= 1
        first = audit.json()[0]
        assert first["event_type"] == "publish"
        assert first["details"]["publisher"] == "acme1234"
        assert first["details"]["skill_name"] == "entry-monitor"
    finally:
        _restore_env(old)


def test_api_structured_logs_for_request_and_publish(tmp_path: Path, caplog) -> None:
    old = _set_env(tmp_path)
    try:
        caplog.set_level("INFO")
        client = TestClient(create_app())
        token = _issue_token(client, code="gho_acme1234")
        response = client.post(
            "/api/v1/skills",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "publisher": "acme1234",
                "skill_name": "entry-monitor",
                "version": "1.0.0",
                "metadata": {"description": "Entry monitor skill", "license": "MIT"},
            },
        )
        assert response.status_code == 200
        assert '"event": "api_request"' in caplog.text
        assert '"duration_ms"' in caplog.text
        assert '"event": "skill_publish"' in caplog.text
    finally:
        _restore_env(old)


def test_version_state_updates(tmp_path: Path) -> None:
    old = _set_env(tmp_path)
    try:
        client = TestClient(create_app())
        token = _issue_token(client, code="gho_acme1234")
        publish_body = {
            "publisher": "acme1234",
            "skill_name": "risk-checker",
            "version": "1.0.0",
            "metadata": {"description": "Risk checker skill", "license": "Apache-2.0"},
        }
        published = client.post("/api/v1/skills", headers={"Authorization": f"Bearer {token}"}, json=publish_body)
        assert published.status_code == 200

        update = client.put(
            "/api/v1/skills/acme1234/risk-checker/versions/1.0.0/state",
            headers={"Authorization": f"Bearer {token}"},
            json={"state": "deprecated"},
        )
        assert update.status_code == 200
        assert update.json()["state"] == "deprecated"

        versions = client.get("/api/v1/skills/acme1234/risk-checker/versions")
        assert versions.status_code == 200
        assert versions.json()[-1]["version_state"] == "deprecated"
    finally:
        _restore_env(old)


def test_publisher_validation_rejects_foreign_publish(tmp_path: Path) -> None:
    old = _set_env(tmp_path)
    try:
        client = TestClient(create_app())
        token = _issue_token(client, code="gho_user0001")
        response = client.post(
            "/api/v1/skills",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "publisher": "acme1234",
                "skill_name": "entry-monitor",
                "version": "1.0.0",
                "metadata": {"description": "Entry monitor skill", "license": "MIT"},
            },
        )
        assert response.status_code == 403
    finally:
        _restore_env(old)


def test_validation_integration_rejects_invalid_manifest(tmp_path: Path) -> None:
    old = _set_env(tmp_path)
    try:
        client = TestClient(create_app())
        token = _issue_token(client, code="gho_acme1234")
        response = client.post(
            "/api/v1/skills",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "publisher": "acme1234",
                "skill_name": "invalid-skill",
                "version": "1.0.0",
                "metadata": {},
            },
        )
        assert response.status_code == 422
        detail = response.json()["detail"]
        assert detail["message"] == "manifest validation failed"
        assert detail["review_id"] == "acme1234-invalid-skill-1.0.0"

        missing = client.get("/api/v1/skills/acme1234/invalid-skill")
        assert missing.status_code == 404
    finally:
        _restore_env(old)


@settings(max_examples=8, deadline=None)
@given(
    skill_name=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-", min_size=3, max_size=20).filter(
        lambda text: _NAME_RE.fullmatch(text) is not None
    ),
    major=st.integers(min_value=0, max_value=9),
    minor=st.integers(min_value=0, max_value=9),
    patch=st.integers(min_value=0, max_value=9),
)
def test_property_1_api_publish_and_retrieval(skill_name: str, major: int, minor: int, patch: int) -> None:
    """Property 1: published skills can be retrieved via API."""
    with tempfile.TemporaryDirectory() as workdir:
        old = _set_env(Path(workdir))
        try:
            client = TestClient(create_app())
            token = _issue_token(client, code="gho_pub1234")
            version = f"{major}.{minor}.{patch}"
            publish = client.post(
                "/api/v1/skills",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "publisher": "pub1234",
                    "skill_name": skill_name,
                    "version": version,
                    "metadata": {"description": "Property validation skill", "license": "MIT"},
                },
            )
            assert publish.status_code == 200
            detail = client.get(f"/api/v1/skills/pub1234/{skill_name}")
            assert detail.status_code == 200
            versions = [item["version"] for item in detail.json()["versions"]]
            assert version in versions
        finally:
            _restore_env(old)


@settings(max_examples=8, deadline=None)
@given(
    skill_name=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-", min_size=3, max_size=20).filter(
        lambda text: _NAME_RE.fullmatch(text) is not None
    ),
    state=st.sampled_from(["draft", "released", "deprecated"]),
)
def test_property_15_publish_audit_log_completeness(skill_name: str, state: str) -> None:
    """Property 15: publish/state operations emit complete audit logs."""
    with tempfile.TemporaryDirectory() as workdir:
        old = _set_env(Path(workdir))
        try:
            client = TestClient(create_app())
            token = _issue_token(client, code="gho_pub1234")
            publish = client.post(
                "/api/v1/skills",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "publisher": "pub1234",
                    "skill_name": skill_name,
                    "version": "1.0.0",
                    "metadata": {"description": "Audit validation skill", "license": "MIT"},
                },
            )
            assert publish.status_code == 200
            update = client.put(
                f"/api/v1/skills/pub1234/{skill_name}/versions/1.0.0/state",
                headers={"Authorization": f"Bearer {token}"},
                json={"state": state},
            )
            assert update.status_code == 200

            admin_token = _issue_token(client, code="gho_admin9000", role="admin")
            logs = client.get("/api/v1/audit", headers={"Authorization": f"Bearer {admin_token}"})
            assert logs.status_code == 200
            payload = logs.json()
            assert any(item["event_type"] == "publish" for item in payload)
            assert any(item["event_type"] == "state_update" for item in payload)
            for item in payload:
                assert "timestamp" in item
                assert "user_id" in item
                assert isinstance(item.get("details", {}), dict)
        finally:
            _restore_env(old)

