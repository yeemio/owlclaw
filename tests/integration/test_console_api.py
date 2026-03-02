"""Integration tests for console API endpoints with mock providers."""

from __future__ import annotations

import time
from datetime import date
from decimal import Decimal
from typing import Any

from fastapi.testclient import TestClient

from owlclaw.web import create_console_app
from owlclaw.web.contracts import HealthStatus, OverviewMetrics


class _OverviewProvider:
    async def get_overview(self, tenant_id: str) -> OverviewMetrics:
        _ = tenant_id
        return OverviewMetrics(
            total_cost_today=Decimal("2.5"),
            total_executions_today=10,
            success_rate_today=0.9,
            active_agents=2,
            health_checks=[HealthStatus(component="runtime", healthy=True)],
        )


class _GovernanceProvider:
    async def get_budget_trend(self, tenant_id: str, start_date: date, end_date: date, granularity: str) -> list[dict[str, Any]]:
        _ = (tenant_id, start_date, end_date, granularity)
        return [{"period_start": "2026-03-02T00:00:00+00:00", "total_cost": "2.5", "executions": 10}]

    async def get_circuit_breaker_states(self, tenant_id: str) -> list[dict[str, Any]]:
        _ = tenant_id
        return [{"capability_name": "cap-a", "state": "closed"}]

    async def get_visibility_matrix(self, tenant_id: str, agent_id: str | None) -> dict[str, Any]:
        _ = (tenant_id, agent_id)
        return {"agent_id": agent_id, "items": [{"capability_name": "cap-a", "visible": True}]}


class _TriggersProvider:
    async def list_triggers(self, tenant_id: str) -> list[dict[str, Any]]:
        _ = tenant_id
        return [{"id": "cron-1", "type": "cron", "enabled": True, "next_run": None, "success_rate": 1.0}]

    async def get_trigger_history(self, trigger_id: str, tenant_id: str, limit: int, offset: int) -> tuple[list[dict[str, Any]], int]:
        _ = (tenant_id, limit, offset)
        return ([{"id": "h1", "trigger_id": trigger_id}], 1)


class _AgentsProvider:
    async def list_agents(self, tenant_id: str) -> list[dict[str, Any]]:
        _ = tenant_id
        return [{"id": "agent-1", "run_count": 10}]

    async def get_agent_detail(self, agent_id: str, tenant_id: str) -> dict[str, Any] | None:
        _ = tenant_id
        if agent_id != "agent-1":
            return None
        return {"id": "agent-1", "recent_history": []}


class _CapabilitiesProvider:
    async def list_capabilities(self, tenant_id: str, category: str | None) -> list[dict[str, Any]]:
        _ = tenant_id
        return [{"name": "cap-a", "category": category or "handler"}]

    async def get_capability_schema(self, capability_name: str) -> dict[str, Any] | None:
        if capability_name != "cap-a":
            return None
        return {"type": "object", "properties": {"x": {"type": "string"}}, "required": ["x"]}


class _LedgerProvider:
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
        return ([{"id": "rec-1", "estimated_cost": "1.0", "status": "success"}], 1)

    async def get_record_detail(self, record_id: str, tenant_id: str) -> dict[str, Any] | None:
        _ = tenant_id
        if record_id != "rec-1":
            return None
        return {"id": "rec-1", "status": "success"}


class _SettingsProvider:
    async def get_settings(self, tenant_id: str) -> dict[str, Any]:
        _ = tenant_id
        return {"runtime": {"console_enabled": True}}

    async def get_system_info(self) -> dict[str, Any]:
        return {"version": "v-test"}


def _create_client() -> TestClient:
    app = create_console_app(
        providers={
            "overview": _OverviewProvider(),
            "governance": _GovernanceProvider(),
            "triggers": _TriggersProvider(),
            "agents": _AgentsProvider(),
            "capabilities": _CapabilitiesProvider(),
            "ledger": _LedgerProvider(),
            "settings": _SettingsProvider(),
        }
    )
    app.state.ws_push_interval_seconds = 60.0
    return TestClient(app)


def test_console_api_endpoints_cover_core_routes() -> None:
    client = _create_client()
    endpoints = [
        ("/api/v1/overview", 200),
        ("/api/v1/agents", 200),
        ("/api/v1/agents/agent-1", 200),
        ("/api/v1/governance/budget", 200),
        ("/api/v1/governance/circuit-breakers", 200),
        ("/api/v1/governance/visibility-matrix", 200),
        ("/api/v1/capabilities", 200),
        ("/api/v1/capabilities/cap-a/schema", 200),
        ("/api/v1/triggers", 200),
        ("/api/v1/triggers/cron-1/history", 200),
        ("/api/v1/ledger", 200),
        ("/api/v1/ledger/rec-1", 200),
        ("/api/v1/settings", 200),
    ]
    for path, expected in endpoints:
        response = client.get(path)
        assert response.status_code == expected


def test_console_websocket_endpoint_streams_messages() -> None:
    client = _create_client()
    with client.websocket_connect("/api/v1/ws") as ws:
        types = [ws.receive_json()["type"] for _ in range(3)]
    assert types == ["overview", "triggers", "ledger"]


def test_console_api_overview_p95_under_200ms() -> None:
    client = _create_client()
    durations: list[float] = []
    for _ in range(30):
        started = time.perf_counter()
        response = client.get("/api/v1/overview")
        ended = time.perf_counter()
        assert response.status_code == 200
        durations.append((ended - started) * 1000)

    sorted_durations = sorted(durations)
    p95_index = max(0, int(len(sorted_durations) * 0.95) - 1)
    p95_ms = sorted_durations[p95_index]
    assert p95_ms < 200.0
