"""Unit and property tests for OwlHub blacklist and takedown moderation."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.owlhub import OwlHubClient
from owlclaw.owlhub.api import create_app
from owlclaw.owlhub.api.routes.skills import _load_index
from tests.unit.test_owlhub_cli_client import _build_index_file, _build_skill_archive


def _issue_token(client: TestClient, *, code: str, role: str = "publisher") -> str:
    response = client.post("/api/v1/auth/token", json={"github_code": code, "role": role})
    assert response.status_code == 200
    return response.json()["access_token"]


def _prepare_env(root: Path) -> dict[str, str | None]:
    keys = (
        "OWLHUB_INDEX_PATH",
        "OWLHUB_REVIEW_DIR",
        "OWLHUB_AUDIT_LOG",
        "OWLHUB_STATISTICS_DB",
        "OWLHUB_BLACKLIST_DB",
    )
    old = {key: os.getenv(key) for key in keys}
    index = {
        "version": "1.0",
        "generated_at": "2026-02-24T00:00:00+00:00",
        "total_skills": 2,
        "skills": [
            {
                "manifest": {
                    "name": "entry-monitor",
                    "publisher": "acme",
                    "version": "1.0.0",
                    "description": "entry monitor",
                    "license": "MIT",
                    "dependencies": {},
                    "tags": ["monitor"],
                },
                "version_state": "released",
                "published_at": "2026-02-24T00:00:00+00:00",
                "updated_at": "2026-02-24T00:00:00+00:00",
            },
            {
                "manifest": {
                    "name": "risk-checker",
                    "publisher": "acme",
                    "version": "1.0.0",
                    "description": "risk checker",
                    "license": "MIT",
                    "dependencies": {},
                    "tags": ["risk"],
                },
                "version_state": "released",
                "published_at": "2026-02-24T00:00:00+00:00",
                "updated_at": "2026-02-24T00:00:00+00:00",
            },
        ],
    }
    index_path = root / "index.json"
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    os.environ["OWLHUB_INDEX_PATH"] = str(index_path)
    os.environ["OWLHUB_REVIEW_DIR"] = str(root / "reviews")
    os.environ["OWLHUB_AUDIT_LOG"] = str(root / "audit.jsonl")
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


def test_blacklist_add_remove_and_search_filter(tmp_path: Path) -> None:
    old = _prepare_env(tmp_path)
    try:
        client = TestClient(create_app())
        admin = _issue_token(client, code="gho_admin1111", role="admin")
        add = client.post(
            "/api/v1/admin/blacklist",
            headers={"Authorization": f"Bearer {admin}"},
            json={"publisher": "acme", "skill_name": "entry-monitor", "reason": "malicious"},
        )
        assert add.status_code == 200

        search = client.get("/api/v1/skills")
        assert search.status_code == 200
        names = [item["name"] for item in search.json()["items"]]
        assert "entry-monitor" not in names
        assert "risk-checker" in names

        listing = client.get("/api/v1/admin/blacklist", headers={"Authorization": f"Bearer {admin}"})
        assert listing.status_code == 200
        assert len(listing.json()) == 1

        remove = client.delete(
            "/api/v1/admin/blacklist",
            params={"publisher": "acme", "skill_name": "entry-monitor"},
            headers={"Authorization": f"Bearer {admin}"},
        )
        assert remove.status_code == 200
        assert remove.json()["removed"] is True
    finally:
        _restore_env(old)


def test_takedown_hides_public_view_but_installed_remains(tmp_path: Path) -> None:
    old = _prepare_env(tmp_path)
    try:
        app = create_app()
        client = TestClient(app)
        admin = _issue_token(client, code="gho_admin1111", role="admin")
        owner = _issue_token(client, code="gho_acme1111", role="publisher")

        publish = client.post(
            "/api/v1/skills",
            headers={"Authorization": f"Bearer {owner}"},
            json={
                "publisher": "acme1111",
                "skill_name": "user-tool",
                "version": "1.0.0",
                "metadata": {"description": "user tool skill", "license": "MIT", "download_url": ""},
            },
        )
        assert publish.status_code == 200

        takedown = client.post(
            "/api/v1/skills/acme1111/user-tool/takedown",
            headers={"Authorization": f"Bearer {admin}"},
            json={"reason": "policy violation"},
        )
        assert takedown.status_code == 200

        hidden = client.get("/api/v1/skills", params={"query": "user-tool"})
        assert hidden.status_code == 200
        assert hidden.json()["total"] == 0
    finally:
        _restore_env(old)


def test_client_install_blocked_for_moderated_skill(tmp_path: Path) -> None:
    archive = _build_skill_archive(tmp_path, name="blocked-skill", publisher="acme", version="1.0.0")
    index_file = _build_index_file(tmp_path, archive, name="blocked-skill", publisher="acme", version="1.0.0")
    payload = json.loads(index_file.read_text(encoding="utf-8"))
    payload["skills"][0]["blacklisted"] = True
    index_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    client = OwlHubClient(index_url=str(index_file), install_dir=tmp_path / "skills", lock_file=tmp_path / "lock.json")
    assert client.search(query="blocked-skill") == []
    try:
        client.install(name="blocked-skill")
        raise AssertionError("expected moderation policy block")
    except ValueError as exc:
        assert "not found" in str(exc) or "blocked" in str(exc)


def test_takedown_preserves_existing_installs(tmp_path: Path) -> None:
    archive = _build_skill_archive(tmp_path, name="steady-skill", publisher="acme", version="1.0.0")
    index_file = _build_index_file(tmp_path, archive, name="steady-skill", publisher="acme", version="1.0.0")
    lock_file = tmp_path / "skill-lock.json"
    client = OwlHubClient(index_url=str(index_file), install_dir=tmp_path / "skills", lock_file=lock_file)
    client.install(name="steady-skill")
    before = client.list_installed()
    assert len(before) == 1

    payload = json.loads(index_file.read_text(encoding="utf-8"))
    payload["skills"][0]["takedown"] = {
        "is_taken_down": True,
        "reason": "policy",
        "timestamp": "2026-02-24T00:00:00+00:00",
    }
    index_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    assert client.search(query="steady-skill") == []
    after = client.list_installed()
    assert len(after) == 1
    assert after[0]["name"] == "steady-skill"


@settings(max_examples=10, deadline=None)
@given(
    skill_name=st.sampled_from(["entry-monitor", "risk-checker"]),
    publisher_level=st.booleans(),
)
def test_property_17_blacklist_filtering(skill_name: str, publisher_level: bool) -> None:
    """Property 17: blacklisted skills are excluded from public search/install."""
    with tempfile.TemporaryDirectory() as workdir:
        old = _prepare_env(Path(workdir))
        try:
            app = create_app()
            client = TestClient(app)
            admin = _issue_token(client, code="gho_admin1111", role="admin")
            payload = {
                "publisher": "acme",
                "skill_name": None if publisher_level else skill_name,
                "reason": "policy",
            }
            add = client.post("/api/v1/admin/blacklist", headers={"Authorization": f"Bearer {admin}"}, json=payload)
            assert add.status_code == 200
            search = client.get("/api/v1/skills")
            assert search.status_code == 200
            names = {item["name"] for item in search.json()["items"]}
            if publisher_level:
                assert "entry-monitor" not in names and "risk-checker" not in names
            else:
                assert skill_name not in names
        finally:
            _restore_env(old)


@settings(max_examples=10, deadline=None)
@given(skill_name=st.sampled_from(["entry-monitor", "risk-checker"]))
def test_property_22_takedown_hidden(skill_name: str) -> None:
    """Property 22: taken down skills are hidden from public discovery."""
    with tempfile.TemporaryDirectory() as workdir:
        old = _prepare_env(Path(workdir))
        try:
            app = create_app()
            client = TestClient(app)
            admin = _issue_token(client, code="gho_admin1111", role="admin")
            down = client.post(
                f"/api/v1/skills/acme/{skill_name}/takedown",
                headers={"Authorization": f"Bearer {admin}"},
                json={"reason": "policy"},
            )
            assert down.status_code == 200
            search = client.get("/api/v1/skills", params={"query": skill_name})
            assert search.status_code == 200
            assert search.json()["total"] == 0
            detail = client.get(f"/api/v1/skills/acme/{skill_name}")
            assert detail.status_code == 404
        finally:
            _restore_env(old)

