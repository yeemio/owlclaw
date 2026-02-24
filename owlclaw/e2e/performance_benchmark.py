"""Performance benchmark management for e2e validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Threshold:
    """Inclusive threshold range for one metric."""

    min_value: float
    max_value: float


class PerformanceBenchmarkManager:
    """Manage thresholds, evaluate warnings, and compute metric trends."""

    def __init__(self) -> None:
        self._thresholds: dict[str, Threshold] = {}

    def set_threshold(self, metric_name: str, min_value: float, max_value: float) -> None:
        """Set threshold range for one metric."""
        if min_value > max_value:
            raise ValueError("min_value cannot be greater than max_value")
        self._thresholds[metric_name] = Threshold(min_value=float(min_value), max_value=float(max_value))

    def update_threshold(self, metric_name: str, min_value: float, max_value: float) -> None:
        """Update threshold for one metric."""
        self.set_threshold(metric_name, min_value, max_value)

    def get_threshold(self, metric_name: str) -> Threshold | None:
        """Get current threshold for one metric."""
        return self._thresholds.get(metric_name)

    def evaluate(self, metrics: dict[str, float]) -> list[dict[str, Any]]:
        """Evaluate metrics against thresholds and return warning list."""
        warnings: list[dict[str, Any]] = []
        for metric_name, threshold in self._thresholds.items():
            value = metrics.get(metric_name)
            if value is None:
                continue
            numeric_value = float(value)
            if threshold.min_value <= numeric_value <= threshold.max_value:
                continue
            warnings.append(
                {
                    "metric": metric_name,
                    "value": numeric_value,
                    "min": threshold.min_value,
                    "max": threshold.max_value,
                    "severity": "high" if abs(numeric_value - threshold.max_value) > 2.0 else "medium",
                }
            )
        return warnings

    def analyze_trend(self, history: list[dict[str, float]], metric_name: str) -> dict[str, Any]:
        """Analyze trend direction and slope for one metric history."""
        series = [float(item[metric_name]) for item in history if metric_name in item]
        if len(series) < 2:
            return {"metric": metric_name, "samples": len(series), "direction": "flat", "slope": 0.0}

        index_delta = float(len(series) - 1)
        slope = (series[-1] - series[0]) / index_delta
        if slope > 0.0:
            direction = "up"
        elif slope < 0.0:
            direction = "down"
        else:
            direction = "flat"

        return {
            "metric": metric_name,
            "samples": len(series),
            "direction": direction,
            "slope": slope,
            "current": series[-1],
            "baseline": series[0],
        }
