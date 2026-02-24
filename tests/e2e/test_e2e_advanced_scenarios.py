"""End-to-end tests for comparison, error injection, and concurrency scenarios."""

from __future__ import annotations

import asyncio

import pytest

from owlclaw.e2e.execution_engine import ExecutionEngine
from owlclaw.e2e.models import ScenarioType
from owlclaw.e2e.models import TestScenario as E2EScenario
from owlclaw.e2e.orchestrator import TestOrchestrator


@pytest.mark.asyncio
async def test_e2e_decision_comparison_flow() -> None:
    orchestrator = TestOrchestrator(
        primary_engine=ExecutionEngine(),
        baseline_engine=ExecutionEngine(),
    )
    scenarios = [
        E2EScenario(scenario_id="cmp-1", name="cmp-1", scenario_type=ScenarioType.MIONYEE_TASK),
        E2EScenario(scenario_id="cmp-2", name="cmp-2", scenario_type=ScenarioType.MIONYEE_TASK),
    ]
    result = await orchestrator.run_decision_comparison(scenarios)
    assert result["total_scenarios"] == 2
    assert len(result["comparisons"]) == 2
    assert "decision_quality_diff" in result["comparisons"][0]


@pytest.mark.asyncio
async def test_e2e_error_injection_flow() -> None:
    engine = ExecutionEngine()
    engine.inject_error("agent_runtime", "network_failure")
    orchestrator = TestOrchestrator(primary_engine=engine)
    result = await orchestrator.run_mionyee_task("err-1", {"symbol": "TSLA"})
    assert result["status"] == "error"
    assert result["rollback_triggered"] is True
    assert result["output"]["failed_component"] == "agent_runtime"
    assert result["output"]["error_type"] == "network_failure"


@pytest.mark.asyncio
async def test_e2e_concurrency_flow() -> None:
    async def runner(scenario: E2EScenario) -> dict[str, object]:
        await asyncio.sleep(0.001)
        return {"status": "passed", "scenario_id": scenario.scenario_id}

    engine = ExecutionEngine(runner=runner)
    scenarios = [
        E2EScenario(
            scenario_id=f"con-{idx}",
            name=f"con-{idx}",
            scenario_type=ScenarioType.CONCURRENCY,
            input_data={"resource": f"r-{idx % 2}"},
        )
        for idx in range(10)
    ]
    results = await engine.execute_scenarios_concurrently(scenarios, max_concurrency=5)
    assert len(results) == 10
    assert {item.scenario_id for item in results} == {item.scenario_id for item in scenarios}
    assert all(item.status.value == "passed" for item in results)

