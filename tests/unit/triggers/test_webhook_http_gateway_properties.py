from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.triggers.webhook import (
    EventLogger,
    ExecutionTrigger,
    GovernanceClient,
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
        return {"execution_id": "exec-prop-http", "status": "completed"}


class _AllowPolicy:
    async def check_permission(self, context: Any) -> dict[str, Any]:  # noqa: ARG002
        return {"allowed": True}

    async def check_rate_limit(self, context: Any) -> dict[str, Any]:  # noqa: ARG002
        return {"allowed": True}


def _client() -> TestClient:
    manager = WebhookEndpointManager(InMemoryEndpointRepository())
    app = create_webhook_app(
        manager=manager,
        validator=RequestValidator(manager),
        transformer=PayloadTransformer(),
        governance=GovernanceClient(_AllowPolicy()),
        execution=ExecutionTrigger(_Runtime()),
        event_logger=EventLogger(InMemoryEventRepository()),
        monitoring=MonitoringService(),
    )
    return TestClient(app)


def _create_endpoint(client: TestClient, token: str) -> str:
    resp = client.post(
        "/endpoints",
        json={
            "name": "orders",
            "target_agent_id": "agent-1",
            "auth_method": {"type": "bearer", "token": token},
            "execution_mode": "async",
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


@given(order_id=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-", min_size=1, max_size=20))
@settings(max_examples=20, deadline=None)
def test_property_success_start_returns_202(order_id: str) -> None:
    """Feature: triggers-webhook, Property 15: 成功启动返回 202."""

    client = _client()
    endpoint_id = _create_endpoint(client, "token-ok")
    resp = client.post(
        f"/webhooks/{endpoint_id}",
        headers={"Authorization": "Bearer token-ok", "Content-Type": "application/json"},
        json={"order_id": order_id},
    )
    assert resp.status_code == 202
    assert resp.json()["status"] in {"accepted", "completed"}


@given(case=st.sampled_from(["bad_payload", "bad_token", "missing_endpoint"]))
@settings(max_examples=20, deadline=None)
def test_property_error_handling_returns_appropriate_status_codes(case: str) -> None:
    """Feature: triggers-webhook, Property 16: 错误处理返回适当状态码."""

    client = _client()
    endpoint_id = _create_endpoint(client, "token-ok")
    if case == "bad_payload":
        resp = client.post(
            f"/webhooks/{endpoint_id}",
            headers={"Authorization": "Bearer token-ok", "Content-Type": "application/json"},
            data="{bad-json",
        )
        assert resp.status_code == 400
    elif case == "bad_token":
        resp = client.post(
            f"/webhooks/{endpoint_id}",
            headers={"Authorization": "Bearer bad", "Content-Type": "application/json"},
            json={"x": 1},
        )
        assert resp.status_code == 401
    else:
        resp = client.post(
            "/webhooks/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": "Bearer token-ok", "Content-Type": "application/json"},
            json={"x": 1},
        )
        assert resp.status_code == 404
