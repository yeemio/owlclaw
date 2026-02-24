"""Comparison engine for V3 Agent and Original Cron execution outputs."""

from __future__ import annotations

from typing import Any

from owlclaw.e2e.models import ExecutionResult


class ComparisonEngine:
    """Compare execution results and derive quality/performance metrics."""

    def compare(self, v3_result: ExecutionResult, cron_result: ExecutionResult) -> dict[str, Any]:
        """Build one comparison payload for two execution results."""
        v3_quality = self.calculate_decision_quality(v3_result)
        cron_quality = self.calculate_decision_quality(cron_result)
        quality_diff = {
            "accuracy_diff": self._percentage_diff(v3_quality["accuracy"], cron_quality["accuracy"]),
            "response_time_diff": self._percentage_diff(v3_quality["response_time"], cron_quality["response_time"]),
            "resource_efficiency_diff": self._percentage_diff(
                v3_quality["resource_efficiency"], cron_quality["resource_efficiency"]
            ),
            "error_rate_diff": self._percentage_diff(v3_quality["error_rate"], cron_quality["error_rate"]),
            "completeness_diff": self._percentage_diff(v3_quality["completeness"], cron_quality["completeness"]),
        }
        quality_diff["overall_improvement"] = (
            quality_diff["accuracy_diff"]
            + quality_diff["resource_efficiency_diff"]
            + quality_diff["completeness_diff"]
            - quality_diff["response_time_diff"]
            - quality_diff["error_rate_diff"]
        ) / 5.0
        performance_diff = self.compare_performance(
            {
                "response_time": v3_result.duration_ms,
                "throughput": v3_result.metrics.get("throughput", 0.0),
                "cpu_usage": v3_result.metadata.get("resource_usage", {}).get("cpu", 0.0),
                "memory_usage": v3_result.metadata.get("resource_usage", {}).get("memory", 0.0),
            },
            {
                "response_time": cron_result.duration_ms,
                "throughput": cron_result.metrics.get("throughput", 0.0),
                "cpu_usage": cron_result.metadata.get("resource_usage", {}).get("cpu", 0.0),
                "memory_usage": cron_result.metadata.get("resource_usage", {}).get("memory", 0.0),
            },
        )
        comparison = {
            "scenario_id": v3_result.scenario_id,
            "v3_agent_result": v3_result,
            "original_cron_result": cron_result,
            "decision_quality_diff": quality_diff,
            "performance_diff": performance_diff,
        }
        comparison["anomalies"] = self.detect_anomalies(comparison, threshold=20.0)
        return comparison

    def calculate_decision_quality(self, result: ExecutionResult) -> dict[str, float]:
        """Calculate quality metrics for one execution result."""
        status_factor = 1.0 if result.status.value == "passed" else 0.0
        trace_count = len(result.metadata.get("traces", []))
        error_rate = float(len(result.errors)) / max(1, len(result.events))
        resource_usage = result.metadata.get("resource_usage", {})
        cpu = float(resource_usage.get("cpu", 0.0))
        memory = float(resource_usage.get("memory", 0.0))
        resource_efficiency = max(0.0, 1.0 - ((cpu + memory) / 200.0))
        return {
            "accuracy": status_factor,
            "response_time": result.duration_ms,
            "resource_efficiency": resource_efficiency,
            "error_rate": error_rate,
            "completeness": 1.0 if trace_count > 0 else 0.0,
        }

    def compare_performance(
        self,
        v3_metrics: dict[str, float],
        cron_metrics: dict[str, float],
    ) -> dict[str, float]:
        """Compare performance metrics between v3 and cron."""
        return {
            "response_time_diff": self._percentage_diff(
                v3_metrics.get("response_time", 0.0),
                cron_metrics.get("response_time", 0.0),
            ),
            "throughput_diff": self._percentage_diff(
                v3_metrics.get("throughput", 0.0),
                cron_metrics.get("throughput", 0.0),
            ),
            "cpu_usage_diff": self._percentage_diff(
                v3_metrics.get("cpu_usage", 0.0),
                cron_metrics.get("cpu_usage", 0.0),
            ),
            "memory_usage_diff": self._percentage_diff(
                v3_metrics.get("memory_usage", 0.0),
                cron_metrics.get("memory_usage", 0.0),
            ),
        }

    def detect_anomalies(self, comparison: dict[str, Any], threshold: float) -> list[dict[str, Any]]:
        """Detect metric-level anomalies where absolute diff exceeds threshold."""
        anomalies: list[dict[str, Any]] = []
        for scope in ("decision_quality_diff", "performance_diff"):
            metrics = comparison.get(scope, {})
            if not isinstance(metrics, dict):
                continue
            for metric_name, metric_value in metrics.items():
                if not isinstance(metric_value, int | float):
                    continue
                if abs(float(metric_value)) <= threshold:
                    continue
                abs_value = abs(float(metric_value))
                if abs_value >= 100.0:
                    severity = "critical"
                elif abs_value >= 60.0:
                    severity = "high"
                elif abs_value >= 30.0:
                    severity = "medium"
                else:
                    severity = "low"
                anomalies.append(
                    {
                        "type": "metric_deviation",
                        "severity": severity,
                        "description": f"{scope}.{metric_name} deviation exceeded threshold",
                        "affected_metrics": [metric_name],
                        "value": float(metric_value),
                        "threshold": threshold,
                    }
                )
        return anomalies

    def _percentage_diff(self, v3_value: float, cron_value: float) -> float:
        baseline = float(cron_value)
        current = float(v3_value)
        if baseline == 0.0:
            return 0.0 if current == 0.0 else 100.0
        return ((current - baseline) / baseline) * 100.0
