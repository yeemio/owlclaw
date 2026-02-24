"""Security hardening tests for OwlHub API."""

from __future__ import annotations

from fastapi.testclient import TestClient

from owlclaw.owlhub.api import create_app


def _issue_token(client: TestClient, *, code: str = "gho_acme1111", role: str = "publisher") -> str:
    response = client.post("/api/v1/auth/token", json={"github_code": code, "role": role})
    assert response.status_code == 200
    token = response.json().get("access_token")
    assert isinstance(token, str)
    return token


def test_security_headers_are_attached_to_api_response() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "default-src 'none'" in response.headers["content-security-policy"]


def test_global_rate_limit_applies_to_anonymous_requests() -> None:
    app = create_app()
    app.state.auth_manager.rate_limit_per_window = 1
    app.state.auth_manager.rate_limit_window_seconds = 3600
    client = TestClient(app)
    first = client.get("/health")
    second = client.get("/health")
    assert first.status_code == 200
    assert second.status_code == 429


def test_form_write_request_requires_csrf_token() -> None:
    client = TestClient(create_app())
    response = client.post("/api/v1/auth/token", data={"github_code": "gho_abcd1234", "role": "publisher"})
    assert response.status_code == 403
    assert "csrf token required" in response.text


def test_publish_rejects_unsafe_skill_identifier() -> None:
    client = TestClient(create_app())
    token = _issue_token(client)
    response = client.post(
        "/api/v1/skills",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "publisher": "acme1111",
            "skill_name": "bad;drop-table",
            "version": "1.0.0",
            "metadata": {"description": "bad", "license": "MIT"},
        },
    )
    assert response.status_code == 422
    assert "invalid skill name format" in response.text
