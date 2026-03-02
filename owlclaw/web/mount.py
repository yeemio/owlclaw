"""Console mount helpers for Starlette/FastAPI hosts."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, MutableMapping

from starlette.applications import Starlette
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, RedirectResponse, Response
from starlette.staticfiles import StaticFiles

from owlclaw.web.app import create_console_app

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


class SPAStaticFiles(StaticFiles):
    """Static files app with SPA fallback to index.html for unknown paths."""

    async def get_response(self, path: str, scope: MutableMapping[str, Any]) -> Response:
        try:
            response = await super().get_response(path, scope)
            if response.status_code != 404:
                return response
        except StarletteHTTPException as exc:
            if exc.status_code != 404:
                raise
        index_file = Path(self.directory) / "index.html"  # type: ignore[arg-type]
        return FileResponse(index_file)


class _RootRedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        if request.url.path == "/":
            return RedirectResponse(url="/console/")
        return await call_next(request)


class _RestorePrefixApp:
    """Re-attach stripped mount prefix before delegating to sub-app."""

    def __init__(self, app, prefix: str) -> None:  # type: ignore[no-untyped-def]
        self._app = app
        self._prefix = prefix

    async def __call__(self, scope, receive, send):  # type: ignore[no-untyped-def]
        if scope["type"] in {"http", "websocket"}:
            patched = dict(scope)
            patched["path"] = f"{self._prefix}{scope['path']}"
            return await self._app(patched, receive, send)
        return await self._app(scope, receive, send)


def mount_console(app: Starlette) -> bool:
    """Mount console API + static frontend. Return True when mounted."""
    index_html = STATIC_DIR / "index.html"
    if not index_html.exists():
        logger.info("Console static files not found at %s, skip mounting", STATIC_DIR)
        return False

    app.mount("/api/v1", _RestorePrefixApp(create_console_app(), "/api/v1"))
    app.mount("/console", SPAStaticFiles(directory=str(STATIC_DIR), html=True), name="console-static")
    app.add_middleware(_RootRedirectMiddleware)
    logger.info("Console mounted (api=/api/v1, ui=/console/)")
    return True
