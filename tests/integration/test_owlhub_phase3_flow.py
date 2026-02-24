"""Integration tests for OwlHub Phase 3 service API workflows."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient

from owlclaw.owlhub import OwlHubClient
from owlclaw.owlhub.api import create_app
from owlclaw.owlhub.api.routes.skills import _load_index
from owlclaw.owlhub.indexer import IndexBuilder
from tests.unit.test_owlhub_cli_client import _build_skill_archive


def _prepare_env(root: Path) -> dict[str, str | None]:
    keys = (
        "OWLHUB_INDEX_PATH",
        "OWLHUB_REVIEW_DIR",
        "OWLHUB_AUDIT_LOG",
        "OWLHUB_STATISTICS_DB",
        "OWLHUB_BLACKLIST_DB",
    )
    old = {key: os.getenv(key) for key in keys}
    os.environ["OWLHUB_INDEX_PATH"] = str(root / "index.json")
    os.environ["OWLHUB_REVIEW_DIR"] = str(root / "reviews")
    os.environ["OWLHUB_AUDIT_LOG"] = str(root / "audit.log.jsonl")
    os.environ["OWLHUB_STATISTICS_DB"] = str(root / "statistics.json")
    os.environ["OWLHUB_BLACKLIST_DB"] = str(root / "blacklist.json")
    _load_index.cache_clear()
    return old


def _restore_env(old: dict[str, str | None]) -> None:
    for key, value in old.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    _load_index.cache_clear()


def _issue_token(client: TestClient, *, code: str, role: str) -> str:
    response = client.post("/api/v1/auth/token", json={"github_code": code, "role": role})
    assert response.status_code == 200
    token = response.json().get("access_token")
    assert isinstance(token, str)
    return token


def test_phase3_publish_review_and_audit_flow(tmp_path: Path) -> None:
    old = _prepare_env(tmp_path)
    try:
        app = create_app()
        client = TestClient(app)
        owner_token = _issue_token(client, code="gho_acme1111", role="publisher")
        reviewer_token = _issue_token(client, code="gho_reviewer", role="reviewer")
        admin_token = _issue_token(client, code="gho_admin111", role="admin")

        archive = _build_skill_archive(tmp_path, name="phase3-skill", publisher="acme1111", version="1.0.0")
        checksum = IndexBuilder().calculate_checksum(archive)
        publish = client.post(
            "/api/v1/skills",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={
                "publisher": "acme1111",
                "skill_name": "phase3-skill",
                "version": "1.0.0",
                "metadata": {
                    "description": "phase3 integration skill",
                    "license": "MIT",
                    "tags": ["phase3", "integration"],
                    "dependencies": {},
                    "download_url": str(archive),
                    "checksum": checksum,
                },
            },
        )
        assert publish.status_code == 200
        review_id = publish.json()["review_id"]
        assert publish.json()["status"] == "pending"

        pending = client.get("/api/v1/reviews/pending", headers={"Authorization": f"Bearer {reviewer_token}"})
        assert pending.status_code == 200
        assert any(row["review_id"] == review_id for row in pending.json())

        approve = client.post(f"/api/v1/reviews/{review_id}/approve", headers={"Authorization": f"Bearer {reviewer_token}"})
        assert approve.status_code == 200
        assert approve.json()["status"] == "approved"

        search = client.get("/api/v1/skills", params={"query": "phase3-skill"})
        assert search.status_code == 200
        assert search.json()["total"] == 1

        detail = client.get("/api/v1/skills/acme1111/phase3-skill")
        assert detail.status_code == 200
        assert detail.json()["name"] == "phase3-skill"

        audit = client.get(
            "/api/v1/audit",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"event_type": "publish"},
        )
        assert audit.status_code == 200
        assert any(row["details"]["skill_name"] == "phase3-skill" for row in audit.json())
    finally:
        _restore_env(old)


def test_phase3_statistics_export_requires_admin_and_returns_counts(tmp_path: Path) -> None:
    old = _prepare_env(tmp_path)
    try:
        app = create_app()
        client = TestClient(app)
        owner_token = _issue_token(client, code="gho_acme1111", role="publisher")
        admin_token = _issue_token(client, code="gho_admin111", role="admin")

        archive = _build_skill_archive(tmp_path, name="stats-skill", publisher="acme1111", version="1.0.0")
        checksum = IndexBuilder().calculate_checksum(archive)
        publish = client.post(
            "/api/v1/skills",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={
                "publisher": "acme1111",
                "skill_name": "stats-skill",
                "version": "1.0.0",
                "metadata": {
                    "description": "stats integration skill",
                    "license": "MIT",
                    "download_url": str(archive),
                    "checksum": checksum,
                },
            },
        )
        assert publish.status_code == 200

        app.state.statistics_tracker.record_download(skill_name="stats-skill", publisher="acme1111", version="1.0.0")
        app.state.statistics_tracker.record_install(
            skill_name="stats-skill",
            publisher="acme1111",
            version="1.0.0",
            user_id="user-a",
        )

        stats = client.get("/api/v1/skills/acme1111/stats-skill/statistics")
        assert stats.status_code == 200
        assert stats.json()["total_downloads"] >= 1
        assert stats.json()["total_installs"] >= 1

        forbidden = client.get("/api/v1/statistics/export", headers={"Authorization": f"Bearer {owner_token}"})
        assert forbidden.status_code == 403

        exported = client.get(
            "/api/v1/statistics/export",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"format": "csv"},
        )
        assert exported.status_code == 200
        assert "stats-skill" in exported.text
    finally:
        _restore_env(old)


def test_phase3_dependency_installation_and_blacklist_enforcement(tmp_path: Path) -> None:
    old = _prepare_env(tmp_path)
    try:
        app = create_app()
        client = TestClient(app)
        owner_token = _issue_token(client, code="gho_acme1111", role="publisher")
        admin_token = _issue_token(client, code="gho_admin111", role="admin")

        dep_archive = _build_skill_archive(tmp_path, name="dep-skill", publisher="acme1111", version="1.0.0")
        dep_checksum = IndexBuilder().calculate_checksum(dep_archive)
        dep_publish = client.post(
            "/api/v1/skills",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={
                "publisher": "acme1111",
                "skill_name": "dep-skill",
                "version": "1.0.0",
                "metadata": {
                    "description": "dependency skill",
                    "license": "MIT",
                    "dependencies": {},
                    "download_url": str(dep_archive),
                    "checksum": dep_checksum,
                },
            },
        )
        assert dep_publish.status_code == 200

        root_archive = _build_skill_archive(tmp_path, name="root-skill", publisher="acme1111", version="1.0.0")
        root_checksum = IndexBuilder().calculate_checksum(root_archive)
        root_publish = client.post(
            "/api/v1/skills",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={
                "publisher": "acme1111",
                "skill_name": "root-skill",
                "version": "1.0.0",
                "metadata": {
                    "description": "root skill",
                    "license": "MIT",
                    "dependencies": {"dep-skill": "^1.0.0"},
                    "download_url": str(root_archive),
                    "checksum": root_checksum,
                },
            },
        )
        assert root_publish.status_code == 200

        index_path = Path(os.environ["OWLHUB_INDEX_PATH"])
        install_client = OwlHubClient(
            index_url=str(index_path),
            install_dir=tmp_path / "skills",
            lock_file=tmp_path / "skill-lock.json",
        )
        install_client.install(name="root-skill")
        assert (tmp_path / "skills" / "dep-skill" / "1.0.0").exists()
        assert (tmp_path / "skills" / "root-skill" / "1.0.0").exists()

        blocked = client.post(
            "/api/v1/admin/blacklist",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"publisher": "acme1111", "skill_name": "dep-skill", "reason": "policy"},
        )
        assert blocked.status_code == 200

        hidden = client.get("/api/v1/skills", params={"query": "dep-skill"})
        assert hidden.status_code == 200
        assert hidden.json()["total"] == 0

        fresh_client = OwlHubClient(
            index_url=str(index_path),
            install_dir=tmp_path / "skills-2",
            lock_file=tmp_path / "skill-lock-2.json",
        )
        try:
            fresh_client.install(name="root-skill")
            raise AssertionError("expected dependency resolution failure after blacklist")
        except ValueError:
            pass
    finally:
        _restore_env(old)
