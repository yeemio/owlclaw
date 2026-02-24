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

    @pytest.mark.asyncio
    async def test_execute_mionyee_task_happy_path(self) -> None:
        async def cron_trigger(_: dict[str, object]) -> dict[str, object]:
            return {"triggered": True}

        async def agent_runtime(_: dict[str, object]) -> dict[str, object]:
            return {"processed": True}

        async def skills_system(_: dict[str, object]) -> dict[str, object]:
            return {"skills": ["market_scan", "risk_check"]}

        async def governance_layer(_: dict[str, object]) -> dict[str, object]:
            return {"checks": ["budget_ok", "permission_ok"]}

        async def hatchet_integration(_: dict[str, object]) -> dict[str, object]:
            return {"workflow_id": "wf-1"}

        engine = ExecutionEngine()
        engine.configure_mionyee_components(
            cron_trigger=cron_trigger,
            agent_runtime=agent_runtime,
            skills_system=skills_system,
            governance_layer=governance_layer,
            hatchet_integration=hatchet_integration,
        )
        scenario = E2ETestScenario(
            scenario_id="m1",
            name="mionyee task",
            scenario_type=ScenarioType.MIONYEE_TASK,
            input_data={"symbol": "AAPL"},
        )

        result = await engine.execute_scenario(scenario)
        assert result.status == ExecutionStatus.PASSED
        output = result.metadata["output"]
        assert output["cron_triggered"] is True
        assert output["agent_runtime_processed"] is True
        assert output["skills_invoked"] == ["market_scan", "risk_check"]
        assert output["governance_checks"] == ["budget_ok", "permission_ok"]
        assert output["hatchet_workflow_id"] == "wf-1"

    @pytest.mark.asyncio
    async def test_execute_mionyee_task_component_failure(self) -> None:
        async def cron_trigger(_: dict[str, object]) -> dict[str, object]:
            raise RuntimeError("cron failed")

        engine = ExecutionEngine()
        engine.configure_mionyee_components(cron_trigger=cron_trigger)
        scenario = E2ETestScenario(
            scenario_id="m2",
            name="mionyee task",
            scenario_type=ScenarioType.MIONYEE_TASK,
        )

        result = await engine.execute_scenario(scenario)
        assert result.status == ExecutionStatus.ERROR
        output = result.metadata["output"]
        assert output["status"] == "error"
        assert "cron failed" in output["error"]
