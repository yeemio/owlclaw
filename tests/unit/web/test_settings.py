"""Tests for settings API and provider."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

from owlclaw.web import create_console_app
from owlclaw.web.providers.settings import DefaultSettingsProvider


class _SettingsProviderStub:
    async def get_settings(self, tenant_id: str) -> dict[str, Any]:
        _ = tenant_id
        return {"runtime": {"console_enabled": True}}

    async def get_system_info(self) -> dict[str, Any]:
        return {"version": "v-test"}


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


def _build_app(provider: _SettingsProviderStub):
    return create_console_app(
        providers={
            "overview": _OverviewProviderStub(),
            "governance": _GovernanceProviderStub(),
            "triggers": _TriggersProviderStub(),
            "agents": _AgentsProviderStub(),
            "capabilities": _CapabilitiesProviderStub(),
            "ledger": _LedgerProviderStub(),
            "settings": provider,
        }
    )


def test_settings_route_returns_settings_and_system() -> None:
    app = _build_app(_SettingsProviderStub())
    client = TestClient(app)
    response = client.get("/api/v1/settings")
    assert response.status_code == 200
    payload = response.json()
    assert payload["runtime"]["console_enabled"] is True
    assert payload["system"]["version"] == "v-test"


@pytest.mark.asyncio
async def test_default_settings_provider_masks_sensitive_env(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = DefaultSettingsProvider()
    monkeypatch.setenv("OWLCLAW_CONSOLE_TOKEN", "secret-value")
    monkeypatch.setenv("OWLCLAW_CONSOLE_CORS_ORIGINS", "http://localhost:3000")

    settings_payload = await provider.get_settings("default")
    runtime_env = settings_payload["runtime"]["env"]
    assert runtime_env["OWLCLAW_CONSOLE_TOKEN"] == "***"
    assert runtime_env["OWLCLAW_CONSOLE_CORS_ORIGINS"] == "http://localhost:3000"


@pytest.mark.asyncio
async def test_default_settings_provider_system_info_contains_version() -> None:
    provider = DefaultSettingsProvider()
    payload = await provider.get_system_info()
    assert "version" in payload
    assert "python_version" in payload
