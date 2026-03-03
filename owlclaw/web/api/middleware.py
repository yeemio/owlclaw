"""API middleware and exception handlers for console backend."""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response


class TokenAuthMiddleware(BaseHTTPMiddleware):
    """Bearer token auth middleware for console API."""

    def __init__(
        self,
        app: FastAPI,
        *,
        token_env: str = "OWLCLAW_CONSOLE_API_TOKEN",
        legacy_token_env: str = "OWLCLAW_CONSOLE_TOKEN",
        exempt_paths: set[str] | None = None,
    ) -> None:
        super().__init__(app)
        self._token_env = token_env
        self._legacy_token_env = legacy_token_env
        self._exempt_paths = exempt_paths or set()

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.method.upper() == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        if path in self._exempt_paths:
            return await call_next(request)

        expected_token = os.getenv(self._token_env, "").strip()
        if not expected_token:
            expected_token = os.getenv(self._legacy_token_env, "").strip()
        if not expected_token:
            return await call_next(request)

        api_token_header = request.headers.get("x-api-token", "").strip()
        if api_token_header == expected_token:
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "code": "UNAUTHORIZED",
                        "message": "Missing bearer token.",
                    },
                },
            )

        provided_token = auth_header[7:].strip()
        if provided_token != expected_token:
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "code": "UNAUTHORIZED",
                        "message": "Invalid token.",
                    },
                },
            )
        return await call_next(request)


def parse_cors_origins(raw_origins: str | None) -> list[str]:
    """Parse comma-separated CORS origins env value."""
    if raw_origins is None:
        return ["http://localhost:3000"]
    parts = [item.strip() for item in raw_origins.split(",")]
    origins = [item for item in parts if item]
    return origins or ["http://localhost:3000"]


def add_cors_middleware(app: FastAPI) -> None:
    """Attach CORS middleware using env-driven configuration."""
    origins = parse_cors_origins(os.getenv("OWLCLAW_CONSOLE_CORS_ORIGINS"))
    allow_credentials = "*" not in origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers using unified error shape."""

    @app.exception_handler(HTTPException)
    async def handle_http_exception(_: Request, exc: HTTPException) -> JSONResponse:
        code = "HTTP_ERROR"
        if exc.status_code == 404:
            code = "NOT_FOUND"
        elif exc.status_code == 401:
            code = "UNAUTHORIZED"
        elif exc.status_code == 403:
            code = "FORBIDDEN"
        elif exc.status_code == 422:
            code = "VALIDATION_ERROR"
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": code,
                    "message": str(exc.detail),
                },
            },
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed.",
                    "details": {"errors": exc.errors()},
                },
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "Unexpected server error.",
                    "details": {"type": exc.__class__.__name__},
                },
            },
        )
