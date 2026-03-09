"""Tests for websocket realtime endpoint."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from owlclaw.web import create_console_app
from owlclaw.web.contracts import HealthStatus, OverviewMetrics


class _OverviewProviderStub:
    async def get_overview(self, tenant_id: str) -> OverviewMetrics:
        _ = tenant_id
        return OverviewMetrics(
            total_cost_today=Decimal("1.20"),
            total_executions_today=2,
            success_rate_today=1.0,
            active_agents=1,
            health_checks=[HealthStatus(component="runtime", healthy=True)],
        )


class _TriggersProviderStub:
    async def list_triggers(self, tenant_id: str) -> list[dict[str, Any]]:
        _ = tenant_id
        return [{"id": "cron-1", "type": "cron", "enabled": True, "next_run": None, "success_rate": 1.0}]

    async def get_trigger_history(self, trigger_id: str, tenant_id: str, limit: int, offset: int) -> tuple[list[dict[str, Any]], int]:
        _ = (trigger_id, tenant_id, limit, offset)
        return [], 0


class _LedgerProviderStub:
    async def query_records(
        self,
        tenant_id: str,
        agent_id: str | None,
        capability_name: str | None,
        status: str | None,
        start_date: date | None,
        end_date: date | None,
        min_cost: Decimal | None,
        max_cost: Decimal | None,
        limit: int,
        offset: int,
        order_by: str | None,
    ) -> tuple[list[dict[str, Any]], int]:
        _ = (tenant_id, agent_id, capability_name, status, start_date, end_date, min_cost, max_cost, limit, offset, order_by)
        return [{"id": "rec-1"}], 1

    async def get_record_detail(self, record_id: str, tenant_id: str) -> dict[str, Any] | None:
        _ = (record_id, tenant_id)
        return None


class _GovernanceProviderStub:
    async def get_budget_trend(self, tenant_id: str, start_date: date, end_date: date, granularity: str) -> list[dict[str, Any]]:
        _ = (tenant_id, start_date, end_date, granularity)
        return []

    async def get_circuit_breaker_states(self, tenant_id: str) -> list[dict[str, Any]]:
        _ = tenant_id
        return []

    async def get_visibility_matrix(self, tenant_id: str, agent_id: str | None) -> dict[str, Any]:
        _ = (tenant_id, agent_id)
        return {"items": []}


class _AgentsProviderStub:
    async def list_agents(self, tenant_id: str) -> list[dict[str, Any]]:
        _ = tenant_id
        return []

    async def get_agent_detail(self, agent_id: str, tenant_id: str) -> dict[str, Any] | None:
        _ = (agent_id, tenant_id)
        return None


class _CapabilitiesProviderStub:
    async def list_capabilities(self, tenant_id: str, category: str | None) -> list[dict[str, Any]]:
        _ = (tenant_id, category)
        return []

    async def get_capability_schema(self, capability_name: str) -> dict[str, Any] | None:
        _ = capability_name
        return None


class _SettingsProviderStub:
    async def get_settings(self, tenant_id: str) -> dict[str, Any]:
        _ = tenant_id
        return {}

    async def get_system_info(self) -> dict[str, Any]:
        return {}


def _build_app() -> Any:
    app = create_console_app(
        providers={
            "overview": _OverviewProviderStub(),
            "governance": _GovernanceProviderStub(),
            "triggers": _TriggersProviderStub(),
            "agents": _AgentsProviderStub(),
            "capabilities": _CapabilitiesProviderStub(),
            "ledger": _LedgerProviderStub(),
            "settings": _SettingsProviderStub(),
        }
    )
    app.state.ws_push_interval_seconds = 60.0
    return app


def test_ws_stream_sends_overview_triggers_and_ledger_messages() -> None:
    app = _build_app()
    client = TestClient(app)

    with client.websocket_connect("/api/v1/ws") as ws:
        first = ws.receive_json()
        second = ws.receive_json()
        third = ws.receive_json()
    assert first["type"] == "overview"
    assert second["type"] == "triggers"
    assert third["type"] == "ledger"


def test_ws_requires_token_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OWLCLAW_CONSOLE_TOKEN", "secret-token")
    monkeypatch.setenv("OWLCLAW_REQUIRE_AUTH", "true")
    app = _build_app()
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/api/v1/ws"):
            pass

    with client.websocket_connect("/api/v1/ws?token=secret-token") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "overview"

    with client.websocket_connect(
        "/api/v1/ws?token=secret-token",
        headers={"x-owlclaw-tenant": "tenant-a"},
    ) as ws:
        with pytest.raises(WebSocketDisconnect):
            ws.receive_json()


def test_ws_accepts_console_api_token_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OWLCLAW_CONSOLE_TOKEN", raising=False)
    monkeypatch.setenv("OWLCLAW_CONSOLE_API_TOKEN", "api-token")
    app = _build_app()
    client = TestClient(app)

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/api/v1/ws"):
            pass

    with client.websocket_connect("/api/v1/ws?token=api-token") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "overview"
