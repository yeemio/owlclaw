from __future__ import annotations

from pathlib import Path

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.testclient import TestClient

from owlclaw.web import mount as web_mount


def test_mount_console_returns_false_when_static_missing(tmp_path: Path, monkeypatch) -> None:
    missing = tmp_path / "missing"
    monkeypatch.setattr(web_mount, "STATIC_DIR", missing)
    app = Starlette()

    mounted = web_mount.mount_console(app)

    assert mounted is False


def test_mount_console_mounts_routes_and_fallback(tmp_path: Path, monkeypatch) -> None:
    static_dir = tmp_path / "static"
    static_dir.mkdir(parents=True)
    (static_dir / "index.html").write_text("<html>console</html>", encoding="utf-8")
    assets_dir = static_dir / "assets"
    assets_dir.mkdir()
    (assets_dir / "file.js").write_text("console.log('ok')", encoding="utf-8")

    monkeypatch.setattr(web_mount, "STATIC_DIR", static_dir)

    api_app = Starlette()

    async def overview(_request):
        return JSONResponse({"status": "ok"})
    api_app.add_route("/overview", overview)

    app = Starlette()
    mounted = web_mount.mount_console(app, api_app=api_app)
    assert mounted is True

    client = TestClient(app)
    assert client.get("/", follow_redirects=False).status_code == 307
    assert client.get("/console/").status_code == 200
    assert client.get("/console/route/not-found").status_code == 200
    assert client.get("/api/v1/overview").json() == {"status": "ok"}


def test_load_console_api_app_returns_app(monkeypatch) -> None:
    monkeypatch.delenv("OWLCLAW_CONSOLE_TOKEN", raising=False)

    app = web_mount._load_console_api_app()

    assert app is not None
