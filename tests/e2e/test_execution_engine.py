"""Unit tests for e2e ExecutionEngine."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

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
        assert output["failed_component"] == "cron_trigger"
        assert output["error_type"] == "component_failure"
        assert output["recovered"] is False

    @pytest.mark.asyncio
    async def test_inject_error_for_component(self) -> None:
        engine = ExecutionEngine()
        engine.inject_error("cron_trigger", "timeout")
        scenario = E2ETestScenario(
            scenario_id="m3",
            name="mionyee task with injected error",
            scenario_type=ScenarioType.MIONYEE_TASK,
        )

        result = await engine.execute_scenario(scenario)
        assert result.status == ExecutionStatus.ERROR
        output = result.metadata["output"]
        assert output["status"] == "error"
        assert output["failed_component"] == "cron_trigger"
        assert output["error_type"] == "timeout"
        assert output["error_propagation"] == []
        assert output["recovery_time_ms"] >= 0.0

    @pytest.mark.asyncio
    async def test_cleanup_removes_error_injection(self) -> None:
        engine = ExecutionEngine()
        engine.inject_error("agent_runtime", "network_failure")
        engine.cleanup()
        scenario = E2ETestScenario(
            scenario_id="m4",
            name="mionyee task after cleanup",
            scenario_type=ScenarioType.MIONYEE_TASK,
        )

        result = await engine.execute_scenario(scenario)
        assert result.status == ExecutionStatus.PASSED
        assert result.metadata["output"]["status"] == "passed"

    def test_inject_error_rejects_unknown_inputs(self) -> None:
        engine = ExecutionEngine()
        with pytest.raises(ValueError):
            engine.inject_error("unknown_component", "timeout")
        with pytest.raises(ValueError):
            engine.inject_error("cron_trigger", "unknown_error")


class TestExecutionEngineProperties:
    @settings(max_examples=100, deadline=None)
    @given(
        task_id=st.sampled_from(["1", "2", "3"]),
        params=st.recursive(
            st.none() | st.booleans() | st.integers() | st.text(max_size=20),
            lambda children: st.lists(children, max_size=5)
            | st.dictionaries(st.text(min_size=1, max_size=10), children, max_size=5),
            max_leaves=20,
        ),
    )
    @pytest.mark.asyncio
    async def test_property_mionyee_flow_contains_all_components(
        self,
        task_id: str,
        params: object,
    ) -> None:
        """Property 1: flow includes cron->agent->skills->governance->hatchet."""
        scenario = E2ETestScenario(
            scenario_id=task_id,
            name=f"task-{task_id}",
            scenario_type=ScenarioType.MIONYEE_TASK,
            input_data={"payload": params},
        )
        engine = ExecutionEngine()
        result = await engine.execute_scenario(scenario)
        assert result.status == ExecutionStatus.PASSED

        traces = result.metadata["traces"]
        phases = {trace.get("phase") for trace in traces}
        assert "cron_trigger" in phases
        assert "agent_runtime" in phases
        assert "skills_system" in phases
        assert "governance_layer" in phases
        assert "hatchet_integration" in phases

    @settings(max_examples=100, deadline=None)
    @given(
        task_id=st.sampled_from(["1", "2", "3"]),
        params=st.recursive(
            st.none() | st.booleans() | st.integers() | st.text(max_size=20),
            lambda children: st.lists(children, max_size=5)
            | st.dictionaries(st.text(min_size=1, max_size=10), children, max_size=5),
            max_leaves=20,
        ),
    )
    @pytest.mark.asyncio
    async def test_property_execution_trace_contains_input_and_output(
        self,
        task_id: str,
        params: object,
    ) -> None:
        """Property 2: each component trace includes input and output."""
        scenario = E2ETestScenario(
            scenario_id=task_id,
            name=f"task-{task_id}",
            scenario_type=ScenarioType.MIONYEE_TASK,
            input_data={"payload": params},
        )
        engine = ExecutionEngine()
        result = await engine.execute_scenario(scenario)
        assert result.status == ExecutionStatus.PASSED

        component_phases = {
            "cron_trigger",
            "agent_runtime",
            "skills_system",
            "governance_layer",
            "hatchet_integration",
        }
        traces = [trace for trace in result.metadata["traces"] if trace.get("phase") in component_phases]
        assert len(traces) == 5
        for trace in traces:
            assert "input" in trace
            assert "output" in trace

    @settings(max_examples=100, deadline=None)
    @given(
        component=st.sampled_from(
            ["cron_trigger", "agent_runtime", "skills_system", "governance_layer", "hatchet_integration"]
        ),
        error_type=st.sampled_from(["timeout", "network_failure", "resource_exhausted"]),
    )
    @pytest.mark.asyncio
    async def test_property_error_injection_supported_for_all_components(
        self,
        component: str,
        error_type: str,
    ) -> None:
        """Property 24: all supported error types are injectable for all components."""
        scenario = E2ETestScenario(
            scenario_id="error-inject",
            name="error injection",
            scenario_type=ScenarioType.MIONYEE_TASK,
        )
        engine = ExecutionEngine()
        engine.inject_error(component, error_type)
        result = await engine.execute_scenario(scenario)

        assert result.status == ExecutionStatus.ERROR
        output = result.metadata["output"]
        assert output["status"] == "error"
        assert output["failed_component"] == component
        assert output["error_type"] == error_type
        assert output["recovery_time_ms"] >= 0.0

    @settings(max_examples=100, deadline=None)
    @given(
        component=st.sampled_from(
            ["cron_trigger", "agent_runtime", "skills_system", "governance_layer", "hatchet_integration"]
        ),
        params=st.dictionaries(st.text(min_size=1, max_size=10), st.integers(), max_size=5),
    )
    @pytest.mark.asyncio
    async def test_property_error_handling_records_propagation_and_recovery(
        self,
        component: str,
        params: dict[str, int],
    ) -> None:
        """Property 25: error handling records propagation path and recovery timing."""
        scenario = E2ETestScenario(
            scenario_id="error-handling",
            name="error handling",
            scenario_type=ScenarioType.MIONYEE_TASK,
            input_data={"payload": params},
        )
        engine = ExecutionEngine()
        engine.inject_error(component, "network_failure")
        result = await engine.execute_scenario(scenario)

        assert result.status == ExecutionStatus.ERROR
        output = result.metadata["output"]
        assert output["recovered"] is False
        assert isinstance(output["error_propagation"], list)
        assert output["recovery_time_ms"] >= 0.0

    @settings(max_examples=100, deadline=None)
    @given(
        component=st.sampled_from(
            ["cron_trigger", "agent_runtime", "skills_system", "governance_layer", "hatchet_integration"]
        ),
        error_type=st.sampled_from(["timeout", "network_failure", "resource_exhausted"]),
    )
    @pytest.mark.asyncio
    async def test_property_cleanup_clears_test_data_and_temp_resources(
        self,
        component: str,
        error_type: str,
    ) -> None:
        """Property 14: cleanup removes injected faults and restores executable state."""
        scenario = E2ETestScenario(
            scenario_id="cleanup",
            name="cleanup",
            scenario_type=ScenarioType.MIONYEE_TASK,
        )
        engine = ExecutionEngine()
        engine.inject_error(component, error_type)
        engine.cleanup()
        result = await engine.execute_scenario(scenario)

        assert result.status == ExecutionStatus.PASSED
        assert result.metadata["output"]["status"] == "passed"
