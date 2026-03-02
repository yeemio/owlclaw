"""Tests for console contracts module."""

from decimal import Decimal

from owlclaw.web.contracts import HealthStatus, OverviewMetrics, PaginatedResult


def test_contract_dataclasses_construct_successfully() -> None:
    metrics = OverviewMetrics(
        total_cost_today=Decimal("1.23"),
        total_executions_today=2,
        success_rate_today=0.5,
        active_agents=1,
        health_checks=[HealthStatus(component="runtime", healthy=True)],
    )
    paged = PaginatedResult(items=[metrics], total=1, offset=0, limit=10)
    assert paged.total == 1
    assert paged.items[0].total_cost_today == Decimal("1.23")

