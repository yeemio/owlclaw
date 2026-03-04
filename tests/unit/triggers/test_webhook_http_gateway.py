from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi.testclient import TestClient

from owlclaw.triggers.webhook import (
    EventLogger,
    ExecutionTrigger,
    GovernanceClient,
    HttpGatewayConfig,
    MonitoringService,
    PayloadTransformer,
    RequestValidator,
    WebhookEndpointManager,
    create_webhook_app,
)
from owlclaw.triggers.webhook.persistence.repositories import InMemoryEndpointRepository, InMemoryEventRepository


@dataclass
class _Runtime:
    async def trigger(self, input_data: Any) -> dict[str, Any]:  # noqa: ARG002
        return {"execution_id": "exec-http-1", "status": "completed", "output": {"ok": True}}


class _AllowPolicy:
    async def check_permission(self, context: Any) -> dict[str, Any]:  # noqa: ARG002
        return {"allowed": True}

    async def check_rate_limit(self, context: Any) -> dict[str, Any]:  # noqa: ARG002
        return {"allowed": True}


def _create_client(
    *,
    per_ip_limit: int = 100,
    admin_token: str | None = "admin-secret",
    max_content_length_bytes: int = 1_048_576,
) -> TestClient:
    manager = WebhookEndpointManager(InMemoryEndpointRepository())
    app = create_webhook_app(
        manager=manager,
        validator=RequestValidator(manager),
        transformer=PayloadTransformer(),
        governance=GovernanceClient(_AllowPolicy()),
        execution=ExecutionTrigger(_Runtime()),
        event_logger=EventLogger(InMemoryEventRepository()),
        monitoring=MonitoringService(),
        config=HttpGatewayConfig(
            per_ip_limit_per_minute=per_ip_limit,
            per_endpoint_limit_per_minute=per_ip_limit,
            admin_token=admin_token,
            max_content_length_bytes=max_content_length_bytes,
        ),
    )
    return TestClient(app)


def _create_endpoint(client: TestClient, *, admin_token: str | None = "admin-secret") -> tuple[str, str]:
    payload = {
        "name": "orders",
        "target_agent_id": "agent-1",
        "auth_method": {"type": "bearer", "token": "token-abc"},
        "execution_mode": "async",
    }
    headers = {"Authorization": f"Bearer {admin_token}"} if admin_token else {}
    resp = client.post("/endpoints", json=payload, headers=headers)
    assert resp.status_code == 201
    endpoint_id = resp.json()["id"]
    return endpoint_id, "token-abc"


def test_http_gateway_full_request_flow() -> None:
    client = _create_client()
    endpoint_id, token = _create_endpoint(client)
    resp = client.post(
        f"/webhooks/{endpoint_id}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"order_id": "o-1"},
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["execution_id"] == "exec-http-1"
    assert "timestamp" in body


def test_http_gateway_error_scenarios() -> None:
    client = _create_client()
    endpoint_id, _token = _create_endpoint(client)

    unauthorized = client.post(
        f"/webhooks/{endpoint_id}",
        headers={"Authorization": "Bearer wrong", "Content-Type": "application/json"},
        json={"x": 1},
    )
    assert unauthorized.status_code == 401

    bad_payload = client.post(
        f"/webhooks/{endpoint_id}",
        headers={"Authorization": "Bearer token-abc", "Content-Type": "application/json"},
        data="{bad-json",
    )
    assert bad_payload.status_code == 400

    not_found = client.post(
        "/webhooks/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": "Bearer token-abc", "Content-Type": "application/json"},
        json={"x": 1},
    )
    assert not_found.status_code == 404


def test_http_gateway_rate_limit() -> None:
    client = _create_client(per_ip_limit=1)
    endpoint_id, token = _create_endpoint(client)

    first = client.post(
        f"/webhooks/{endpoint_id}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"x": 1},
    )
    second = client.post(
        f"/webhooks/{endpoint_id}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"x": 2},
    )

    assert first.status_code == 202
    assert second.status_code == 429


def test_management_endpoints_require_admin_token() -> None:
    client = _create_client(admin_token="admin-secret")
    payload = {
        "name": "orders",
        "target_agent_id": "agent-1",
        "auth_method": {"type": "bearer", "token": "token-abc"},
        "execution_mode": "async",
    }
    unauthorized = client.post("/endpoints", json=payload)
    assert unauthorized.status_code == 401

    forbidden = client.post("/endpoints", json=payload, headers={"Authorization": "Bearer wrong"})
    assert forbidden.status_code == 401

    authorized = client.post("/endpoints", json=payload, headers={"Authorization": "Bearer admin-secret"})
    assert authorized.status_code == 201


def test_management_endpoints_return_500_when_admin_token_not_configured() -> None:
    client = _create_client(admin_token=None)
    payload = {
        "name": "orders",
        "target_agent_id": "agent-1",
        "auth_method": {"type": "bearer", "token": "token-abc"},
        "execution_mode": "async",
    }
    response = client.post("/endpoints", json=payload)
    assert response.status_code == 500


def test_webhook_request_body_too_large_returns_413() -> None:
    client = _create_client(max_content_length_bytes=16)
    endpoint_id, token = _create_endpoint(client)
    oversized = client.post(
        f"/webhooks/{endpoint_id}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        data='{"value":"this payload is too large"}',
    )
    assert oversized.status_code == 413


def test_http_gateway_config_default_cors_origins_is_closed() -> None:
    cfg = HttpGatewayConfig()
    assert cfg.cors_origins == []
