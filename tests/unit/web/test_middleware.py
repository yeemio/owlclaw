"""Tests for console API middleware and auth behavior."""

from __future__ import annotations

from fastapi.testclient import TestClient

from owlclaw.web import create_console_app


def test_overview_without_token_env_returns_200(monkeypatch) -> None:
    monkeypatch.delenv("OWLCLAW_CONSOLE_TOKEN", raising=False)
    app = create_console_app()
    client = TestClient(app)

    response = client.get("/api/v1/overview")
    assert response.status_code == 200


def test_overview_requires_token_when_configured(monkeypatch) -> None:
    monkeypatch.setenv("OWLCLAW_CONSOLE_TOKEN", "secret-token")
    app = create_console_app()
    client = TestClient(app)

    response = client.get("/api/v1/overview")
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "UNAUTHORIZED"


def test_overview_accepts_valid_token(monkeypatch) -> None:
    monkeypatch.setenv("OWLCLAW_CONSOLE_TOKEN", "secret-token")
    app = create_console_app()
    client = TestClient(app)

    response = client.get(
        "/api/v1/overview",
        headers={"Authorization": "Bearer secret-token"},
    )
    assert response.status_code == 200
    assert "total_cost_today" in response.json()


def test_openapi_is_public_even_when_auth_enabled(monkeypatch) -> None:
    monkeypatch.setenv("OWLCLAW_CONSOLE_TOKEN", "secret-token")
    app = create_console_app()
    client = TestClient(app)

    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200

