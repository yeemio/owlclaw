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
ComponentFn = Callable[[dict[str, Any]], dict[str, Any] | Awaitable[dict[str, Any]]]


class ExecutionEngine:
    """Execute test scenarios and capture execution trace."""

    def __init__(self, runner: ScenarioRunner | None = None) -> None:
        self._runner = runner
        self._collector = DataCollector()
        self._cron_trigger: ComponentFn | None = None
        self._agent_runtime: ComponentFn | None = None
        self._skills_system: ComponentFn | None = None
        self._governance_layer: ComponentFn | None = None
        self._hatchet_integration: ComponentFn | None = None

    def configure_mionyee_components(
        self,
        *,
        cron_trigger: ComponentFn | None = None,
        agent_runtime: ComponentFn | None = None,
        skills_system: ComponentFn | None = None,
        governance_layer: ComponentFn | None = None,
        hatchet_integration: ComponentFn | None = None,
    ) -> None:
        """Configure component adapters for mionyee task execution."""
        self._cron_trigger = cron_trigger
        self._agent_runtime = agent_runtime
        self._skills_system = skills_system
        self._governance_layer = governance_layer
        self._hatchet_integration = hatchet_integration

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
                if scenario.scenario_type.value == "mionyee_task":
                    output = await self.execute_mionyee_task(
                        task_id=scenario.scenario_id,
                        params=scenario.input_data,
                    )
                    raw_status = str(output.get("status", "passed")).lower()
                    status = {
                        "passed": ExecutionStatus.PASSED,
                        "failed": ExecutionStatus.FAILED,
                        "skipped": ExecutionStatus.SKIPPED,
                        "error": ExecutionStatus.ERROR,
                    }.get(raw_status, ExecutionStatus.PASSED)
                else:
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

    async def execute_mionyee_task(
        self,
        task_id: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute mionyee task flow through integrated components."""
        payload: dict[str, Any] = {"task_id": task_id, "params": params or {}}
        try:
            cron_out = await self._invoke_component("cron_trigger", self._cron_trigger, payload)
            payload["cron"] = cron_out

            agent_out = await self._invoke_component("agent_runtime", self._agent_runtime, payload)
            payload["agent"] = agent_out

            skills_out = await self._invoke_component("skills_system", self._skills_system, payload)
            payload["skills"] = skills_out

            governance_out = await self._invoke_component("governance_layer", self._governance_layer, payload)
            payload["governance"] = governance_out

            hatchet_out = await self._invoke_component("hatchet_integration", self._hatchet_integration, payload)
            payload["hatchet"] = hatchet_out
        except Exception as exc:
            return {
                "status": "error",
                "task_id": task_id,
                "error": str(exc),
            }

        skills_invoked = skills_out.get("skills", []) if isinstance(skills_out, dict) else []
        governance_checks = governance_out.get("checks", []) if isinstance(governance_out, dict) else []
        workflow_id = hatchet_out.get("workflow_id") if isinstance(hatchet_out, dict) else None
        return {
            "status": "passed",
            "task_id": task_id,
            "cron_triggered": bool(cron_out.get("triggered", True)) if isinstance(cron_out, dict) else True,
            "agent_runtime_processed": bool(agent_out.get("processed", True)) if isinstance(agent_out, dict) else True,
            "skills_invoked": skills_invoked if isinstance(skills_invoked, list) else [],
            "governance_checks": governance_checks if isinstance(governance_checks, list) else [],
            "hatchet_workflow_id": workflow_id,
        }

    async def _invoke_component(
        self,
        name: str,
        fn: ComponentFn | None,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._collector.record_event(event_type=f"{name}.start", data={"task_id": payload.get("task_id")})
        if fn is None:
            result: dict[str, Any] = {"status": "simulated"}
        else:
            maybe_result = fn(payload)
            invoked = await maybe_result if inspect.isawaitable(maybe_result) else maybe_result
            if not isinstance(invoked, dict):
                raise TypeError(f"{name} must return dict")
            result = dict(invoked)
        self._collector.record_event(event_type=f"{name}.complete", data={"result": result})
        self._collector.record_trace({"phase": name, "result": result})
        return result
