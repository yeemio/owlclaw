"""Unit tests for console mount helper."""

from __future__ import annotations

from starlette.applications import Starlette
from starlette.testclient import TestClient

import owlclaw.web.mount as mount_module


def test_mount_console_returns_false_when_static_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(mount_module, "STATIC_DIR", tmp_path / "missing")
    app = Starlette()
    mounted = mount_module.mount_console(app)
    assert mounted is False


def test_mount_console_mounts_api_and_spa_fallback(tmp_path, monkeypatch) -> None:
    static_dir = tmp_path / "static"
    static_dir.mkdir(parents=True)
    (static_dir / "index.html").write_text("<html><body>console</body></html>", encoding="utf-8")
    monkeypatch.setattr(mount_module, "STATIC_DIR", static_dir)

    app = Starlette()
    mounted = mount_module.mount_console(app)
    assert mounted is True

    client = TestClient(app)
    root = client.get("/", follow_redirects=False)
    assert root.status_code in {307, 308}
    assert root.headers["location"] == "/console/"

    html = client.get("/console/")
    assert html.status_code == 200
    assert "console" in html.text

    fallback = client.get("/console/agents/agent-1")
    assert fallback.status_code == 200
    assert "console" in fallback.text
