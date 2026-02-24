"""Test orchestration for e2e validation workflows."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from owlclaw.e2e.comparison_engine import ComparisonEngine
from owlclaw.e2e.execution_engine import ExecutionEngine
from owlclaw.e2e.models import ExecutionResult, ScenarioType, TestScenario
from owlclaw.e2e.report_generator import ReportGenerator


class TestOrchestrator:
    """Coordinate validation runs across e2e components."""

    __test__ = False

    def __init__(
        self,
        *,
        primary_engine: ExecutionEngine | None = None,
        baseline_engine: ExecutionEngine | None = None,
        comparison_engine: ComparisonEngine | None = None,
        report_generator: ReportGenerator | None = None,
    ) -> None:
        self._primary_engine = primary_engine or ExecutionEngine()
        self._baseline_engine = baseline_engine or ExecutionEngine()
        self._comparison_engine = comparison_engine or ComparisonEngine()
        self._report_generator = report_generator or ReportGenerator()
        self._run_state = "idle"
        self._run_started_at: datetime | None = None

    async def run_full_validation(
        self,
        scenarios: list[TestScenario],
        *,
        timeout_seconds: int = 300,
        fail_fast: bool = False,
    ) -> dict[str, Any]:
        """Run full validation and return aggregated execution + report payload."""
        self._run_state = "running"
        self._run_started_at = datetime.now(UTC)
        results: list[ExecutionResult] = []
        try:
            for scenario in scenarios:
                result = await self._execute_with_timeout(scenario, timeout_seconds=timeout_seconds)
                results.append(result)
                if fail_fast and result.status.value in {"failed", "error"}:
                    break
        finally:
            self._run_state = "completed"
        return self._aggregate_results(results)

    async def run_mionyee_task(self, task_id: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Run one mionyee scenario through full component chain."""
        scenario = TestScenario(
            scenario_id=task_id,
            name=f"mionyee-{task_id}",
            scenario_type=ScenarioType.MIONYEE_TASK,
            input_data=params or {},
        )
        result = await self._primary_engine.execute_scenario(scenario)
        payload = {
            "scenario_id": scenario.scenario_id,
            "status": result.status.value,
            "traces": result.metadata.get("traces", []),
            "output": result.metadata.get("output", {}),
            "rollback_triggered": result.status.value in {"failed", "error"},
            "error_propagation": result.metadata.get("output", {}).get("error_propagation", []),
        }
        return payload

    async def run_decision_comparison(self, scenarios: list[TestScenario]) -> dict[str, Any]:
        """Run scenario list on primary and baseline engines and compare outputs."""
        comparisons: list[dict[str, Any]] = []
        for scenario in scenarios:
            primary_result = await self._primary_engine.execute_scenario(scenario)
            baseline_result = await self._baseline_engine.execute_scenario(scenario)
            comparisons.append(self._comparison_engine.compare(primary_result, baseline_result))
        summary_report = self._report_generator.generate_comparison_report(comparisons[0]) if comparisons else {}
        return {
            "total_scenarios": len(scenarios),
            "comparisons": comparisons,
            "report": summary_report,
        }

    async def run_integration_tests(self, scenarios: list[TestScenario]) -> dict[str, Any]:
        """Run integration scenario set and produce validation report."""
        integration_scenarios = [scenario for scenario in scenarios if scenario.scenario_type == ScenarioType.INTEGRATION]
        results = await self._primary_engine.execute_scenarios_concurrently(integration_scenarios, max_concurrency=4)
        return self._aggregate_results(results)

    def start_validation(self) -> None:
        """Mark orchestrator state as running."""
        self._run_state = "running"
        self._run_started_at = datetime.now(UTC)

    def stop_validation(self) -> None:
        """Stop current orchestration lifecycle."""
        self._run_state = "stopped"

    def get_state(self) -> dict[str, Any]:
        """Return lifecycle state for current run."""
        return {
            "state": self._run_state,
            "started_at": self._run_started_at.isoformat() if self._run_started_at else None,
        }

    async def _execute_with_timeout(self, scenario: TestScenario, *, timeout_seconds: int) -> ExecutionResult:
        async with asyncio.timeout(timeout_seconds):
            return await self._primary_engine.execute_scenario(scenario)

    def _aggregate_results(self, results: list[ExecutionResult]) -> dict[str, Any]:
        report = self._report_generator.generate_validation_report(results)
        return {
            "total_tests": len(results),
            "passed_tests": sum(1 for result in results if result.status.value == "passed"),
            "failed_tests": sum(1 for result in results if result.status.value in {"failed", "error"}),
            "skipped_tests": sum(1 for result in results if result.status.value == "skipped"),
            "results": results,
            "report": report,
            "state": self._run_state,
        }
