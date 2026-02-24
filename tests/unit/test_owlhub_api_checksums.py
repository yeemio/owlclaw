"""Checksum validation and generation tests for OwlHub publish API."""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi.testclient import TestClient

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


def _issue_token(client: TestClient, *, code: str = "gho_acme1111", role: str = "publisher") -> str:
    response = client.post("/api/v1/auth/token", json={"github_code": code, "role": role})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_publish_generates_checksum_from_local_package_when_missing(tmp_path: Path) -> None:
    old = _prepare_env(tmp_path)
    try:
        archive = _build_skill_archive(tmp_path, name="sum-skill", publisher="acme1111", version="1.0.0")
        expected = IndexBuilder().calculate_checksum(archive)
        client = TestClient(create_app())
        token = _issue_token(client)
        response = client.post(
            "/api/v1/skills",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "publisher": "acme1111",
                "skill_name": "sum-skill",
                "version": "1.0.0",
                "metadata": {
                    "description": "checksum test",
                    "license": "MIT",
                    "download_url": str(archive),
                },
            },
        )
        assert response.status_code == 200
        payload = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
        assert payload["skills"][0]["checksum"] == expected
    finally:
        _restore_env(old)


def test_publish_rejects_mismatched_checksum_for_local_package(tmp_path: Path) -> None:
    old = _prepare_env(tmp_path)
    try:
        archive = _build_skill_archive(tmp_path, name="sum-skill", publisher="acme1111", version="1.0.0")
        client = TestClient(create_app())
        token = _issue_token(client)
        response = client.post(
            "/api/v1/skills",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "publisher": "acme1111",
                "skill_name": "sum-skill",
                "version": "1.0.0",
                "metadata": {
                    "description": "checksum test",
                    "license": "MIT",
                    "download_url": str(archive),
                    "checksum": "sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
                },
            },
        )
        assert response.status_code == 422
        assert "checksum does not match package content" in response.text
    finally:
        _restore_env(old)


def test_publish_rejects_remote_package_without_checksum(tmp_path: Path) -> None:
    old = _prepare_env(tmp_path)
    try:
        client = TestClient(create_app())
        token = _issue_token(client)
        response = client.post(
            "/api/v1/skills",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "publisher": "acme1111",
                "skill_name": "sum-skill",
                "version": "1.0.0",
                "metadata": {
                    "description": "checksum test",
                    "license": "MIT",
                    "download_url": "https://example.com/sum-skill-1.0.0.tar.gz",
                },
            },
        )
        assert response.status_code == 422
        assert "checksum is required" in response.text
    finally:
        _restore_env(old)


def test_publish_generates_manifest_checksum_without_download_url(tmp_path: Path) -> None:
    old = _prepare_env(tmp_path)
    try:
        client = TestClient(create_app())
        token = _issue_token(client)
        response = client.post(
            "/api/v1/skills",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "publisher": "acme1111",
                "skill_name": "manifest-skill",
                "version": "1.0.0",
                "metadata": {
                    "description": "manifest checksum test",
                    "license": "MIT",
                },
            },
        )
        assert response.status_code == 200
        payload = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
        checksum = payload["skills"][0]["checksum"]
        assert checksum.startswith("sha256:")
        assert len(checksum) == 71
    finally:
        _restore_env(old)
