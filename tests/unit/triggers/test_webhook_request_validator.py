from __future__ import annotations

import base64
import hashlib
import hmac
from uuid import uuid4

import pytest

from owlclaw.triggers.webhook import (
    AuthMethod,
    EndpointConfig,
    HttpRequest,
    RequestValidator,
    WebhookEndpointManager,
)
from owlclaw.triggers.webhook.persistence.repositories import InMemoryEndpointRepository


async def _create_endpoint(manager: WebhookEndpointManager, auth_method: AuthMethod) -> str:
    endpoint = await manager.create_endpoint(
        EndpointConfig(name="orders", target_agent_id="agent-1", auth_method=auth_method)
    )
    return endpoint.id


@pytest.mark.asyncio
async def test_validator_rejects_invalid_bearer_token_formats() -> None:
    manager = WebhookEndpointManager(InMemoryEndpointRepository())
    endpoint_id = await _create_endpoint(manager, AuthMethod(type="bearer", token="top-secret"))
    validator = RequestValidator(manager)

    missing_scheme = HttpRequest(headers={"Authorization": "top-secret", "Content-Type": "application/json"}, body="{}")
    missing_token = HttpRequest(headers={"Authorization": "Bearer ", "Content-Type": "application/json"}, body="{}")
    wrong_token = HttpRequest(headers={"Authorization": "Bearer wrong", "Content-Type": "application/json"}, body="{}")

    for request in (missing_scheme, missing_token, wrong_token):
        _, result = await validator.validate_request(endpoint_id, request)
        assert not result.valid
        assert result.error is not None
        assert result.error.code == "INVALID_TOKEN"
        assert result.error.status_code == 401


@pytest.mark.asyncio
async def test_validator_handles_hmac_algorithm_edge_cases() -> None:
    manager = WebhookEndpointManager(InMemoryEndpointRepository())
    endpoint_id = await _create_endpoint(
        manager,
        AuthMethod(type="hmac", secret="s3cr3t", algorithm="sha256"),
    )
    validator = RequestValidator(manager)
    body = '{"ok":true}'
    request = HttpRequest(headers={"Content-Type": "application/json"}, body=body)

    _, missing_signature = await validator.validate_request(endpoint_id, request)
    assert not missing_signature.valid
    assert missing_signature.error is not None
    assert missing_signature.error.code == "MISSING_SIGNATURE"
    assert missing_signature.error.status_code == 403

    signature = hmac.new(b"s3cr3t", body.encode("utf-8"), hashlib.sha256).hexdigest()
    wrong_algo_prefix = HttpRequest(
        headers={
            "Content-Type": "application/json",
            "X-Signature": f"sha512={signature}",
        },
        body=body,
    )
    _, wrong_signature = await validator.validate_request(endpoint_id, wrong_algo_prefix)
    assert not wrong_signature.valid
    assert wrong_signature.error is not None
    assert wrong_signature.error.code == "INVALID_SIGNATURE"
    assert wrong_signature.error.status_code == 403


@pytest.mark.asyncio
async def test_validator_rejects_missing_request_headers() -> None:
    manager = WebhookEndpointManager(InMemoryEndpointRepository())
    endpoint_id = await _create_endpoint(manager, AuthMethod(type="bearer", token="abc123"))
    validator = RequestValidator(manager)

    _, result = await validator.validate_request(endpoint_id, HttpRequest(headers={}, body="{}"))
    assert not result.valid
    assert result.error is not None
    assert result.error.code == "INVALID_TOKEN"
    assert result.error.status_code == 401


@pytest.mark.asyncio
async def test_validator_accepts_basic_auth() -> None:
    manager = WebhookEndpointManager(InMemoryEndpointRepository())
    endpoint_id = await _create_endpoint(
        manager,
        AuthMethod(type="basic", username="owl", password="claw"),
    )
    validator = RequestValidator(manager)
    credentials = base64.b64encode(b"owl:claw").decode("utf-8")
    request = HttpRequest(
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
        },
        body="{}",
    )

    endpoint, result = await validator.validate_request(endpoint_id, request)
    assert result.valid
    assert endpoint is not None


@pytest.mark.asyncio
async def test_validator_returns_404_for_unknown_endpoint() -> None:
    manager = WebhookEndpointManager(InMemoryEndpointRepository())
    validator = RequestValidator(manager)
    unknown_id = str(uuid4())
    request = HttpRequest(headers={"Authorization": "Bearer token", "Content-Type": "application/json"}, body="{}")

    endpoint, result = await validator.validate_request(unknown_id, request)
    assert endpoint is None
    assert not result.valid
    assert result.error is not None
    assert result.error.code == "ENDPOINT_NOT_FOUND"
    assert result.error.status_code == 404
