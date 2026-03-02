"""Tests for overview provider and API route."""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from owlclaw.web import create_console_app
from owlclaw.web.contracts import HealthStatus, OverviewMetrics
from owlclaw.web.providers.overview import DefaultOverviewProvider


class _OverviewProviderStub:
    async def get_overview(self, tenant_id: str) -> OverviewMetrics:
        _ = tenant_id
        return OverviewMetrics(
            total_cost_today=Decimal("12.34"),
            total_executions_today=9,
            success_rate_today=0.8889,
            active_agents=3,
            health_checks=[
                HealthStatus(component="runtime", healthy=True, message="ok"),
                HealthStatus(component="db", healthy=True, message="connected"),
            ],
        )


def test_overview_route_returns_overview_metrics_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OWLCLAW_CONSOLE_TOKEN", raising=False)
    app = create_console_app(
        providers={
            "overview": _OverviewProviderStub(),
            "governance": object(),
            "triggers": object(),
            "agents": object(),
            "capabilities": object(),
            "ledger": object(),
            "settings": object(),
        }
    )
    client = TestClient(app)

    response = client.get("/api/v1/overview")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_cost_today"] == "12.34"
    assert payload["total_executions_today"] == 9
    assert payload["active_agents"] == 3
    assert payload["health_checks"][1]["component"] == "db"


@pytest.mark.asyncio
async def test_default_overview_provider_uses_ttl_cache() -> None:
    calls = {"health": 0, "metrics": 0}
    now = [100.0]

    async def health_checker() -> list[HealthStatus]:
        calls["health"] += 1
        return [HealthStatus(component="db", healthy=True, message="connected")]

    async def metrics_fetcher(tenant_id: str, db_healthy: bool) -> tuple[Decimal, int, float, int]:
        _ = tenant_id
        assert db_healthy is True
        calls["metrics"] += 1
        return Decimal("1.25"), 5, 0.8, 2

    provider = DefaultOverviewProvider(
        ttl_seconds=30.0,
        clock=lambda: now[0],
        health_checker=health_checker,
        metrics_fetcher=metrics_fetcher,
    )

    first = await provider.get_overview("default")
    second = await provider.get_overview("default")
    assert first == second
    assert calls["health"] == 1
    assert calls["metrics"] == 1

    now[0] += 31.0
    third = await provider.get_overview("default")
    assert third.total_executions_today == 5
    assert calls["health"] == 2
    assert calls["metrics"] == 2


@pytest.mark.asyncio
async def test_default_overview_provider_passes_db_health_to_metrics_fetcher() -> None:
    observed: list[bool] = []

    async def health_checker() -> list[HealthStatus]:
        return [HealthStatus(component="db", healthy=False, message="down")]

    async def metrics_fetcher(tenant_id: str, db_healthy: bool) -> tuple[Decimal, int, float, int]:
        _ = tenant_id
        observed.append(db_healthy)
        return Decimal("0"), 0, 0.0, 0

    provider = DefaultOverviewProvider(
        health_checker=health_checker,
        metrics_fetcher=metrics_fetcher,
    )
    metrics = await provider.get_overview("default")
    assert metrics.total_executions_today == 0
    assert observed == [False]
