"""Tests for governance API and provider."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

from owlclaw.web import create_console_app
from owlclaw.governance.visibility import CapabilityView
from owlclaw.web.providers.governance import DefaultGovernanceProvider


class _GovernanceProviderStub:
    def __init__(self) -> None:
        self.last_budget_args: tuple[str, date, date, str] | None = None
        self.last_matrix_args: tuple[str, str | None] | None = None

    async def get_budget_trend(
        self,
        tenant_id: str,
        start_date: date,
        end_date: date,
        granularity: str,
    ) -> list[dict[str, Any]]:
        self.last_budget_args = (tenant_id, start_date, end_date, granularity)
        return [{"period_start": start_date.isoformat(), "granularity": granularity, "total_cost": "1.25", "executions": 3}]

    async def get_circuit_breaker_states(self, tenant_id: str) -> list[dict[str, Any]]:
        _ = tenant_id
        return [{"capability_name": "cap-a", "state": "closed"}]

    async def get_visibility_matrix(self, tenant_id: str, agent_id: str | None) -> dict[str, Any]:
        self.last_matrix_args = (tenant_id, agent_id)
        return {"agent_id": agent_id, "items": [{"capability_name": "cap-a", "visible": True}]}


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


def _build_app(governance_provider: _GovernanceProviderStub):
    return create_console_app(
        providers={
            "overview": _OverviewProviderStub(),
            "governance": governance_provider,
            "triggers": object(),
            "agents": object(),
            "capabilities": object(),
            "ledger": object(),
            "settings": object(),
        }
    )


def test_governance_budget_route_returns_data() -> None:
    provider = _GovernanceProviderStub()
    app = _build_app(provider)
    client = TestClient(app)

    response = client.get("/api/v1/governance/budget?start_date=2026-03-01&end_date=2026-03-02&granularity=day")
    assert response.status_code == 200
    payload = response.json()
    assert payload["granularity"] == "day"
    assert payload["items"][0]["total_cost"] == "1.25"
    assert provider.last_budget_args is not None
    assert provider.last_budget_args[0] == "default"


def test_governance_circuit_breakers_route_returns_data() -> None:
    provider = _GovernanceProviderStub()
    app = _build_app(provider)
    client = TestClient(app)

    response = client.get("/api/v1/governance/circuit-breakers")
    assert response.status_code == 200
    assert response.json()["items"][0]["state"] == "closed"


def test_governance_visibility_matrix_route_passes_agent_id() -> None:
    provider = _GovernanceProviderStub()
    app = _build_app(provider)
    client = TestClient(app)

    response = client.get("/api/v1/governance/visibility-matrix?agent_id=agent-1")
    assert response.status_code == 200
    assert response.json()["agent_id"] == "agent-1"
    assert provider.last_matrix_args == ("default", "agent-1")


class _FakeResult:
    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self._rows = rows

    def all(self) -> list[tuple[Any, ...]]:
        return self._rows


class _FakeSession:
    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self._rows = rows

    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        _ = (exc_type, exc, tb)

    async def execute(self, statement: Any) -> _FakeResult:
        _ = statement
        return _FakeResult(self._rows)


def _fake_session_factory(rows: list[tuple[Any, ...]]):
    def _factory(_engine: Any):
        def _session() -> _FakeSession:
            return _FakeSession(rows)

        return _session

    return _factory


@pytest.mark.asyncio
async def test_default_governance_provider_budget_trend_formats_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    from owlclaw.web.providers import governance as module

    rows = [
        (datetime(2026, 3, 1, tzinfo=UTC), Decimal("3.50"), 5),
        (datetime(2026, 3, 2, tzinfo=UTC), Decimal("2.00"), 2),
    ]
    monkeypatch.setattr(module, "get_engine", lambda: object())
    monkeypatch.setattr(module, "create_session_factory", _fake_session_factory(rows))

    provider = DefaultGovernanceProvider()
    result = await provider.get_budget_trend(
        tenant_id="default",
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 2),
        granularity="day",
    )
    assert len(result) == 2
    assert result[0]["total_cost"] == "3.50"
    assert result[1]["executions"] == 2


@pytest.mark.asyncio
async def test_default_governance_provider_circuit_breaker_state_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    from owlclaw.web.providers import governance as module

    rows = [
        ("cap-open", 10, 7, datetime(2026, 3, 2, tzinfo=UTC)),
        ("cap-half-open", 4, 1, datetime(2026, 3, 2, tzinfo=UTC)),
        ("cap-closed", 3, 0, datetime(2026, 3, 2, tzinfo=UTC)),
    ]
    monkeypatch.setattr(module, "get_engine", lambda: object())
    monkeypatch.setattr(module, "create_session_factory", _fake_session_factory(rows))

    provider = DefaultGovernanceProvider()
    result = await provider.get_circuit_breaker_states(tenant_id="default")
    states = {entry["capability_name"]: entry["state"] for entry in result}
    assert states["cap-open"] == "open"
    assert states["cap-half-open"] == "half_open"
    assert states["cap-closed"] == "closed"


@pytest.mark.asyncio
async def test_default_governance_provider_visibility_matrix_uses_visibility_filter() -> None:
    class _FakeVisibilityFilter:
        async def filter_capabilities(self, capabilities, agent_id, context):
            _ = (agent_id, context)
            return [capabilities[0]]

    capabilities = [
        CapabilityView(name="cap-a", description="", constraints={}),
        CapabilityView(name="cap-b", description="", constraints={}),
    ]
    provider = DefaultGovernanceProvider(
        visibility_filter=_FakeVisibilityFilter(),  # type: ignore[arg-type]
        capability_loader=lambda: capabilities,
    )
    matrix = await provider.get_visibility_matrix(tenant_id="default", agent_id="agent-1")
    items = {entry["capability_name"]: entry["visible"] for entry in matrix["items"]}
    assert items == {"cap-a": True, "cap-b": False}
    assert matrix["source"] == "visibility_filter"
