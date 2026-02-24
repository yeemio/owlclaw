"""FastAPI application factory for OwlHub."""

from __future__ import annotations

import os
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
from owlclaw.owlhub.api.routes.reviews import router as reviews_router
from owlclaw.owlhub.api.routes.skills import router as skills_router
from owlclaw.owlhub.api.routes.statistics import router as statistics_router
from owlclaw.owlhub.review import ReviewSystem
from owlclaw.owlhub.statistics import StatisticsTracker
from owlclaw.owlhub.validator import Validator

current_principal_type = Annotated[Principal, Depends(get_current_principal)]


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
    app.state.validator = validator
    app.state.review_system = ReviewSystem(storage_dir=review_dir, validator=validator)
    app.state.audit_logger = AuditLogger()
    app.state.statistics_tracker = StatisticsTracker(storage_path=statistics_db)
    app.state.auth_manager = AuthManager()

    @app.middleware("http")
    async def authz_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        try:
            enforce_write_auth(request)
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        return await call_next(request)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/v1/skills/publish-probe")
    def publish_probe(principal: current_principal_type) -> dict[str, str]:
        return {"status": "accepted", "user_id": principal.user_id, "role": principal.role}

    app.include_router(create_auth_router(app.state.auth_manager))
    app.include_router(skills_router)
    app.include_router(reviews_router)
    app.include_router(statistics_router)
    app.include_router(create_audit_router(app.state.audit_logger))

    return app
