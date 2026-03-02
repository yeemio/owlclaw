"""End-to-end console integration checks."""

from __future__ import annotations

from starlette.applications import Starlette
from starlette.testclient import TestClient

import owlclaw.web.mount as mount_module


def test_console_integration_mount_and_api_coexist(tmp_path, monkeypatch) -> None:
    static_dir = tmp_path / "static"
    static_dir.mkdir(parents=True)
    (static_dir / "index.html").write_text("<html><body>console</body></html>", encoding="utf-8")
    monkeypatch.setattr(mount_module, "STATIC_DIR", static_dir)

    app = Starlette()
    mounted = mount_module.mount_console(app)
    assert mounted is True

    client = TestClient(app)
    assert client.get("/console/").status_code == 200
    assert client.get("/api/v1/health").status_code == 200


def test_console_integration_graceful_degrade_when_static_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(mount_module, "STATIC_DIR", tmp_path / "missing")
    app = Starlette()
    mounted = mount_module.mount_console(app)
    assert mounted is False
    client = TestClient(app)
    assert client.get("/console/").status_code == 404

