"""Tests for console API middleware and auth behavior."""

from __future__ import annotations

import logging

from fastapi.testclient import TestClient

from owlclaw.web import create_console_app
from owlclaw.web.api.middleware import parse_cors_origins


def test_overview_without_token_env_returns_200(monkeypatch) -> None:
    monkeypatch.delenv("OWLCLAW_CONSOLE_API_TOKEN", raising=False)
    monkeypatch.delenv("OWLCLAW_CONSOLE_TOKEN", raising=False)
    monkeypatch.delenv("OWLCLAW_REQUIRE_AUTH", raising=False)
    app = create_console_app()
    client = TestClient(app)

    response = client.get("/api/v1/overview")
    assert response.status_code == 200


def test_overview_requires_token_when_configured(monkeypatch) -> None:
    monkeypatch.delenv("OWLCLAW_CONSOLE_API_TOKEN", raising=False)
    monkeypatch.setenv("OWLCLAW_CONSOLE_TOKEN", "secret-token")
    monkeypatch.delenv("OWLCLAW_REQUIRE_AUTH", raising=False)
    app = create_console_app()
    client = TestClient(app)

    response = client.get("/api/v1/overview")
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "UNAUTHORIZED"


def test_overview_accepts_valid_token(monkeypatch) -> None:
    monkeypatch.delenv("OWLCLAW_CONSOLE_API_TOKEN", raising=False)
    monkeypatch.setenv("OWLCLAW_CONSOLE_TOKEN", "secret-token")
    monkeypatch.delenv("OWLCLAW_REQUIRE_AUTH", raising=False)
    app = create_console_app()
    client = TestClient(app)

    response = client.get(
        "/api/v1/overview",
        headers={"Authorization": "Bearer secret-token"},
    )
    assert response.status_code == 200
    assert "total_cost_today" in response.json()


def test_openapi_is_public_even_when_auth_enabled(monkeypatch) -> None:
    monkeypatch.delenv("OWLCLAW_CONSOLE_API_TOKEN", raising=False)
    monkeypatch.setenv("OWLCLAW_CONSOLE_TOKEN", "secret-token")
    monkeypatch.delenv("OWLCLAW_REQUIRE_AUTH", raising=False)
    app = create_console_app()
    client = TestClient(app)

    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200


def test_overview_uses_console_api_token_env_and_x_api_token(monkeypatch) -> None:
    monkeypatch.setenv("OWLCLAW_CONSOLE_API_TOKEN", "api-token-1")
    monkeypatch.delenv("OWLCLAW_CONSOLE_TOKEN", raising=False)
    monkeypatch.delenv("OWLCLAW_REQUIRE_AUTH", raising=False)
    app = create_console_app()
    client = TestClient(app)

    unauthorized = client.get("/api/v1/overview")
    assert unauthorized.status_code == 401

    authorized = client.get("/api/v1/overview", headers={"X-API-Token": "api-token-1"})
    assert authorized.status_code == 200


def test_parse_cors_origins_uses_localhost_default() -> None:
    assert parse_cors_origins(None) == ["http://localhost:3000"]
    assert parse_cors_origins("") == ["http://localhost:3000"]


def test_overview_returns_500_when_require_auth_enabled_without_token(monkeypatch) -> None:
    monkeypatch.delenv("OWLCLAW_CONSOLE_API_TOKEN", raising=False)
    monkeypatch.delenv("OWLCLAW_CONSOLE_TOKEN", raising=False)
    monkeypatch.setenv("OWLCLAW_REQUIRE_AUTH", "true")
    app = create_console_app()
    client = TestClient(app)

    response = client.get("/api/v1/overview")
    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "AUTH_NOT_CONFIGURED"
    assert body["error"]["message"] == "auth not configured"


def test_auth_middleware_logs_warning_when_token_empty(monkeypatch, caplog) -> None:
    monkeypatch.delenv("OWLCLAW_CONSOLE_API_TOKEN", raising=False)
    monkeypatch.delenv("OWLCLAW_CONSOLE_TOKEN", raising=False)
    monkeypatch.delenv("OWLCLAW_REQUIRE_AUTH", raising=False)
    with caplog.at_level(logging.WARNING):
        app = create_console_app()
        client = TestClient(app)
        client.get("/api/v1/overview")
    assert any("Console API token is empty" in rec.message for rec in caplog.records)
