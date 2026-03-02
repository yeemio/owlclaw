from __future__ import annotations

from pathlib import Path

from starlette.applications import Starlette
from starlette.testclient import TestClient

from owlclaw.web import mount as web_mount


def test_console_degrades_gracefully_without_static(tmp_path: Path, monkeypatch) -> None:
    missing = tmp_path / "missing"
    monkeypatch.setattr(web_mount, "STATIC_DIR", missing)
    app = Starlette()

    mounted = web_mount.mount_console(app)
    client = TestClient(app)

    assert mounted is False
    assert client.get("/").status_code == 404

