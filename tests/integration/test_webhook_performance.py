from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from fastapi.testclient import TestClient

from owlclaw.triggers.webhook import build_webhook_application


@dataclass
class _Runtime:
    async def trigger(self, input_data: Any) -> dict[str, Any]:  # noqa: ARG002
        return {"execution_id": "perf", "status": "completed"}


class _AllowPolicy:
    async def check_permission(self, context: Any) -> dict[str, Any]:  # noqa: ARG002
        return {"allowed": True}

    async def check_rate_limit(self, context: Any) -> dict[str, Any]:  # noqa: ARG002
        return {"allowed": True}


def _endpoint(client: TestClient) -> str:
    resp = client.post(
        "/endpoints",
        json={
            "name": "perf",
            "target_agent_id": "agent-p",
            "auth_method": {"type": "bearer", "token": "token-perf"},
            "execution_mode": "async",
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_performance_high_request_volume() -> None:
    app = build_webhook_application(runtime=_Runtime(), governance_policy=_AllowPolicy())
    client = TestClient(app.build_http_app())
    endpoint = _endpoint(client)

    total = 100
    started = time.perf_counter()
    for i in range(total):
        response = client.post(
            f"/webhooks/{endpoint}",
            headers={"Authorization": "Bearer token-perf", "Content-Type": "application/json"},
            json={"idx": i},
        )
        assert response.status_code == 202
    elapsed = time.perf_counter() - started
    assert elapsed < 10.0
