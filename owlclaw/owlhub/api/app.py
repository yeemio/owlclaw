"""FastAPI application factory for OwlHub."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from owlclaw.owlhub.api.schemas import SkillSearchResponse


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

    @app.get("/api/v1/skills", response_model=SkillSearchResponse)
    def list_skills(page: int = 1, page_size: int = 20) -> SkillSearchResponse:
        return SkillSearchResponse(total=0, page=page, page_size=page_size, items=[])

    return app
