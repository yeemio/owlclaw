"""Tests for agents API and provider."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

from owlclaw.db.exceptions import ConfigurationError
from owlclaw.web import create_console_app
from owlclaw.web.providers.agents import DefaultAgentsProvider


class _AgentsProviderStub:
    async def list_agents(self, tenant_id: str) -> list[dict[str, Any]]:
        _ = tenant_id
        return [{"id": "agent-1", "run_count": 3}]

    async def get_agent_detail(self, agent_id: str, tenant_id: str) -> dict[str, Any] | None:
        _ = tenant_id
        if agent_id == "missing":
            return None
        return {"id": agent_id, "recent_history": []}


class _OverviewProviderStub:
    async def get_overview(self, tenant_id: str) -> dict[str, Any]:
        _ = tenant_id
        return {
            "total_cost_today": Decimal("0"),
            "total_executions_today": 0,
            "success_rate_today": 0.0,
            "active_agents": 0,
            "health_checks": [],
        }


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


class _TriggersProviderStub:
    async def list_triggers(self, tenant_id: str) -> list[dict[str, Any]]:
        _ = tenant_id
        return []

    async def get_trigger_history(self, trigger_id: str, tenant_id: str, limit: int, offset: int) -> tuple[list[dict[str, Any]], int]:
        _ = (trigger_id, tenant_id, limit, offset)
        return [], 0


class _CapabilitiesProviderStub:
    async def list_capabilities(self, tenant_id: str, category: str | None) -> list[dict[str, Any]]:
        _ = (tenant_id, category)
        return []

    async def get_capability_schema(self, capability_name: str) -> dict[str, Any] | None:
        _ = capability_name
        return None


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
        return [], 0

    async def get_record_detail(self, record_id: str, tenant_id: str) -> dict[str, Any] | None:
        _ = (record_id, tenant_id)
        return None


class _SettingsProviderStub:
    async def get_settings(self, tenant_id: str) -> dict[str, Any]:
        _ = tenant_id
        return {}

    async def get_system_info(self) -> dict[str, Any]:
        return {}


def _build_app(provider: _AgentsProviderStub):
    return create_console_app(
        providers={
            "overview": _OverviewProviderStub(),
            "governance": _GovernanceProviderStub(),
            "triggers": _TriggersProviderStub(),
            "agents": provider,
            "capabilities": _CapabilitiesProviderStub(),
            "ledger": _LedgerProviderStub(),
            "settings": _SettingsProviderStub(),
        }
    )


def test_agents_list_route_returns_items() -> None:
    app = _build_app(_AgentsProviderStub())
    client = TestClient(app)
    response = client.get("/api/v1/agents")
    assert response.status_code == 200
    assert response.json()["items"][0]["id"] == "agent-1"


def test_agents_list_route_returns_empty_when_database_not_configured() -> None:
    class _NoDbProvider(_AgentsProviderStub):
        async def list_agents(self, tenant_id: str) -> list[dict[str, Any]]:
            _ = tenant_id
            raise ConfigurationError("Database URL not set")

    app = _build_app(_NoDbProvider())
    client = TestClient(app)
    response = client.get("/api/v1/agents")
    assert response.status_code == 200
    assert response.json() == {"items": [], "message": "Database not configured"}


def test_agents_detail_route_returns_404_when_missing() -> None:
    app = _build_app(_AgentsProviderStub())
    client = TestClient(app)
    response = client.get("/api/v1/agents/missing")
    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "NOT_FOUND"
    assert payload["error"]["message"] == "Agent not found"


@dataclass
class _AggRow:
    agent_id: str
    runs: int
    last_run_at: datetime
    capability_count: int


@dataclass
class _Record:
    id: uuid.UUID
    run_id: str
    capability_name: str
    status: str
    execution_time_ms: int
    estimated_cost: Decimal
    created_at: datetime


class _FakeResult:
    def __init__(self, rows: list[Any], *, scalar: bool = False) -> None:
        self._rows = rows
        self._scalar = scalar

    def all(self) -> list[Any]:
        return self._rows

    def scalars(self) -> _FakeResult:
        return self

    def scalar_one_or_none(self) -> Any:
        if not self._rows:
            return None
        return self._rows[0]


class _FakeSession:
    def __init__(self, shared_results: list[_FakeResult]) -> None:
        self._shared_results = shared_results

    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        _ = (exc_type, exc, tb)

    async def execute(self, statement: Any) -> _FakeResult:
        _ = statement
        return self._shared_results.pop(0)


def _fake_session_factory(results: list[_FakeResult]):
    shared_results = list(results)

    def _factory(_engine: Any):
        def _session() -> _FakeSession:
            return _FakeSession(shared_results)

        return _session

    return _factory


@pytest.mark.asyncio
async def test_default_agents_provider_list_and_detail(monkeypatch: pytest.MonkeyPatch) -> None:
    from owlclaw.web.providers import agents as module

    now = datetime.now(tz=UTC)
    agg_rows = [("agent-a", 3, now, 2)]
    detail_rows = [
        _Record(
            id=uuid.uuid4(),
            run_id="run-1",
            capability_name="cap-1",
            status="success",
            execution_time_ms=120,
            estimated_cost=Decimal("1.23"),
            created_at=now,
        )
    ]
    monkeypatch.setattr(module, "get_engine", lambda: object())
    monkeypatch.setattr(
        module,
        "create_session_factory",
        _fake_session_factory([_FakeResult(agg_rows), _FakeResult(detail_rows)]),
    )

    provider = DefaultAgentsProvider()
    agents = await provider.list_agents("default")
    assert agents[0]["agent_id"] == "agent-a"

    detail = await provider.get_agent_detail("agent-a", "default")
    assert detail is not None
    assert detail["recent_history"][0]["run_id"] == "run-1"
