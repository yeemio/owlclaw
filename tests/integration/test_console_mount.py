"""Integration tests for console mount behavior."""

from __future__ import annotations

from starlette.applications import Starlette
from starlette.testclient import TestClient

import owlclaw.web.mount as mount_module


def test_console_mount_with_static_files(tmp_path, monkeypatch) -> None:
    static_dir = tmp_path / "static"
    static_dir.mkdir(parents=True)
    (static_dir / "index.html").write_text("<html><body>console ui</body></html>", encoding="utf-8")
    monkeypatch.setattr(mount_module, "STATIC_DIR", static_dir)

    app = Starlette()
    assert mount_module.mount_console(app) is True

    client = TestClient(app)
    assert client.get("/api/v1/overview").status_code != 404
    ui = client.get("/console/")
    assert ui.status_code == 200
    assert "console ui" in ui.text


def test_console_mount_without_static_files(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(mount_module, "STATIC_DIR", tmp_path / "not-found")
    app = Starlette()
    assert mount_module.mount_console(app) is False
