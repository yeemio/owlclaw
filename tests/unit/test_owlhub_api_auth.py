"""Unit and property tests for OwlHub API authentication."""

from __future__ import annotations

from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.owlhub.api import create_app


def _issue_token(client: TestClient, *, code: str = "gho_demo1234", role: str = "publisher") -> str:
    response = client.post("/api/v1/auth/token", json={"github_code": code, "role": role})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_oauth2_flow_with_valid_credentials() -> None:
    client = TestClient(create_app())
    response = client.post("/api/v1/auth/token", json={"github_code": "gho_abcd1234", "role": "publisher"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]


def test_jwt_token_validation_via_me_endpoint() -> None:
    client = TestClient(create_app())
    token = _issue_token(client)
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["auth_type"] == "bearer"


def test_api_key_authentication_flow() -> None:
    client = TestClient(create_app())
    token = _issue_token(client)
    key_response = client.post("/api/v1/auth/api-keys", headers={"Authorization": f"Bearer {token}"})
    assert key_response.status_code == 200
    api_key = key_response.json()["api_key"]
    me = client.get("/api/v1/auth/me", headers={"X-API-Key": api_key})
    assert me.status_code == 200
    assert me.json()["auth_type"] == "api_key"


def test_unauthorized_write_access_rejected() -> None:
    client = TestClient(create_app())
    response = client.post("/api/v1/skills/publish-probe", json={"name": "demo"})
    assert response.status_code == 401


@settings(max_examples=10, deadline=None)
@given(
    payload=st.dictionaries(
        keys=st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=8),
        values=st.one_of(st.text(min_size=0, max_size=12), st.integers(min_value=0, max_value=100)),
        max_size=5,
    )
)
def test_property_14_authentication_protection(payload: dict[str, object]) -> None:
    """Property 14: unauthenticated publish requests are rejected."""
    client = TestClient(create_app())
    response = client.post("/api/v1/skills/publish-probe", json=payload)
    assert response.status_code == 401

