"""Unit tests for e2e ComparisonEngine."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.e2e.comparison_engine import ComparisonEngine
from owlclaw.e2e.models import ExecutionResult, ExecutionStatus


def _build_result(
    *,
    scenario_id: str,
    status: ExecutionStatus,
    duration_ms: float,
    throughput: float,
) -> ExecutionResult:
    now = datetime.now(UTC)
    return ExecutionResult(
        scenario_id=scenario_id,
        status=status,
        started_at=now,
        ended_at=now + timedelta(milliseconds=duration_ms),
        duration_ms=duration_ms,
        events=[],
        metrics={"throughput": throughput},
        errors=[],
        metadata={"traces": [{"phase": "done"}], "resource_usage": {"cpu": 10.0, "memory": 20.0}},
    )


def test_compare_returns_expected_shape() -> None:
    engine = ComparisonEngine()
    v3 = _build_result(scenario_id="s1", status=ExecutionStatus.PASSED, duration_ms=100.0, throughput=20.0)
    cron = _build_result(scenario_id="s1", status=ExecutionStatus.PASSED, duration_ms=200.0, throughput=10.0)

    result = engine.compare(v3, cron)
    assert result["scenario_id"] == "s1"
    assert result["v3_agent_result"].scenario_id == "s1"
    assert result["original_cron_result"].scenario_id == "s1"
    assert "decision_quality_diff" in result
    assert "performance_diff" in result
    assert isinstance(result["anomalies"], list)


def test_detect_anomalies_when_diff_exceeds_threshold() -> None:
    engine = ComparisonEngine()
    comparison = {
        "decision_quality_diff": {"accuracy_diff": 10.0},
        "performance_diff": {"response_time_diff": 50.0},
    }
    anomalies = engine.detect_anomalies(comparison, threshold=20.0)
    assert len(anomalies) == 1
    assert anomalies[0]["affected_metrics"] == ["response_time_diff"]


class TestComparisonEngineProperties:
    @settings(max_examples=100, deadline=None)
    @given(
        v3_status=st.sampled_from([ExecutionStatus.PASSED, ExecutionStatus.FAILED, ExecutionStatus.ERROR]),
        cron_status=st.sampled_from([ExecutionStatus.PASSED, ExecutionStatus.FAILED, ExecutionStatus.ERROR]),
        v3_duration=st.floats(min_value=0.0, max_value=20000.0, allow_nan=False, allow_infinity=False),
        cron_duration=st.floats(min_value=0.0, max_value=20000.0, allow_nan=False, allow_infinity=False),
    )
    def test_property_dual_system_execution_produces_decision_outputs(
        self,
        v3_status: ExecutionStatus,
        cron_status: ExecutionStatus,
        v3_duration: float,
        cron_duration: float,
    ) -> None:
        """Property 4: both V3 and Original Cron produce decision outputs in comparison flow."""
        engine = ComparisonEngine()
        v3 = _build_result(scenario_id="cmp", status=v3_status, duration_ms=v3_duration, throughput=12.0)
        cron = _build_result(scenario_id="cmp", status=cron_status, duration_ms=cron_duration, throughput=10.0)
        result = engine.compare(v3, cron)

        assert result["v3_agent_result"] is not None
        assert result["original_cron_result"] is not None
        assert "decision_quality_diff" in result
        assert "performance_diff" in result

    @settings(max_examples=100, deadline=None)
    @given(
        duration=st.floats(min_value=0.0, max_value=30000.0, allow_nan=False, allow_infinity=False),
        status=st.sampled_from([ExecutionStatus.PASSED, ExecutionStatus.FAILED, ExecutionStatus.ERROR]),
    )
    def test_property_decision_metrics_are_complete(
        self,
        duration: float,
        status: ExecutionStatus,
    ) -> None:
        """Property 5: decision quality metrics include all required fields."""
        engine = ComparisonEngine()
        result = _build_result(scenario_id="metrics", status=status, duration_ms=duration, throughput=1.0)
        quality = engine.calculate_decision_quality(result)

        required_keys = {"accuracy", "response_time", "resource_efficiency", "error_rate", "completeness"}
        assert required_keys.issubset(set(quality.keys()))

    @settings(max_examples=100, deadline=None)
    @given(
        v3_metric=st.floats(min_value=0.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
        cron_metric=st.floats(min_value=0.1, max_value=10000.0, allow_nan=False, allow_infinity=False),
    )
    def test_property_percentage_diff_uses_expected_formula(
        self,
        v3_metric: float,
        cron_metric: float,
    ) -> None:
        """Property 6: diff follows (v3 - cron) / cron * 100."""
        engine = ComparisonEngine()
        diff = engine.compare_performance(
            {
                "response_time": v3_metric,
                "throughput": v3_metric,
                "cpu_usage": v3_metric,
                "memory_usage": v3_metric,
            },
            {
                "response_time": cron_metric,
                "throughput": cron_metric,
                "cpu_usage": cron_metric,
                "memory_usage": cron_metric,
            },
        )
        expected = ((v3_metric - cron_metric) / cron_metric) * 100.0
        assert diff["response_time_diff"] == pytest.approx(expected)
        assert diff["throughput_diff"] == pytest.approx(expected)
        assert diff["cpu_usage_diff"] == pytest.approx(expected)
        assert diff["memory_usage_diff"] == pytest.approx(expected)

    @settings(max_examples=100, deadline=None)
    @given(
        metric_value=st.floats(min_value=-200.0, max_value=200.0, allow_nan=False, allow_infinity=False),
        threshold=st.floats(min_value=1.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    )
    def test_property_anomaly_detection_respects_threshold(
        self,
        metric_value: float,
        threshold: float,
    ) -> None:
        """Property 8: anomaly is raised when absolute diff exceeds threshold."""
        engine = ComparisonEngine()
        comparison = {
            "decision_quality_diff": {"accuracy_diff": metric_value},
            "performance_diff": {},
        }
        anomalies = engine.detect_anomalies(comparison, threshold=threshold)
        if abs(metric_value) > threshold:
            assert len(anomalies) == 1
            assert anomalies[0]["affected_metrics"] == ["accuracy_diff"]
        else:
            assert anomalies == []
