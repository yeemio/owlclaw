"""Execution engine for e2e validation scenarios."""

from __future__ import annotations

import inspect
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

from owlclaw.e2e.data_collector import DataCollector
from owlclaw.e2e.models import ExecutionResult, ExecutionStatus, TestScenario

ScenarioRunner = Callable[[TestScenario], dict[str, Any] | Awaitable[dict[str, Any]]]


class ExecutionEngine:
    """Execute test scenarios and capture execution trace."""

    def __init__(self, runner: ScenarioRunner | None = None) -> None:
        self._runner = runner
        self._collector = DataCollector()

    async def execute_scenario(self, scenario: TestScenario) -> ExecutionResult:
        """Execute one scenario and return normalized result."""
        execution_id = f"{scenario.scenario_id}-{uuid.uuid4().hex[:8]}"
        started_at = datetime.now(timezone.utc)
        self._collector.start_collection(execution_id)
        self._collector.record_event(
            event_type="scenario.started",
            message=f"scenario={scenario.scenario_id}",
            data={"scenario_type": scenario.scenario_type.value},
        )
        self._collector.record_trace(
            {
                "phase": "start",
                "scenario_id": scenario.scenario_id,
                "timestamp": started_at.isoformat(),
            }
        )

        status = ExecutionStatus.PASSED
        output: dict[str, Any] = {}
        errors: list[str] = []
        try:
            if self._runner is None:
                status = ExecutionStatus.SKIPPED
                output = {"reason": "runner_not_configured"}
            else:
                maybe_result = self._runner(scenario)
                result = await maybe_result if inspect.isawaitable(maybe_result) else maybe_result
                if not isinstance(result, dict):
                    raise TypeError("runner must return a dictionary")
                output = dict(result)
                raw_status = str(result.get("status", "passed")).lower()
                status = {
                    "passed": ExecutionStatus.PASSED,
                    "failed": ExecutionStatus.FAILED,
                    "skipped": ExecutionStatus.SKIPPED,
                    "error": ExecutionStatus.ERROR,
                }.get(raw_status, ExecutionStatus.PASSED)
        except Exception as exc:
            status = ExecutionStatus.ERROR
            errors.append(str(exc))
            self._collector.record_error(str(exc))
            self._collector.record_event(
                event_type="scenario.error",
                message=str(exc),
                data={"scenario_id": scenario.scenario_id},
            )
            self._collector.record_trace(
                {
                    "phase": "error",
                    "scenario_id": scenario.scenario_id,
                    "error": str(exc),
                }
            )

        ended_at = datetime.now(timezone.utc)
        duration_ms = max(0.0, (ended_at - started_at).total_seconds() * 1000.0)
        self._collector.record_metric("duration_ms", duration_ms)
        self._collector.record_event(
            event_type="scenario.completed",
            message=f"status={status.value}",
            data={"scenario_id": scenario.scenario_id, "status": status.value},
        )
        self._collector.record_trace(
            {
                "phase": "complete",
                "scenario_id": scenario.scenario_id,
                "status": status.value,
                "duration_ms": duration_ms,
            }
        )
        snapshot = self._collector.stop_collection()

        return ExecutionResult(
            scenario_id=scenario.scenario_id,
            status=status,
            started_at=started_at,
            ended_at=ended_at,
            duration_ms=duration_ms,
            events=snapshot.events,
            metrics=snapshot.metrics,
            errors=snapshot.errors + errors,
            metadata={
                "execution_id": snapshot.execution_id,
                "output": output,
                "traces": snapshot.traces,
                "resource_usage": snapshot.resource_usage,
            },
        )
