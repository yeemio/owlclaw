"""FastAPI application factory for OwlHub."""

from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from owlclaw.owlhub.api.audit import AuditLogger, create_audit_router
from owlclaw.owlhub.api.auth import (
    AuthManager,
    Principal,
    create_auth_router,
    enforce_write_auth,
    get_current_principal,
)
from owlclaw.owlhub.api.routes.blacklist import router as blacklist_router
from owlclaw.owlhub.api.routes.reviews import router as reviews_router
from owlclaw.owlhub.api.routes.skills import router as skills_router
from owlclaw.owlhub.api.routes.statistics import router as statistics_router
from owlclaw.owlhub.models import BlacklistManager
from owlclaw.owlhub.review import ReviewSystem
from owlclaw.owlhub.statistics import StatisticsTracker
from owlclaw.owlhub.validator import Validator

current_principal_type = Annotated[Principal, Depends(get_current_principal)]
logger = logging.getLogger(__name__)


def _resolve_log_level() -> int:
    level_name = os.getenv("OWLHUB_LOG_LEVEL", "INFO").strip().upper()
    level = getattr(logging, level_name, logging.INFO)
    return int(level)


def _log_json(level: int, event: str, **fields: object) -> None:
    if not logger.isEnabledFor(level):
        return
    payload = {"event": event, **fields}
    logger.log(level, "%s", json.dumps(payload, ensure_ascii=False, sort_keys=True))


def create_app() -> FastAPI:
    """Create FastAPI app with basic middleware and health endpoint."""
    app = FastAPI(
        title="OwlHub API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    validator = Validator()
    review_dir = Path(os.getenv("OWLHUB_REVIEW_DIR", "./.owlhub/reviews")).resolve()
    statistics_db = Path(os.getenv("OWLHUB_STATISTICS_DB", "./.owlhub/skill_statistics.json")).resolve()
    blacklist_db = Path(os.getenv("OWLHUB_BLACKLIST_DB", "./.owlhub/blacklist.json")).resolve()
    app.state.validator = validator
    app.state.review_system = ReviewSystem(storage_dir=review_dir, validator=validator)
    app.state.audit_logger = AuditLogger()
    app.state.statistics_tracker = StatisticsTracker(storage_path=statistics_db)
    app.state.blacklist_manager = BlacklistManager(path=blacklist_db)
    app.state.auth_manager = AuthManager()
    app.state.log_level = _resolve_log_level()

    @app.middleware("http")
    async def authz_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        started = time.perf_counter()
        method = request.method
        path = request.url.path
        try:
            enforce_write_auth(request)
        except HTTPException as exc:
            _log_json(
                app.state.log_level,
                "api_request",
                method=method,
                path=path,
                status_code=exc.status_code,
                duration_ms=round((time.perf_counter() - started) * 1000.0, 3),
            )
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "Unhandled API exception: %s",
                json.dumps({"event": "api_request_error", "method": method, "path": path}, ensure_ascii=False),
            )
            raise
        _log_json(
            app.state.log_level,
            "api_request",
            method=method,
            path=path,
            status_code=response.status_code,
            duration_ms=round((time.perf_counter() - started) * 1000.0, 3),
        )
        return response

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/v1/skills/publish-probe")
    def publish_probe(principal: current_principal_type) -> dict[str, str]:
        return {"status": "accepted", "user_id": principal.user_id, "role": principal.role}

    app.include_router(create_auth_router(app.state.auth_manager))
    app.include_router(blacklist_router)
    app.include_router(skills_router)
    app.include_router(reviews_router)
    app.include_router(statistics_router)
    app.include_router(create_audit_router(app.state.audit_logger))

    return app
