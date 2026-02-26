"""Unit tests for quality metric aggregation."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

from owlclaw.governance.quality_aggregator import QualityAggregator, QualityWeights


def _record(
    *,
    status: str,
    latency: int,
    cost: str,
    at: datetime,
    tenant: str = "default",
    skill: str = "inventory-monitor",
    input_params: dict | None = None,
    output_result: dict | None = None,
):
    return SimpleNamespace(
        tenant_id=tenant,
        capability_name=skill,
        status=status,
        execution_time_ms=latency,
        estimated_cost=Decimal(cost),
        input_params=input_params or {},
        output_result=output_result or {},
        created_at=at,
    )


def test_quality_aggregator_computes_metrics() -> None:
    agg = QualityAggregator()
    now = datetime.now(timezone.utc)
    records = [
        _record(status="success", latency=1000, cost="0.01", at=now - timedelta(hours=3), input_params={"approval": "approved"}),
        _record(status="success", latency=2000, cost="0.02", at=now - timedelta(hours=2), output_result={"modified": True}),
        _record(status="error", latency=3000, cost="0.03", at=now - timedelta(hours=1), input_params={"manual_intervention": True}),
    ]
    report = agg.compute_report(
        tenant_id="default",
        skill_name="inventory-monitor",
        records=records,
        window_end=now,
    )
    assert report.total_runs == 3
    assert round(report.success_rate, 3) == 0.667
    assert report.avg_latency_ms == 2000.0
    assert report.avg_cost == 0.02
    assert round(report.intervention_rate, 3) == 0.333
    assert 0.0 <= report.satisfaction <= 1.0
    assert 0.0 <= report.quality_score <= 1.0


def test_quality_aggregator_filters_by_window_and_identity() -> None:
    agg = QualityAggregator()
    now = datetime.now(timezone.utc)
    records = [
        _record(status="success", latency=1000, cost="0.01", at=now - timedelta(days=1)),
        _record(status="success", latency=1000, cost="0.01", at=now - timedelta(days=40)),
        _record(status="success", latency=1000, cost="0.01", at=now - timedelta(days=1), tenant="other"),
        _record(status="success", latency=1000, cost="0.01", at=now - timedelta(days=1), skill="other-skill"),
    ]
    report = agg.compute_report(
        tenant_id="default",
        skill_name="inventory-monitor",
        records=records,
        window_end=now,
        window=timedelta(days=30),
    )
    assert report.total_runs == 1


def test_quality_aggregator_custom_weights_affect_score() -> None:
    now = datetime.now(timezone.utc)
    records = [
        _record(status="success", latency=100, cost="0.01", at=now - timedelta(hours=2)),
        _record(status="error", latency=100, cost="0.01", at=now - timedelta(hours=1)),
    ]
    baseline = QualityAggregator().compute_report(
        tenant_id="default",
        skill_name="inventory-monitor",
        records=records,
        window_end=now,
    )
    weighted = QualityAggregator(
        QualityWeights(
            success_rate=0.9,
            intervention_rate=0.02,
            satisfaction=0.02,
            consistency=0.02,
            latency=0.02,
            cost=0.02,
        )
    ).compute_report(
        tenant_id="default",
        skill_name="inventory-monitor",
        records=records,
        window_end=now,
    )
    assert weighted.quality_score < baseline.quality_score


def test_quality_aggregator_compute_trend_periods() -> None:
    agg = QualityAggregator()
    now = datetime.now(timezone.utc)
    records = [
        _record(status="success", latency=1000, cost="0.01", at=now - timedelta(days=1)),
        _record(status="success", latency=1000, cost="0.01", at=now - timedelta(days=8)),
        _record(status="success", latency=1000, cost="0.01", at=now - timedelta(days=15)),
    ]
    trend = agg.compute_trend(
        tenant_id="default",
        skill_name="inventory-monitor",
        records=records,
        window_end=now,
        periods=3,
        granularity="week",
    )
    assert len(trend) == 3
    assert trend[0].window_end <= trend[1].window_end <= trend[2].window_end
