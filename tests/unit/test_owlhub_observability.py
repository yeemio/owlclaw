"""Observability tests for OwlHub API and CLI logging."""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.error import URLError

from click.exceptions import Exit as ClickExit
from fastapi.testclient import TestClient

from owlclaw.cli import _dispatch_skill_command
from owlclaw.owlhub.api import create_app
from owlclaw.owlhub.api.routes.skills import _load_index
from tests.unit.test_owlhub_cli_client import _build_index_file, _build_skill_archive


def _prepare_index_env(root: Path) -> dict[str, str | None]:
    old = {key: os.getenv(key) for key in ("OWLHUB_INDEX_PATH", "OWLHUB_STATISTICS_DB")}
    payload = {
        "version": "1.0",
        "generated_at": "2026-02-24T00:00:00+00:00",
        "total_skills": 1,
        "skills": [
            {
                "manifest": {
                    "name": "entry-monitor",
                    "publisher": "acme",
                    "version": "1.0.0",
                    "description": "Entry monitor",
                    "license": "MIT",
                    "dependencies": {},
                    "tags": [],
                },
                "version_state": "released",
                "published_at": "2026-02-24T00:00:00+00:00",
                "updated_at": "2026-02-24T00:00:00+00:00",
                "statistics": {"total_downloads": 0, "downloads_last_30d": 0},
            }
        ],
    }
    index_path = root / "index.json"
    index_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    os.environ["OWLHUB_INDEX_PATH"] = str(index_path)
    os.environ["OWLHUB_STATISTICS_DB"] = str(root / "skill_statistics.json")
    _load_index.cache_clear()
    return old


def _restore_env(old: dict[str, str | None]) -> None:
    for key, value in old.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    _load_index.cache_clear()


def test_observability_health_and_metrics_endpoints(tmp_path: Path) -> None:
    old = _prepare_index_env(tmp_path)
    try:
        client = TestClient(create_app())
        health = client.get("/health")
        assert health.status_code == 200
        payload = health.json()
        assert payload["status"] == "ok"
        assert "checks" in payload
        assert "index" in payload["checks"]

        _ = client.get("/api/v1/skills")
        metrics = client.get("/metrics")
        assert metrics.status_code == 200
        assert "text/plain" in metrics.headers["content-type"]
        assert "# HELP owlhub_api_requests_total" in metrics.text
        assert "# TYPE owlhub_api_requests_total counter" in metrics.text
        assert "owlhub_api_requests_by_route_total" in metrics.text
    finally:
        _restore_env(old)


def test_observability_logging_output_format_for_api_requests(tmp_path: Path, caplog) -> None:
    old = _prepare_index_env(tmp_path)
    try:
        caplog.set_level("INFO")
        client = TestClient(create_app())
        response = client.get("/api/v1/skills")
        assert response.status_code == 200

        json_events = []
        for record in caplog.records:
            message = record.getMessage()
            if message.startswith("{") and message.endswith("}"):
                json_events.append(json.loads(message))
        assert any(event.get("event") == "api_request" for event in json_events)
        matched = [event for event in json_events if event.get("event") == "api_request"]
        assert any("duration_ms" in event and "path" in event and "method" in event for event in matched)
    finally:
        _restore_env(old)


def test_observability_error_logging_includes_context(tmp_path: Path, caplog, monkeypatch) -> None:
    old = _prepare_index_env(tmp_path)
    try:
        caplog.set_level("INFO")
        app = create_app()

        def broken_load_index() -> dict[str, object]:
            raise RuntimeError("boom")

        monkeypatch.setattr("owlclaw.owlhub.api.routes.skills._load_index", broken_load_index)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/v1/skills")
        assert response.status_code == 500
        assert "api_request_error" in caplog.text
        assert '"path": "/api/v1/skills"' in caplog.text
        assert '"method": "GET"' in caplog.text
    finally:
        _restore_env(old)


def test_observability_cli_error_logging_includes_context(tmp_path: Path, caplog, monkeypatch) -> None:
    archive = _build_skill_archive(tmp_path, name="entry-monitor", publisher="acme", version="1.0.0")
    _build_index_file(tmp_path, archive, name="entry-monitor", publisher="acme", version="1.0.0")
    skill_dir = tmp_path / "skill-publish"
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

    def fail_urlopen(*args, **kwargs):  # noqa: ANN002, ANN003
        _ = (args, kwargs)
        raise URLError("offline")

    monkeypatch.setattr("urllib.request.urlopen", fail_urlopen)
    monkeypatch.chdir(tmp_path)
    caplog.set_level("INFO")
    try:
        _dispatch_skill_command(
            [
                "skill",
                "publish",
                str(skill_dir),
                "--api-base-url",
                "http://hub.local",
                "--api-token",
                "token-123",
            ]
        )
        raise AssertionError("expected publish failure")
    except ClickExit:
        pass
    assert "skill_publish_error" in caplog.text
    assert '"mode": "api"' in caplog.text
