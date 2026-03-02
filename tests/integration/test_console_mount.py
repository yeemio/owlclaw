from __future__ import annotations

from pathlib import Path

from starlette.testclient import TestClient

from owlclaw.cli.start import create_start_app
from owlclaw.web import mount as web_mount


def test_start_app_mounts_console_when_static_exists(tmp_path: Path, monkeypatch) -> None:
    static_dir = tmp_path / "static"
    static_dir.mkdir(parents=True)
    (static_dir / "index.html").write_text("<html>console</html>", encoding="utf-8")
    monkeypatch.setattr(web_mount, "STATIC_DIR", static_dir)

    app = create_start_app()
    client = TestClient(app)
    assert client.get("/healthz").status_code == 200
    assert client.get("/console/").status_code == 200

