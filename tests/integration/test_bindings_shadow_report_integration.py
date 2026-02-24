from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest

from owlclaw.capabilities.bindings import (
    BindingExecutor,
    BindingExecutorRegistry,
    BindingTool,
    HTTPBindingConfig,
    query_shadow_results,
)
from owlclaw.capabilities.bindings.schema import BindingConfig
from owlclaw.e2e.report_generator import ReportGenerator
from owlclaw.governance.ledger import LedgerQueryFilters


class _ShadowExecutor(BindingExecutor):
    async def execute(self, config: BindingConfig, parameters: dict[str, Any]) -> dict[str, Any]:
        return {"status": "shadow", "mode": "shadow", "sent": False, "parameters": parameters}

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        return []

    @property
    def supported_modes(self) -> list[str]:
        return ["active", "shadow"]


class _InMemoryLedger:
    def __init__(self) -> None:
        self.rows: list[Any] = []

    async def record_execution(
        self,
        tenant_id: str,
        agent_id: str,
        run_id: str,
        capability_name: str,
        task_type: str,
        input_params: dict[str, Any],
        output_result: dict[str, Any] | None,
        decision_reasoning: str | None,
        execution_time_ms: int,
        llm_model: str,
        llm_tokens_input: int,
        llm_tokens_output: int,
        estimated_cost: Decimal,
        status: str,
        error_message: str | None = None,
    ) -> None:
        self.rows.append(
            SimpleNamespace(
                tenant_id=tenant_id,
                agent_id=agent_id,
                run_id=run_id,
                capability_name=capability_name,
                task_type=task_type,
                input_params=input_params,
                output_result=output_result,
                decision_reasoning=decision_reasoning,
                execution_time_ms=execution_time_ms,
                llm_model=llm_model,
                llm_tokens_input=llm_tokens_input,
                llm_tokens_output=llm_tokens_output,
                estimated_cost=estimated_cost,
                status=status,
                error_message=error_message,
                created_at=datetime.now(UTC),
            )
        )

    async def query_records(self, tenant_id: str, filters: LedgerQueryFilters) -> list[Any]:
        out = [row for row in self.rows if row.tenant_id == tenant_id]
        if filters.capability_name is not None:
            out = [row for row in out if row.capability_name == filters.capability_name]
        return out


@pytest.mark.asyncio
async def test_shadow_invocation_to_query_to_report_flow() -> None:
    registry = BindingExecutorRegistry()
    registry.register("http", _ShadowExecutor())

    ledger = _InMemoryLedger()
    tool = BindingTool(
        name="fetch-order",
        description="Fetch order",
        parameters_schema={"type": "object"},
        binding_config=HTTPBindingConfig(method="POST", mode="shadow", url="https://svc.local/orders"),
        executor_registry=registry,
        ledger=ledger,
    )

    result = await tool(order_id=1)
    assert result["status"] == "shadow"

    shadow_results = await query_shadow_results(
        ledger,
        tenant_id="default",
        tool_name="fetch-order",
    )
    assert len(shadow_results) == 1

    report = ReportGenerator().generate_shadow_comparison_report(
        tool_name="fetch-order",
        shadow_results=shadow_results,
    )
    assert report["summary"]["tool_name"] == "fetch-order"
    assert report["summary"]["total_shadow_runs"] == 1
    assert report["sections"][0]["title"] == "shadow_timeline"
