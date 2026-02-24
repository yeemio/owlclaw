from __future__ import annotations

import asyncio

from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.triggers.webhook import MetricRecord, MonitoringService


@given(
    response_times=st.lists(st.floats(min_value=1, max_value=10000, allow_nan=False, allow_infinity=False), min_size=1, max_size=30),
)
@settings(max_examples=30, deadline=None)
def test_property_monitoring_metric_recording(response_times: list[float]) -> None:
    """Feature: triggers-webhook, Property 23: 监控指标记录."""

    async def _run() -> None:
        service = MonitoringService()
        for value in response_times:
            await service.record_metric(MetricRecord(name="request_count", value=1))
            await service.record_metric(MetricRecord(name="response_time_ms", value=value))
            await service.record_metric(MetricRecord(name="request_status", value=1, tags={"status": "success"}))
        stats = await service.get_metrics(window="realtime")
        assert stats.request_count == len(response_times)
        assert stats.avg_response_time > 0
        assert stats.p99_response_time >= stats.p95_response_time

    asyncio.run(_run())


@given(
    failures=st.integers(min_value=1, max_value=20),
    successes=st.integers(min_value=0, max_value=20),
)
@settings(max_examples=30, deadline=None)
def test_property_metrics_threshold_triggers_alerts(failures: int, successes: int) -> None:
    """Feature: triggers-webhook, Property 24: 指标超过阈值触发告警."""

    async def _run() -> None:
        service = MonitoringService(failure_rate_threshold=0.2, dedup_window_seconds=0)
        for _ in range(successes):
            await service.record_metric(MetricRecord(name="request_status", value=1, tags={"status": "success"}))
        for _ in range(failures):
            await service.record_metric(MetricRecord(name="request_status", value=1, tags={"status": "failure"}))
        stats = await service.get_metrics(window="realtime")
        alerts = service.get_alerts()
        if stats.failure_rate > 0.2:
            assert any(alert.name == "high_failure_rate" for alert in alerts)

    asyncio.run(_run())
