"""Unit and property tests for OwlHub review workflow API."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.owlhub.api import create_app


def _issue_token(client: TestClient, *, code: str, role: str) -> str:
    response = client.post("/api/v1/auth/token", json={"github_code": code, "role": role})
    assert response.status_code == 200
    return response.json()["access_token"]


def _prepare_env(root: Path) -> dict[str, str | None]:
    old = {key: os.getenv(key) for key in ("OWLHUB_REVIEW_DIR", "OWLHUB_STATISTICS_DB")}
    os.environ["OWLHUB_REVIEW_DIR"] = str(root / "reviews")
    os.environ["OWLHUB_STATISTICS_DB"] = str(root / "stats.json")
    return old


def _restore_env(old: dict[str, str | None]) -> None:
    for key, value in old.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def test_pending_approve_reject_and_permissions(tmp_path: Path) -> None:
    old = _prepare_env(tmp_path)
    try:
        app = create_app()
        system = app.state.review_system
        pending = system.submit_manifest_for_review(
            manifest={
                "name": "entry-monitor",
                "version": "1.0.0",
                "publisher": "acme",
                "description": "entry monitor skill",
                "license": "MIT",
            },
            skill_name="entry-monitor",
            version="1.0.0",
            publisher="acme",
        )
        client = TestClient(app)
        publisher_token = _issue_token(client, code="gho_pub12345", role="publisher")
        forbidden = client.get("/api/v1/reviews/pending", headers={"Authorization": f"Bearer {publisher_token}"})
        assert forbidden.status_code == 403

        reviewer_token = _issue_token(client, code="gho_rev12345", role="reviewer")
        pending_resp = client.get("/api/v1/reviews/pending", headers={"Authorization": f"Bearer {reviewer_token}"})
        assert pending_resp.status_code == 200
        assert any(item["review_id"] == pending.review_id for item in pending_resp.json())

        approve = client.post(
            f"/api/v1/reviews/{pending.review_id}/approve",
            headers={"Authorization": f"Bearer {reviewer_token}"},
        )
        assert approve.status_code == 200
        assert approve.json()["status"] == "approved"
    finally:
        _restore_env(old)


def test_appeal_flow_for_rejected_review(tmp_path: Path) -> None:
    old = _prepare_env(tmp_path)
    try:
        app = create_app()
        system = app.state.review_system
        rejected = system.submit_manifest_for_review(
            manifest={
                "name": "bad-skill",
                "version": "1.0.0",
                "publisher": "publishe",
                "description": "",
                "license": "",
            },
            skill_name="bad-skill",
            version="1.0.0",
            publisher="publishe",
        )
        assert rejected.status.value == "rejected"

        client = TestClient(app)
        publisher_token = _issue_token(client, code="gho_publisher1", role="publisher")
        appeal = client.post(
            f"/api/v1/reviews/{rejected.review_id}/appeal",
            headers={"Authorization": f"Bearer {publisher_token}"},
            json={"reason": "please recheck"},
        )
        assert appeal.status_code == 200
        assert appeal.json()["review_id"] == rejected.review_id
        assert len(system.list_appeals(review_id=rejected.review_id)) == 1
    finally:
        _restore_env(old)


@settings(max_examples=80, deadline=None)
@given(should_approve=st.booleans())
def test_property_20_review_state_transition_api(should_approve: bool) -> None:
    """Property 20: API review transitions are valid and single-step."""
    with tempfile.TemporaryDirectory() as workdir:
        old = _prepare_env(Path(workdir))
        try:
            app = create_app()
            system = app.state.review_system
            pending = system.submit_manifest_for_review(
                manifest={
                    "name": "entry-monitor",
                    "version": "1.0.0",
                    "publisher": "acme",
                    "description": "entry monitor skill",
                    "license": "MIT",
                },
                skill_name="entry-monitor",
                version="1.0.0",
                publisher="acme",
            )
            client = TestClient(app)
            reviewer_token = _issue_token(client, code="gho_rev12345", role="reviewer")
            if should_approve:
                first = client.post(
                    f"/api/v1/reviews/{pending.review_id}/approve",
                    headers={"Authorization": f"Bearer {reviewer_token}"},
                )
                second = client.post(
                    f"/api/v1/reviews/{pending.review_id}/reject",
                    headers={"Authorization": f"Bearer {reviewer_token}"},
                    json={"reason": "late reject"},
                )
            else:
                first = client.post(
                    f"/api/v1/reviews/{pending.review_id}/reject",
                    headers={"Authorization": f"Bearer {reviewer_token}"},
                    json={"reason": "invalid"},
                )
                second = client.post(
                    f"/api/v1/reviews/{pending.review_id}/approve",
                    headers={"Authorization": f"Bearer {reviewer_token}"},
                )
            assert first.status_code == 200
            assert second.status_code == 409
        finally:
            _restore_env(old)


@settings(max_examples=60, deadline=None)
@given(reasons=st.lists(st.text(alphabet="abcdefghijklmnopqrstuvwxyz ", min_size=1, max_size=20), min_size=1, max_size=5))
def test_property_23_appeal_records_persist(reasons: list[str]) -> None:
    """Property 23: appeal records are persisted with complete information."""
    with tempfile.TemporaryDirectory() as workdir:
        old = _prepare_env(Path(workdir))
        try:
            app = create_app()
            system = app.state.review_system
            rejected = system.submit_manifest_for_review(
                manifest={
                    "name": "bad-skill",
                    "version": "1.0.0",
                    "publisher": "publishe",
                    "description": "",
                    "license": "",
                },
                skill_name="bad-skill",
                version="1.0.0",
                publisher="publishe",
            )
            client = TestClient(app)
            publisher_token = _issue_token(client, code="gho_publisher1", role="publisher")
            for reason in reasons:
                response = client.post(
                    f"/api/v1/reviews/{rejected.review_id}/appeal",
                    headers={"Authorization": f"Bearer {publisher_token}"},
                    json={"reason": reason},
                )
                assert response.status_code == 200

            appeals = system.list_appeals(review_id=rejected.review_id)
            assert len(appeals) == len(reasons)
            assert all(item.review_id == rejected.review_id for item in appeals)
            assert all(item.publisher == "publishe" for item in appeals)
        finally:
            _restore_env(old)
