"""Unit tests for in-memory ledger migration fields."""

from __future__ import annotations

from decimal import Decimal

import pytest

from owlclaw.governance.ledger import LedgerQueryFilters
from owlclaw.governance.ledger_inmemory import InMemoryLedger


@pytest.mark.asyncio
async def test_inmemory_ledger_records_and_filters_execution_mode() -> None:
    ledger = InMemoryLedger()
    await ledger.record_execution(
        tenant_id="default",
        agent_id="agent-1",
        run_id="run-1",
        capability_name="inventory-check",
        task_type="monitor",
        input_params={},
        output_result={"action": "observe"},
        decision_reasoning=None,
        execution_time_ms=20,
        llm_model="mock",
        llm_tokens_input=0,
        llm_tokens_output=0,
        estimated_cost=Decimal("0"),
        status="success",
        migration_weight=20,
        execution_mode="pending_approval",
        risk_level=Decimal("0.2000"),
        approval_by="ops-a",
    )
    rows = await ledger.query_records(
        tenant_id="default",
        filters=LedgerQueryFilters(execution_mode="pending_approval"),
    )
    assert len(rows) == 1
    row = rows[0]
    assert row.migration_weight == 20
    assert row.execution_mode == "pending_approval"
    assert row.risk_level == Decimal("0.2000")
    assert row.approval_by == "ops-a"
