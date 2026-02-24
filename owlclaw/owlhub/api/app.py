"""FastAPI application factory for OwlHub."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from owlclaw.owlhub.api.routes.skills import router as skills_router


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

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(skills_router)

    return app
