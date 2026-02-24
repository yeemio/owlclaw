from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from owlclaw.capabilities.bindings.shadow import query_shadow_results
from owlclaw.governance.ledger import LedgerQueryFilters


class _Ledger:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows
        self.last_filters: LedgerQueryFilters | None = None
        self.last_tenant_id: str | None = None

    async def query_records(self, tenant_id: str, filters: LedgerQueryFilters) -> list[object]:
        self.last_tenant_id = tenant_id
        self.last_filters = filters
        return list(self.rows)


@pytest.mark.asyncio
async def test_query_shadow_results_filters_by_mode_and_tool_name() -> None:
    now = datetime.now(UTC)
    rows = [
        SimpleNamespace(
            capability_name="fetch-order",
            run_id="run-1",
            input_params={"binding_type": "http", "mode": "shadow", "parameters": {"id": 1}},
            output_result={"mode": "shadow", "result_summary": "ok", "elapsed_ms": 12},
            status="success",
            created_at=now,
            execution_time_ms=12,
        ),
        SimpleNamespace(
            capability_name="fetch-order",
            run_id="run-2",
            input_params={"binding_type": "http", "mode": "active", "parameters": {"id": 2}},
            output_result={"mode": "active", "result_summary": "ok", "elapsed_ms": 10},
            status="success",
            created_at=now,
            execution_time_ms=10,
        ),
    ]
    ledger = _Ledger(rows)

    records = await query_shadow_results(
        ledger,
        tenant_id="default",
        tool_name="fetch-order",
        limit=50,
    )
    assert len(records) == 1
    assert records[0].run_id == "run-1"
    assert records[0].mode == "shadow"
    assert ledger.last_tenant_id == "default"
    assert ledger.last_filters is not None
    assert ledger.last_filters.capability_name == "fetch-order"
    assert ledger.last_filters.limit == 50
