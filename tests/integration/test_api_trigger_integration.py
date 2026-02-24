from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest
from starlette.testclient import TestClient

from owlclaw.triggers.api import APITriggerConfig, APITriggerServer, GovernanceDecision
from owlclaw.triggers.api.auth import APIKeyAuthProvider

pytestmark = pytest.mark.integration


@dataclass
class _Runtime:
    async def trigger_event(
        self,
        event_name: str,
        payload: dict[str, Any],
        focus: str | None = None,
        tenant_id: str = "default",
    ) -> dict[str, Any]:
        return {"event_name": event_name, "tenant_id": tenant_id, "ok": True}


@dataclass
class _Gate:
    mode: str = "allow"

    async def evaluate_request(self, event_name: str, tenant_id: str, payload: dict[str, Any]) -> GovernanceDecision:  # noqa: ARG002
        if self.mode == "rate":
            return GovernanceDecision(allowed=False, status_code=429, reason="rate_limited")
        if self.mode == "budget":
            return GovernanceDecision(allowed=False, status_code=503, reason="budget_exhausted")
        return GovernanceDecision(allowed=True)


def test_api_trigger_integration_auth_and_sync_flow() -> None:
    server = APITriggerServer(auth_provider=APIKeyAuthProvider({"k1"}), agent_runtime=_Runtime())
    server.register(APITriggerConfig(path="/api/v1/orders", method="POST", event_name="order_request", response_mode="sync"))

    with TestClient(server.app) as client:
        no_auth = client.post("/api/v1/orders", json={"a": 1})
        assert no_auth.status_code == 401

        ok = client.post("/api/v1/orders", headers={"X-API-Key": "k1"}, json={"a": 1})
        assert ok.status_code == 200
        assert ok.json()["status"] == "ok"


def test_api_trigger_integration_governance_block_flow() -> None:
    server = APITriggerServer(auth_provider=APIKeyAuthProvider({"k1"}), agent_runtime=_Runtime(), governance_gate=_Gate(mode="rate"))
    server.register(APITriggerConfig(path="/api/v1/guarded", method="POST", event_name="guarded", response_mode="sync"))

    with TestClient(server.app) as client:
        blocked = client.post("/api/v1/guarded", headers={"X-API-Key": "k1"}, json={"a": 1})
    assert blocked.status_code == 429


def test_api_trigger_integration_async_mode_and_result_query() -> None:
    server = APITriggerServer(auth_provider=APIKeyAuthProvider({"k1"}), agent_runtime=_Runtime())
    server.register(APITriggerConfig(path="/api/v1/async", method="POST", event_name="async_request", response_mode="async"))

    with TestClient(server.app) as client:
        accepted = client.post("/api/v1/async", headers={"X-API-Key": "k1"}, json={"a": 1})
        assert accepted.status_code == 202
        run_id = accepted.json()["run_id"]

        found_completed = False
        for _ in range(10):
            result = client.get(f"/runs/{run_id}/result")
            if result.status_code == 200 and result.json().get("status") == "completed":
                found_completed = True
                break
        assert found_completed
