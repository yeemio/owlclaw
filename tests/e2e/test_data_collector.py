"""Unit tests for e2e DataCollector."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from owlclaw.e2e.data_collector import DataCollector


class TestDataCollector:
    def test_record_requires_started_collection(self) -> None:
        collector = DataCollector()
        with pytest.raises(RuntimeError):
            collector.record_event(event_type="runtime.step")
        with pytest.raises(RuntimeError):
            collector.record_metric("latency_ms", 12.0)
        with pytest.raises(RuntimeError):
            collector.record_error("boom")

    def test_collects_events_metrics_and_errors(self) -> None:
        collector = DataCollector()
        collector.start_collection("run-1")
        ts = datetime.now(UTC)
        collector.record_event(
            event_type="cron.triggered",
            message="triggered",
            data={"task": "m1"},
            timestamp=ts,
        )
        collector.record_metric("latency_ms", 10.5)
        collector.record_metric("cost_usd", 0.001)
        collector.record_error("network timeout")
        collector.record_trace({"component": "agent-runtime", "status": "ok"})
        collector.record_resource_usage("cpu_percent", 25.0)

        snapshot = collector.stop_collection()
        assert snapshot.execution_id == "run-1"
        assert len(snapshot.events) == 1
        assert snapshot.events[0].timestamp == ts
        assert snapshot.events[0].event_type == "cron.triggered"
        assert snapshot.events[0].data == {"task": "m1"}
        assert snapshot.metrics == {"latency_ms": 10.5, "cost_usd": 0.001}
        assert snapshot.errors == ["network timeout"]
        assert snapshot.traces == [{"component": "agent-runtime", "status": "ok"}]
        assert snapshot.resource_usage == {"cpu_percent": 25.0}

    def test_start_collection_resets_previous_buffers(self) -> None:
        collector = DataCollector()
        collector.start_collection("run-1")
        collector.record_event(event_type="one")
        collector.record_metric("m", 1.0)
        collector.record_error("e")

        collector.start_collection("run-2")
        snapshot = collector.stop_collection()
        assert snapshot.execution_id == "run-2"
        assert snapshot.events == []
        assert snapshot.metrics == {}
        assert snapshot.errors == []
