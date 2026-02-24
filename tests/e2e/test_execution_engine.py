"""Unit tests for e2e ExecutionEngine."""

from __future__ import annotations

import pytest

from owlclaw.e2e.execution_engine import ExecutionEngine
from owlclaw.e2e.models import ExecutionStatus, ScenarioType
from owlclaw.e2e.models import TestScenario as E2ETestScenario


class TestExecutionEngine:
    @pytest.mark.asyncio
    async def test_execute_scenario_with_runner_records_trace(self) -> None:
        async def runner(scenario: E2ETestScenario) -> dict[str, object]:
            return {"status": "passed", "result": {"scenario": scenario.scenario_id}}

        engine = ExecutionEngine(runner=runner)
        scenario = E2ETestScenario(
            scenario_id="s1",
            name="scenario",
            scenario_type=ScenarioType.INTEGRATION,
        )
        result = await engine.execute_scenario(scenario)

        assert result.status == ExecutionStatus.PASSED
        assert result.metrics["duration_ms"] >= 0.0
        assert len(result.events) >= 2
        assert result.metadata["output"]["result"] == {"scenario": "s1"}
        traces = result.metadata["traces"]
        assert isinstance(traces, list)
        assert any(trace.get("phase") == "start" for trace in traces)
        assert any(trace.get("phase") == "complete" for trace in traces)

    @pytest.mark.asyncio
    async def test_execute_scenario_without_runner_is_skipped(self) -> None:
        engine = ExecutionEngine()
        scenario = E2ETestScenario(
            scenario_id="s2",
            name="scenario",
            scenario_type=ScenarioType.PERFORMANCE,
        )
        result = await engine.execute_scenario(scenario)
        assert result.status == ExecutionStatus.SKIPPED
        assert result.metadata["output"]["reason"] == "runner_not_configured"

    @pytest.mark.asyncio
    async def test_execute_scenario_runner_error_returns_error(self) -> None:
        async def runner(_: E2ETestScenario) -> dict[str, object]:
            raise RuntimeError("boom")

        engine = ExecutionEngine(runner=runner)
        scenario = E2ETestScenario(
            scenario_id="s3",
            name="scenario",
            scenario_type=ScenarioType.MIONYEE_TASK,
        )
        result = await engine.execute_scenario(scenario)
        assert result.status == ExecutionStatus.ERROR
        assert any("boom" in err for err in result.errors)
        assert any(event.event_type == "scenario.error" for event in result.events)
