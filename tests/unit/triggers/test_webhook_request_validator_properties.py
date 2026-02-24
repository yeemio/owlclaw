from __future__ import annotations

import asyncio
import hashlib
import hmac
from uuid import UUID

from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.triggers.webhook import (
    AuthMethod,
    EndpointConfig,
    HttpRequest,
    RequestValidator,
    WebhookEndpointManager,
)
from owlclaw.triggers.webhook.persistence.repositories import InMemoryEndpointRepository


@given(
    token=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_", min_size=1, max_size=32),
    body=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789{}:_-, ", min_size=0, max_size=48),
    use_valid_token=st.booleans(),
)
@settings(max_examples=40, deadline=None)
def test_property_auth_token_validation_and_error_response(
    token: str,
    body: str,
    use_valid_token: bool,
) -> None:
    """Feature: triggers-webhook, Property 5: 认证令牌验证和错误响应."""

    async def _run() -> None:
        manager = WebhookEndpointManager(InMemoryEndpointRepository())
        endpoint = await manager.create_endpoint(
            EndpointConfig(name="orders", target_agent_id="agent-1", auth_method=AuthMethod(type="bearer", token=token))
        )
        validator = RequestValidator(manager)
        provided = token if use_valid_token else f"{token}-invalid"
        request = HttpRequest(
            headers={
                "Authorization": f"Bearer {provided}",
                "Content-Type": "application/json",
            },
            body=body,
        )
        _, result = await validator.validate_request(endpoint.id, request)
        assert result.valid is use_valid_token
        if not use_valid_token:
            assert result.error is not None
            assert result.error.status_code == 401

    asyncio.run(_run())


@given(
    secret=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_", min_size=1, max_size=32),
    payload=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789{}:_-, ", min_size=0, max_size=48),
    algorithm=st.sampled_from(["sha256", "sha512"]),
    use_valid_signature=st.booleans(),
)
@settings(max_examples=40, deadline=None)
def test_property_signature_validation_and_error_response(
    secret: str,
    payload: str,
    algorithm: str,
    use_valid_signature: bool,
) -> None:
    """Feature: triggers-webhook, Property 6: 签名验证和错误响应."""

    async def _run() -> None:
        manager = WebhookEndpointManager(InMemoryEndpointRepository())
        endpoint = await manager.create_endpoint(
            EndpointConfig(
                name="secure",
                target_agent_id="agent-2",
                auth_method=AuthMethod(type="hmac", secret=secret, algorithm=algorithm),
            )
        )
        validator = RequestValidator(manager)
        hasher = hashlib.sha256 if algorithm == "sha256" else hashlib.sha512
        digest = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hasher).hexdigest()
        signature = digest if use_valid_signature else f"{digest}x"
        request = HttpRequest(
            headers={
                "Content-Type": "application/json",
                "X-Signature": f"{algorithm}={signature}",
            },
            body=payload,
        )
        _, result = await validator.validate_request(endpoint.id, request)
        assert result.valid is use_valid_signature
        if not use_valid_signature:
            assert result.error is not None
            assert result.error.status_code == 403

    asyncio.run(_run())


@given(endpoint_id=st.uuids())
@settings(max_examples=30, deadline=None)
def test_property_unknown_endpoint_returns_404(endpoint_id: UUID) -> None:
    """Feature: triggers-webhook, Property 7: 未知端点返回 404."""

    async def _run() -> None:
        manager = WebhookEndpointManager(InMemoryEndpointRepository())
        validator = RequestValidator(manager)
        request = HttpRequest(
            headers={
                "Authorization": "Bearer any",
                "Content-Type": "application/json",
            },
            body="{}",
        )
        _, result = await validator.validate_request(str(endpoint_id), request)
        assert not result.valid
        assert result.error is not None
        assert result.error.code == "ENDPOINT_NOT_FOUND"
        assert result.error.status_code == 404

    asyncio.run(_run())
