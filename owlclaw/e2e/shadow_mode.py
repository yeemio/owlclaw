"""Shadow mode components for safe agent rollout."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class ShadowDecisionLog:
    """Recorded agent decision in shadow mode."""

    agent_id: str
    capability: str
    args: dict[str, Any]
    timestamp: datetime


@dataclass
class CronExecutionLog:
    """Recorded cron execution output for realtime comparison."""

    agent_id: str
    capability: str
    result: dict[str, Any]
    timestamp: datetime


@dataclass
class InterceptResult:
    """Result returned by shadow mode interceptor."""

    executed: bool
    simulated_result: dict[str, Any]


@dataclass
class ComparisonEntry:
    """One realtime comparison between shadow decision and cron result."""

    agent_id: str
    timestamp: datetime
    capability: str
    consistent: bool
    shadow_args: dict[str, Any]
    cron_result: dict[str, Any]


@dataclass
class ShadowDashboardMetrics:
    """Dashboard metrics for a shadow mode time range."""

    consistency_rate: float
    total_comparisons: int
    consistent_decisions: int
    inconsistent_decisions: list[dict[str, Any]]
    quality_trend: list[float]
    cumulative_llm_cost: float
    recommendation: str | None


class ShadowModeInterceptor:
    """Intercept capability execution and store decision logs without side effects."""

    def __init__(self) -> None:
        self._logs: list[ShadowDecisionLog] = []

    async def intercept(self, agent_id: str, capability_name: str, args: dict[str, Any]) -> InterceptResult:
        """Record a shadow decision and return simulated success."""
        entry = ShadowDecisionLog(
            agent_id=agent_id,
            capability=capability_name,
            args=dict(args),
            timestamp=datetime.now(timezone.utc),
        )
        self._logs.append(entry)
        return InterceptResult(
            executed=False,
            simulated_result={
                "status": "shadow_simulated",
                "capability": capability_name,
                "args": dict(args),
            },
        )

    def get_logs(self, *, agent_id: str | None = None) -> list[ShadowDecisionLog]:
        """Return recorded logs for all agents or one agent."""
        if agent_id is None:
            return list(self._logs)
        return [log for log in self._logs if log.agent_id == agent_id]


class ShadowComparator:
    """Compare shadow decisions with real cron executions."""

    def __init__(self) -> None:
        self._entries: list[ComparisonEntry] = []

    async def compare_realtime(self, agent_decision: ShadowDecisionLog, cron_result: CronExecutionLog) -> ComparisonEntry:
        """Store and return one realtime comparison entry."""
        consistent = agent_decision.capability == cron_result.capability
        entry = ComparisonEntry(
            agent_id=agent_decision.agent_id,
            timestamp=max(agent_decision.timestamp, cron_result.timestamp),
            capability=agent_decision.capability,
            consistent=consistent,
            shadow_args=dict(agent_decision.args),
            cron_result=dict(cron_result.result),
        )
        self._entries.append(entry)
        return entry

    async def get_dashboard_metrics(
        self,
        agent_id: str,
        time_range: tuple[datetime, datetime],
    ) -> ShadowDashboardMetrics:
        """Compute dashboard metrics over the selected time range."""
        start, end = time_range
        entries = [
            entry
            for entry in self._entries
            if entry.agent_id == agent_id and start <= entry.timestamp <= end
        ]
        total = len(entries)
        consistent_count = sum(1 for entry in entries if entry.consistent)
        rate = (consistent_count / total) if total else 0.0
        trend: list[float] = []
        running = 0
        for index, entry in enumerate(entries, start=1):
            if entry.consistent:
                running += 1
            trend.append(running / index)
        inconsistent = [
            {
                "timestamp": entry.timestamp.isoformat(),
                "capability": entry.capability,
                "shadow_args": entry.shadow_args,
                "cron_result": entry.cron_result,
            }
            for entry in entries
            if not entry.consistent
        ]
        recommendation = "ready_to_switch" if total >= 7 and rate >= 0.9 else None
        return ShadowDashboardMetrics(
            consistency_rate=rate,
            total_comparisons=total,
            consistent_decisions=consistent_count,
            inconsistent_decisions=inconsistent,
            quality_trend=trend,
            cumulative_llm_cost=0.0,
            recommendation=recommendation,
        )


class MigrationWeightController:
    """Adjust migration_weight based on shadow consistency metrics."""

    def __init__(self, *, shadow_comparator: ShadowComparator, current_weight: float = 0.0) -> None:
        self.shadow_comparator = shadow_comparator
        self.current_weight = current_weight

    async def evaluate_and_adjust(
        self,
        agent_id: str,
        *,
        time_range: tuple[datetime, datetime],
    ) -> float:
        """Evaluate metrics and return updated migration weight suggestion."""
        metrics = await self.shadow_comparator.get_dashboard_metrics(agent_id, time_range)
        if metrics.consistency_rate >= 0.95 and self.current_weight < 0.1:
            self.current_weight = 0.1
        elif metrics.consistency_rate >= 0.90 and self.current_weight < 0.5:
            self.current_weight = 0.5
        elif metrics.consistency_rate < 0.70:
            self.current_weight = 0.0
        return self.current_weight

