"""End-to-end tests for mionyee task flows."""

from __future__ import annotations

import pytest

from owlclaw.e2e.execution_engine import ExecutionEngine
from owlclaw.e2e.orchestrator import TestOrchestrator


def _build_orchestrator() -> TestOrchestrator:
    async def cron_trigger(payload: dict[str, object]) -> dict[str, object]:
        return {"triggered": True, "task_id": payload.get("task_id")}

    async def agent_runtime(payload: dict[str, object]) -> dict[str, object]:
        return {"processed": True, "task_id": payload.get("task_id")}

    async def skills_system(_: dict[str, object]) -> dict[str, object]:
        return {"skills": ["entry-monitor", "risk-check"]}

    async def governance_layer(_: dict[str, object]) -> dict[str, object]:
        return {"checks": ["permission_ok", "budget_ok"]}

    async def hatchet_integration(payload: dict[str, object]) -> dict[str, object]:
        return {"workflow_id": f"wf-{payload.get('task_id', 'x')}"}

    engine = ExecutionEngine()
    engine.configure_mionyee_components(
        cron_trigger=cron_trigger,
        agent_runtime=agent_runtime,
        skills_system=skills_system,
        governance_layer=governance_layer,
        hatchet_integration=hatchet_integration,
    )
    return TestOrchestrator(primary_engine=engine)


@pytest.mark.asyncio
async def test_e2e_mionyee_task_1_flow() -> None:
    orchestrator = _build_orchestrator()
    result = await orchestrator.run_mionyee_task("1", {"symbol": "AAPL"})
    assert result["status"] == "passed"
    phases = {trace.get("phase") for trace in result["traces"]}
    assert {"cron_trigger", "agent_runtime", "skills_system", "governance_layer", "hatchet_integration"}.issubset(
        phases
    )


@pytest.mark.asyncio
async def test_e2e_mionyee_task_2_flow() -> None:
    orchestrator = _build_orchestrator()
    result = await orchestrator.run_mionyee_task("2", {"symbol": "MSFT"})
    assert result["status"] == "passed"
    assert result["output"]["task_id"] == "2"
    assert result["output"]["agent_runtime_processed"] is True


@pytest.mark.asyncio
async def test_e2e_mionyee_task_3_flow() -> None:
    orchestrator = _build_orchestrator()
    result = await orchestrator.run_mionyee_task("3", {"symbol": "NVDA"})
    assert result["status"] == "passed"
    assert result["output"]["task_id"] == "3"
    assert result["output"]["hatchet_workflow_id"] == "wf-3"

