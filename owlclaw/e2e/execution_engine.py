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


class ComponentExecutionError(RuntimeError):
    """Structured component failure used for error propagation tracking."""

    def __init__(self, component: str, error_type: str, message: str) -> None:
        super().__init__(message)
        self.component = component
        self.error_type = error_type


class ExecutionEngine:
    """Execute test scenarios and capture execution trace."""

    def __init__(self, runner: ScenarioRunner | None = None) -> None:
        self._runner = runner
        self._collector = DataCollector()
        self._injected_errors: dict[str, str] = {}
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

    def inject_error(self, component: str, error_type: str) -> None:
        """Inject one error type for a given component."""
        component_name = component.strip().lower()
        allowed_components = {
            "cron_trigger",
            "agent_runtime",
            "skills_system",
            "governance_layer",
            "hatchet_integration",
        }
        if component_name not in allowed_components:
            raise ValueError(f"unsupported component: {component}")

        normalized_error_type = error_type.strip().lower()
        allowed_error_types = {"timeout", "network_failure", "resource_exhausted"}
        if normalized_error_type not in allowed_error_types:
            raise ValueError(f"unsupported error type: {error_type}")
        self._injected_errors[component_name] = normalized_error_type

    def cleanup(self) -> None:
        """Reset injected failures and temporary execution resources."""
        self._injected_errors.clear()
        self._collector = DataCollector()
        self._cron_trigger = None
        self._agent_runtime = None
        self._skills_system = None
        self._governance_layer = None
        self._hatchet_integration = None

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
        propagation_path: list[str] = []
        recovery_started = datetime.now(timezone.utc)
        try:
            cron_out = await self._invoke_component("cron_trigger", self._cron_trigger, payload)
            propagation_path.append("cron_trigger")
            payload["cron"] = cron_out

            agent_out = await self._invoke_component("agent_runtime", self._agent_runtime, payload)
            propagation_path.append("agent_runtime")
            payload["agent"] = agent_out

            skills_out = await self._invoke_component("skills_system", self._skills_system, payload)
            propagation_path.append("skills_system")
            payload["skills"] = skills_out

            governance_out = await self._invoke_component("governance_layer", self._governance_layer, payload)
            propagation_path.append("governance_layer")
            payload["governance"] = governance_out

            hatchet_out = await self._invoke_component("hatchet_integration", self._hatchet_integration, payload)
            propagation_path.append("hatchet_integration")
            payload["hatchet"] = hatchet_out
        except ComponentExecutionError as exc:
            recovery_finished = datetime.now(timezone.utc)
            recovery_time_ms = max(0.0, (recovery_finished - recovery_started).total_seconds() * 1000.0)
            self._collector.record_event(
                event_type="recovery.attempted",
                message="recovery_not_implemented",
                data={
                    "failed_component": exc.component,
                    "error_type": exc.error_type,
                    "propagation_path": propagation_path,
                    "recovery_time_ms": recovery_time_ms,
                },
            )
            return {
                "status": "error",
                "task_id": task_id,
                "error": str(exc),
                "failed_component": exc.component,
                "error_type": exc.error_type,
                "error_propagation": propagation_path,
                "recovery_time_ms": recovery_time_ms,
                "recovered": False,
            }
        except Exception as exc:
            recovery_finished = datetime.now(timezone.utc)
            recovery_time_ms = max(0.0, (recovery_finished - recovery_started).total_seconds() * 1000.0)
            return {
                "status": "error",
                "task_id": task_id,
                "error": str(exc),
                "failed_component": "unknown",
                "error_type": "execution_error",
                "error_propagation": propagation_path,
                "recovery_time_ms": recovery_time_ms,
                "recovered": False,
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
        component_input = dict(payload)
        self._collector.record_event(
            event_type=f"{name}.start",
            data={"task_id": payload.get("task_id"), "input": component_input},
        )
        injected_error_type = self._injected_errors.get(name)
        if injected_error_type is not None:
            if injected_error_type == "timeout":
                raise ComponentExecutionError(name, injected_error_type, f"{name} timed out")
            if injected_error_type == "network_failure":
                raise ComponentExecutionError(name, injected_error_type, f"{name} network failure")
            raise ComponentExecutionError(name, injected_error_type, f"{name} resource exhausted")
        if fn is None:
            result: dict[str, Any] = {"status": "simulated"}
        else:
            try:
                maybe_result = fn(payload)
                invoked = await maybe_result if inspect.isawaitable(maybe_result) else maybe_result
                if not isinstance(invoked, dict):
                    raise TypeError(f"{name} must return dict")
                result = dict(invoked)
            except ComponentExecutionError:
                raise
            except TimeoutError as exc:
                raise ComponentExecutionError(name, "timeout", str(exc)) from exc
            except ConnectionError as exc:
                raise ComponentExecutionError(name, "network_failure", str(exc)) from exc
            except Exception as exc:
                raise ComponentExecutionError(name, "component_failure", str(exc)) from exc
        self._collector.record_event(
            event_type=f"{name}.complete",
            data={"task_id": payload.get("task_id"), "output": result},
        )
        self._collector.record_trace(
            {
                "phase": name,
                "input": component_input,
                "output": result,
            }
        )
        return result
