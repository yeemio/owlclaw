"""Unit and property tests for performance benchmark management."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.e2e.data_collector import DataCollector
from owlclaw.e2e.performance_benchmark import PerformanceBenchmarkManager


def test_analyze_trend_returns_direction() -> None:
    manager = PerformanceBenchmarkManager()
    trend = manager.analyze_trend(
        [
            {"response_time_ms": 10.0},
            {"response_time_ms": 15.0},
            {"response_time_ms": 20.0},
        ],
        "response_time_ms",
    )
    assert trend["direction"] == "up"
    assert trend["samples"] == 3


class TestPerformanceBenchmarkProperties:
    @settings(max_examples=100, deadline=None)
    @given(
        response=st.floats(min_value=0.0, max_value=100000.0, allow_nan=False, allow_infinity=False),
        throughput=st.floats(min_value=0.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
        cpu=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        memory=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        network=st.floats(min_value=0.0, max_value=100000.0, allow_nan=False, allow_infinity=False),
        disk=st.floats(min_value=0.0, max_value=100000.0, allow_nan=False, allow_infinity=False),
    )
    def test_property_performance_metrics_collection_is_complete(
        self,
        response: float,
        throughput: float,
        cpu: float,
        memory: float,
        network: float,
        disk: float,
    ) -> None:
        """Property 20: collector records complete performance metric set."""
        collector = DataCollector()
        collector.start_collection("perf")
        collector.collect_performance_metrics(
            response_time_ms=response,
            throughput_qps=throughput,
            cpu_usage=cpu,
            memory_usage=memory,
            network_io=network,
            disk_io=disk,
        )
        snapshot = collector.stop_collection()
        required = {"response_time_ms", "throughput_qps", "cpu_usage", "memory_usage", "network_io", "disk_io"}
        assert required.issubset(snapshot.metrics.keys())

    @settings(max_examples=100, deadline=None)
    @given(
        min_value=st.floats(min_value=0.0, max_value=500.0, allow_nan=False, allow_infinity=False),
        max_value=st.floats(min_value=500.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        outside=st.floats(min_value=1001.0, max_value=5000.0, allow_nan=False, allow_infinity=False),
    )
    def test_property_warning_triggered_when_metric_exceeds_threshold(
        self,
        min_value: float,
        max_value: float,
        outside: float,
    ) -> None:
        """Property 21: warning is emitted when metric exceeds configured threshold."""
        manager = PerformanceBenchmarkManager()
        manager.set_threshold("response_time_ms", min_value=min_value, max_value=max_value)
        warnings = manager.evaluate({"response_time_ms": outside})
        assert len(warnings) == 1
        assert warnings[0]["metric"] == "response_time_ms"

    @settings(max_examples=100, deadline=None)
    @given(
        min_value=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        max_value=st.floats(min_value=100.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
    )
    def test_property_threshold_values_can_be_set_and_updated(self, min_value: float, max_value: float) -> None:
        """Property 22: benchmark threshold management supports set and update."""
        manager = PerformanceBenchmarkManager()
        manager.set_threshold("cpu_usage", min_value=min_value, max_value=max_value)
        first = manager.get_threshold("cpu_usage")
        assert first is not None
        assert first.min_value == min_value
        assert first.max_value == max_value

        manager.update_threshold("cpu_usage", min_value=min_value + 1.0, max_value=max_value + 1.0)
        second = manager.get_threshold("cpu_usage")
        assert second is not None
        assert second.min_value == min_value + 1.0
        assert second.max_value == max_value + 1.0
