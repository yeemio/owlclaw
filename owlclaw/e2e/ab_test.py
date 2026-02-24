"""A/B testing utilities for migration_weight control."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import UTC, datetime
from statistics import mean
from typing import Any


@dataclass
class ABOutcome:
    """One recorded A/B outcome sample."""

    run_id: str
    agent_id: str
    group: str
    metrics: dict[str, float]
    timestamp: datetime


@dataclass
class ABTestResult:
    """Statistical test result for one metric."""

    agent_mean: float
    fallback_mean: float
    p_value: float
    significant: bool
    recommendation: str


class ABTestRunner:
    """Run A/B sampling and significance checks for migration_weight decisions."""

    def __init__(self) -> None:
        self._outcomes: list[ABOutcome] = []

    async def should_use_agent(self, migration_weight: float) -> bool:
        """Randomly assign one run to agent or fallback group."""
        if migration_weight < 0.0 or migration_weight > 1.0:
            raise ValueError("migration_weight must be between 0.0 and 1.0")
        return random.random() < migration_weight

    async def record_outcome(self, run_id: str, agent_id: str, group: str, metrics: dict[str, Any]) -> None:
        """Record one A/B outcome sample."""
        if group not in {"agent", "fallback"}:
            raise ValueError("group must be agent or fallback")
        normalized = {key: float(value) for key, value in metrics.items()}
        self._outcomes.append(
            ABOutcome(
                run_id=run_id,
                agent_id=agent_id,
                group=group,
                metrics=normalized,
                timestamp=datetime.now(UTC),
            )
        )

    async def statistical_test(self, agent_id: str, metric_name: str) -> ABTestResult:
        """Run approximate two-sample t-test and produce adjustment recommendation."""
        agent_values = self._metric_values(agent_id, "agent", metric_name)
        fallback_values = self._metric_values(agent_id, "fallback", metric_name)
        if not agent_values or not fallback_values:
            raise ValueError("insufficient samples for statistical test")

        agent_mean = mean(agent_values)
        fallback_mean = mean(fallback_values)
        t_score = _t_score(agent_values, fallback_values)
        p_value = _two_tailed_p_value(t_score)
        significant = p_value < 0.05
        if significant and agent_mean > fallback_mean:
            recommendation = "increase_weight"
        elif significant and agent_mean < fallback_mean:
            recommendation = "rollback_weight"
        else:
            recommendation = "hold"
        return ABTestResult(
            agent_mean=agent_mean,
            fallback_mean=fallback_mean,
            p_value=p_value,
            significant=significant,
            recommendation=recommendation,
        )

    async def auto_adjust_weight(self, current_weight: float, result: ABTestResult) -> float:
        """Adjust migration weight based on A/B result recommendation."""
        if result.recommendation == "increase_weight":
            return min(1.0, current_weight + 0.1)
        if result.recommendation == "rollback_weight":
            return 0.0
        return current_weight

    def _metric_values(self, agent_id: str, group: str, metric_name: str) -> list[float]:
        values: list[float] = []
        for outcome in self._outcomes:
            if outcome.agent_id != agent_id or outcome.group != group:
                continue
            if metric_name in outcome.metrics:
                values.append(float(outcome.metrics[metric_name]))
        return values


def _variance(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = mean(values)
    return sum((value - m) ** 2 for value in values) / (len(values) - 1)


def _t_score(sample_a: list[float], sample_b: list[float]) -> float:
    var_a = _variance(sample_a)
    var_b = _variance(sample_b)
    denom = math.sqrt((var_a / len(sample_a)) + (var_b / len(sample_b)))
    if denom == 0.0:
        if mean(sample_a) == mean(sample_b):
            return 0.0
        return math.inf
    return (mean(sample_a) - mean(sample_b)) / denom


def _two_tailed_p_value(t_score: float) -> float:
    # Normal approximation for p-value; enough for rollout heuristic decisions.
    z = abs(t_score)
    cdf = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    return max(0.0, min(1.0, 2.0 * (1.0 - cdf)))
