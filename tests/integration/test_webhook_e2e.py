from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from fastapi.testclient import TestClient

from owlclaw.triggers.webhook import HttpGatewayConfig, build_webhook_application


@dataclass
class _Runtime:
    fail_before_success: int = 0
    calls: int = 0

    async def trigger(self, input_data: Any) -> dict[str, Any]:  # noqa: ARG002
        self.calls += 1
        if self.calls <= self.fail_before_success:
            raise ConnectionError("temporary runtime failure")
        return {"execution_id": f"exec-{self.calls}", "status": "completed", "output": {"ok": True}}


class _AllowPolicy:
    async def check_permission(self, context: Any) -> dict[str, Any]:  # noqa: ARG002
        return {"allowed": True}

    async def check_rate_limit(self, context: Any) -> dict[str, Any]:  # noqa: ARG002
        return {"allowed": True}


class _DenyPolicy:
    async def check_permission(self, context: Any) -> dict[str, Any]:  # noqa: ARG002
        return {"allowed": False, "status_code": 403, "reason": "denied by governance"}

    async def check_rate_limit(self, context: Any) -> dict[str, Any]:  # noqa: ARG002
        return {"allowed": True}


def _create_endpoint(client: TestClient, token: str = "token-e2e", retry_policy: dict[str, Any] | None = None) -> str:
    payload: dict[str, Any] = {
        "name": "orders",
        "target_agent_id": "agent-1",
        "auth_method": {"type": "bearer", "token": token},
        "execution_mode": "async",
    }
    if retry_policy is not None:
        payload["retry_policy"] = retry_policy
    resp = client.post("/endpoints", json=payload)
    assert resp.status_code == 201
    return resp.json()["id"]


def test_e2e_complete_webhook_request_pipeline() -> None:
    runtime = _Runtime()
    app = build_webhook_application(runtime=runtime, governance_policy=_AllowPolicy(), config=HttpGatewayConfig())
    client = TestClient(app.build_http_app())
    endpoint_id = _create_endpoint(client)

    resp = client.post(
        f"/webhooks/{endpoint_id}",
        headers={"Authorization": "Bearer token-e2e", "Content-Type": "application/json"},
        json={"order_id": "o-1"},
    )
    assert resp.status_code == 202
    assert runtime.calls == 1


def test_e2e_multi_endpoint_processing() -> None:
    runtime = _Runtime()
    app = build_webhook_application(runtime=runtime, governance_policy=_AllowPolicy())
    client = TestClient(app.build_http_app())
    endpoint_a = _create_endpoint(client, token="token-a")
    endpoint_b = _create_endpoint(client, token="token-b")

    resp_a = client.post(
        f"/webhooks/{endpoint_a}",
        headers={"Authorization": "Bearer token-a", "Content-Type": "application/json"},
        json={"stream": "a"},
    )
    resp_b = client.post(
        f"/webhooks/{endpoint_b}",
        headers={"Authorization": "Bearer token-b", "Content-Type": "application/json"},
        json={"stream": "b"},
    )
    assert resp_a.status_code == 202
    assert resp_b.status_code == 202
    assert runtime.calls == 2


def test_e2e_idempotency_under_concurrency() -> None:
    runtime = _Runtime()
    app = build_webhook_application(runtime=runtime, governance_policy=_AllowPolicy())
    client = TestClient(app.build_http_app())
    endpoint_id = _create_endpoint(client)

    def _send() -> int:
        response = client.post(
            f"/webhooks/{endpoint_id}",
            headers={
                "Authorization": "Bearer token-e2e",
                "Content-Type": "application/json",
                "X-Idempotency-Key": "same-key",
            },
            json={"x": 1},
        )
        return response.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(lambda _: _send(), [1, 2]))
    assert statuses == [202, 202]
    assert runtime.calls == 1


def test_e2e_retry_behavior() -> None:
    runtime = _Runtime(fail_before_success=2)
    app = build_webhook_application(runtime=runtime, governance_policy=_AllowPolicy())
    client = TestClient(app.build_http_app())
    endpoint_id = _create_endpoint(
        client,
        retry_policy={"max_attempts": 3, "initial_delay_ms": 1, "max_delay_ms": 10, "backoff_multiplier": 2.0},
    )

    resp = client.post(
        f"/webhooks/{endpoint_id}",
        headers={"Authorization": "Bearer token-e2e", "Content-Type": "application/json"},
        json={"retry": True},
    )
    assert resp.status_code == 202
    assert runtime.calls == 3


def test_e2e_governance_rejection_path() -> None:
    runtime = _Runtime()
    app = build_webhook_application(runtime=runtime, governance_policy=_DenyPolicy())
    client = TestClient(app.build_http_app())
    endpoint_id = _create_endpoint(client)

    resp = client.post(
        f"/webhooks/{endpoint_id}",
        headers={"Authorization": "Bearer token-e2e", "Content-Type": "application/json"},
        json={"x": 1},
    )
    assert resp.status_code == 403
    assert runtime.calls == 0
