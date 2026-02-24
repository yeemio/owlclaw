"""Unit and property tests for e2e test orchestrator."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.e2e.execution_engine import ExecutionEngine
from owlclaw.e2e.models import ScenarioType
from owlclaw.e2e.models import TestScenario as E2EScenario
from owlclaw.e2e.orchestrator import TestOrchestrator as E2EOrchestrator


@pytest.mark.asyncio
async def test_run_full_validation_returns_aggregated_payload() -> None:
    orchestrator = E2EOrchestrator(primary_engine=ExecutionEngine())
    scenarios = [
        E2EScenario(scenario_id="a", name="a", scenario_type=ScenarioType.MIONYEE_TASK),
        E2EScenario(scenario_id="b", name="b", scenario_type=ScenarioType.PERFORMANCE),
    ]
    result = await orchestrator.run_full_validation(scenarios)
    assert result["total_tests"] == 2
    assert "report" in result
    assert result["state"] == "completed"


class TestOrchestratorProperties:
    @settings(max_examples=100, deadline=None)
    @given(
        task_id=st.sampled_from(["1", "2", "3"]),
        payload=st.dictionaries(st.text(min_size=1, max_size=10), st.integers(), max_size=5),
    )
    @pytest.mark.asyncio
    async def test_property_component_integration_chain_is_complete(
        self,
        task_id: str,
        payload: dict[str, int],
    ) -> None:
        """Property 9: mionyee path preserves full integration chain."""
        orchestrator = E2EOrchestrator(primary_engine=ExecutionEngine())
        result = await orchestrator.run_mionyee_task(task_id, payload)
        phases = {trace.get("phase") for trace in result["traces"]}
        assert {"cron_trigger", "agent_runtime", "skills_system", "governance_layer", "hatchet_integration"}.issubset(
            phases
        )

    @settings(max_examples=100, deadline=None)
    @given(component=st.sampled_from(["cron_trigger", "agent_runtime", "skills_system", "governance_layer"]))
    @pytest.mark.asyncio
    async def test_property_error_propagation_and_rollback(
        self,
        component: str,
    ) -> None:
        """Property 10: component error propagates and triggers rollback flag."""
        engine = ExecutionEngine()
        engine.inject_error(component, "network_failure")
        orchestrator = E2EOrchestrator(primary_engine=engine)
        result = await orchestrator.run_mionyee_task("x", {"trigger": "test"})
        assert result["status"] == "error"
        assert result["rollback_triggered"] is True
        assert isinstance(result["error_propagation"], list)
