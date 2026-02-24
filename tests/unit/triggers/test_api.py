from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import pytest
from starlette.testclient import TestClient

from owlclaw.triggers.api import APITriggerConfig, APITriggerServer
from owlclaw.triggers.api.auth import APIKeyAuthProvider, BearerTokenAuthProvider


@dataclass
class _Runtime:
    calls: list[dict[str, Any]] = field(default_factory=list)
    delay_seconds: float = 0.0

    async def trigger_event(
        self,
        event_name: str,
        payload: dict[str, Any],
        focus: str | None = None,
        tenant_id: str = "default",
    ) -> dict[str, Any]:
        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)
        self.calls.append({"event_name": event_name, "payload": payload, "focus": focus, "tenant_id": tenant_id})
        return {"ok": True, "event_name": event_name}


def test_api_trigger_config_validation() -> None:
    config = APITriggerConfig(path="/api/v1/analysis", method="POST", event_name="analysis_request")
    assert config.response_mode == "async"


def test_api_key_auth_provider() -> None:
    runtime = _Runtime()
    server = APITriggerServer(auth_provider=APIKeyAuthProvider({"k1"}), agent_runtime=runtime)
    server.register(APITriggerConfig(path="/api/v1/orders", method="POST", event_name="order_request", response_mode="sync"))

    with TestClient(server.app) as client:
        unauthorized = client.post("/api/v1/orders", json={"x": 1})
        assert unauthorized.status_code == 401

        ok = client.post("/api/v1/orders", headers={"X-API-Key": "k1"}, json={"x": 1})
        assert ok.status_code == 200
        assert ok.json()["status"] == "ok"


def test_bearer_auth_provider() -> None:
    runtime = _Runtime()
    server = APITriggerServer(auth_provider=BearerTokenAuthProvider({"t1"}), agent_runtime=runtime)
    server.register(APITriggerConfig(path="/api/v1/secure", method="POST", event_name="secure_request", response_mode="sync"))

    with TestClient(server.app) as client:
        unauthorized = client.post("/api/v1/secure", json={"x": 1})
        assert unauthorized.status_code == 401

        ok = client.post("/api/v1/secure", headers={"Authorization": "Bearer t1"}, json={"x": 1})
        assert ok.status_code == 200


def test_api_trigger_server_async_mode_returns_202() -> None:
    runtime = _Runtime()
    server = APITriggerServer(auth_provider=APIKeyAuthProvider({"k1"}), agent_runtime=runtime)
    server.register(APITriggerConfig(path="/api/v1/async", method="POST", event_name="async_request", response_mode="async"))

    with TestClient(server.app) as client:
        response = client.post("/api/v1/async", headers={"X-API-Key": "k1"}, json={"foo": "bar"})
    assert response.status_code == 202
    assert "run_id" in response.json()
    assert response.headers.get("Location", "").startswith("/runs/")


def test_api_trigger_server_sync_timeout_returns_408(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _Runtime()
    server = APITriggerServer(auth_provider=APIKeyAuthProvider({"k1"}), agent_runtime=runtime)
    server.register(
        APITriggerConfig(
            path="/api/v1/timeout",
            method="POST",
            event_name="timeout_request",
            response_mode="sync",
            sync_timeout_seconds=1,
        )
    )

    async def _raise_timeout(coro: Any, *args: Any, **kwargs: Any) -> Any:
        if hasattr(coro, "close"):
            coro.close()
        raise asyncio.TimeoutError

    monkeypatch.setattr("owlclaw.triggers.api.server.asyncio.wait_for", _raise_timeout)

    with TestClient(server.app) as client:
        response = client.post("/api/v1/timeout", headers={"X-API-Key": "k1"}, json={"foo": "bar"})
    assert response.status_code == 408


def test_api_trigger_server_duplicate_registration_raises() -> None:
    server = APITriggerServer()
    cfg = APITriggerConfig(path="/api/v1/x", method="POST", event_name="x")
    server.register(cfg)
    try:
        server.register(cfg)
        raise AssertionError("Expected ValueError")
    except ValueError:
        pass
