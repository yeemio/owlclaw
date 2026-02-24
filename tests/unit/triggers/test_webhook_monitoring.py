from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from owlclaw.triggers.webhook import AlertRecord, MetricRecord, MonitoringService


@dataclass
class _Notifier:
    alerts: list[AlertRecord] = field(default_factory=list)

    async def notify(self, alert: AlertRecord) -> None:
        self.alerts.append(alert)


@pytest.mark.asyncio
async def test_monitoring_health_status_response_format() -> None:
    service = MonitoringService()
    service.register_health_check("database", lambda: True)
    service.register_health_check("runtime", lambda: False)
    service.register_health_check("governance", lambda: True)

    status = await service.get_health_status()
    assert status.status == "degraded"
    assert len(status.checks) == 3
    assert {check.name for check in status.checks} == {"database", "runtime", "governance"}


@pytest.mark.asyncio
async def test_monitoring_metrics_aggregation_accuracy() -> None:
    service = MonitoringService()
    await service.record_metric(MetricRecord(name="request_count", value=1))
    await service.record_metric(MetricRecord(name="request_count", value=1))
    await service.record_metric(MetricRecord(name="response_time_ms", value=100))
    await service.record_metric(MetricRecord(name="response_time_ms", value=200))
    await service.record_metric(MetricRecord(name="request_status", value=1, tags={"status": "success"}))
    await service.record_metric(MetricRecord(name="request_status", value=1, tags={"status": "failure"}))

    stats = await service.get_metrics(window="realtime")
    assert stats.request_count == 2
    assert stats.success_rate == pytest.approx(0.5)
    assert stats.failure_rate == pytest.approx(0.5)
    assert stats.avg_response_time == pytest.approx(150.0)
    assert stats.p95_response_time >= 100.0


@pytest.mark.asyncio
async def test_monitoring_alert_dedup_logic() -> None:
    notifier = _Notifier()
    service = MonitoringService(alert_notifier=notifier, dedup_window_seconds=3600)
    alert = AlertRecord(name="high_failure_rate", severity="critical", message="failed")

    first = await service.trigger_alert(alert)
    second = await service.trigger_alert(alert)

    assert first is True
    assert second is False
    assert len(service.get_alerts()) == 1
    assert len(notifier.alerts) == 1
