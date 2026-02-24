"""Tests for CLI API/index hybrid client."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request

from owlclaw.cli.api_client import SkillHubApiClient
from owlclaw.owlhub import OwlHubClient
from tests.unit.test_owlhub_cli_client import _build_index_file, _build_skill_archive


class _FakeResponse:
    def __init__(self, payload: str):
        self._payload = payload.encode("utf-8")

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_api_mode_search_uses_remote_endpoint(tmp_path: Path, monkeypatch) -> None:
    archive = _build_skill_archive(tmp_path, name="entry-monitor", publisher="acme", version="1.0.0")
    index_file = _build_index_file(tmp_path, archive, name="entry-monitor", publisher="acme", version="1.0.0")
    index_client = OwlHubClient(index_url=str(index_file), install_dir=tmp_path / "skills", lock_file=tmp_path / "lock.json")

    def fake_urlopen(request: Request, timeout: int):  # noqa: ARG001
        assert request.full_url.startswith("http://hub.local/api/v1/skills")
        payload = {
            "total": 1,
            "page": 1,
            "page_size": 20,
            "items": [
                {
                    "name": "entry-monitor",
                    "publisher": "acme",
                    "version": "1.0.1",
                    "description": "remote",
                    "tags": ["x"],
                    "version_state": "released",
                }
            ],
        }
        return _FakeResponse(json.dumps(payload))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = SkillHubApiClient(index_client=index_client, api_base_url="http://hub.local", mode="api")
    results = client.search(query="entry")
    assert len(results) == 1
    assert results[0].version == "1.0.1"


def test_auto_mode_falls_back_to_index_when_api_unavailable(tmp_path: Path, monkeypatch) -> None:
    archive = _build_skill_archive(tmp_path, name="entry-monitor", publisher="acme", version="1.0.0")
    index_file = _build_index_file(tmp_path, archive, name="entry-monitor", publisher="acme", version="1.0.0")
    index_client = OwlHubClient(index_url=str(index_file), install_dir=tmp_path / "skills", lock_file=tmp_path / "lock.json")

    def fail_urlopen(request: Request, timeout: int):  # noqa: ARG001
        raise URLError("offline")

    monkeypatch.setattr("urllib.request.urlopen", fail_urlopen)
    client = SkillHubApiClient(index_client=index_client, api_base_url="http://hub.local", mode="auto")
    results = client.search(query="entry")
    assert len(results) == 1
    assert results[0].version == "1.0.0"


def test_publish_uses_token_and_sends_manifest_payload(tmp_path: Path, monkeypatch) -> None:
    archive = _build_skill_archive(tmp_path, name="entry-monitor", publisher="acme", version="1.0.0")
    index_file = _build_index_file(tmp_path, archive, name="entry-monitor", publisher="acme", version="1.0.0")
    index_client = OwlHubClient(index_url=str(index_file), install_dir=tmp_path / "skills", lock_file=tmp_path / "lock.json")

    skill_dir = tmp_path / "publish-skill"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: "entry-monitor"
publisher: "acme"
description: "entry monitor skill"
license: "MIT"
metadata:
  version: "1.0.0"
---
# entry-monitor
""",
        encoding="utf-8",
    )
    called = {"auth": "", "name": ""}

    def fake_urlopen(request: Request, timeout: int):  # noqa: ARG001
        called["auth"] = request.headers.get("Authorization", "")
        body = json.loads((request.data or b"{}").decode("utf-8"))
        called["name"] = body.get("skill_name", "")
        return _FakeResponse(json.dumps({"accepted": True, "review_id": "r1", "status": "pending"}))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = SkillHubApiClient(
        index_client=index_client,
        api_base_url="http://hub.local",
        api_token="token-123",
        mode="api",
    )
    response = client.publish(skill_path=skill_dir)
    assert called["auth"] == "Bearer token-123"
    assert called["name"] == "entry-monitor"
    assert response["review_id"] == "r1"
