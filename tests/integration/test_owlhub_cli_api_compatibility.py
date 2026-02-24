"""Integration compatibility test for CLI index mode and API mode."""

from __future__ import annotations

import json
from pathlib import Path
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


def test_property_26_cli_api_backward_compatibility(tmp_path: Path, monkeypatch) -> None:
    """Property 26: API mode search stays compatible with index mode search."""
    archive = _build_skill_archive(tmp_path, name="phase3-monitor", publisher="acme", version="1.0.0")
    index_file = _build_index_file(tmp_path, archive, name="phase3-monitor", publisher="acme", version="1.0.0")
    index_client = OwlHubClient(index_url=str(index_file), install_dir=tmp_path / "skills", lock_file=tmp_path / "lock.json")
    expected = SkillHubApiClient(index_client=index_client, mode="index").search(query="phase3")
    assert len(expected) == 1

    def fake_urlopen(request: Request, timeout: int):  # noqa: ARG001
        if request.full_url.endswith("/api/v1/skills?query=phase3&tags="):
            payload = {
                "total": 1,
                "page": 1,
                "page_size": 20,
                "items": [
                    {
                        "name": "phase3-monitor",
                        "publisher": "acme",
                        "version": "1.0.0",
                        "description": "phase3-monitor description",
                        "tags": ["demo"],
                        "version_state": "released",
                    }
                ],
            }
            return _FakeResponse(json.dumps(payload))
        raise AssertionError(f"unexpected url: {request.full_url}")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    api_client = SkillHubApiClient(index_client=index_client, api_base_url="http://hub.local", mode="api")
    actual = api_client.search(query="phase3")
    assert len(actual) == len(expected)
    assert actual[0].name == expected[0].name
    assert actual[0].version == expected[0].version
