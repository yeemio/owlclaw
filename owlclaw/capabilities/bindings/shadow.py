"""Shadow mode query helpers for declarative bindings."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from owlclaw.governance.ledger import LedgerQueryFilters


@dataclass(slots=True)
class ShadowExecutionRecord:
    """Normalized shadow execution view from ledger records."""

    tool_name: str
    run_id: str
    binding_type: str
    mode: str
    status: str
    parameters: dict[str, Any]
    result_summary: str
    elapsed_ms: int
    created_at: datetime | None


class LedgerQueryProtocol(Protocol):
    """Protocol for querying ledger records."""

    async def query_records(self, tenant_id: str, filters: LedgerQueryFilters) -> list[Any]:
        """Query records from governance ledger."""


async def query_shadow_results(
    ledger: LedgerQueryProtocol,
    *,
    tenant_id: str,
    tool_name: str,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    limit: int = 100,
) -> list[ShadowExecutionRecord]:
    """Query shadow-mode binding results by tool name and optional time range."""
    filters = LedgerQueryFilters(
        capability_name=tool_name,
        start_date=start_at.date() if start_at is not None else None,
        end_date=end_at.date() if end_at is not None else None,
        limit=limit,
        order_by="created_at DESC",
    )
    rows = await ledger.query_records(tenant_id, filters)
    records: list[ShadowExecutionRecord] = []
    for row in rows:
        input_params = getattr(row, "input_params", {}) or {}
        output_result = getattr(row, "output_result", {}) or {}
        mode = str(output_result.get("mode", input_params.get("mode", ""))).strip().lower()
        if mode != "shadow":
            continue
        records.append(
            ShadowExecutionRecord(
                tool_name=str(getattr(row, "capability_name", tool_name)),
                run_id=str(getattr(row, "run_id", "")),
                binding_type=str(input_params.get("binding_type", "")),
                mode=mode,
                status=str(getattr(row, "status", "")),
                parameters=input_params.get("parameters", {}) if isinstance(input_params.get("parameters"), dict) else {},
                result_summary=str(output_result.get("result_summary", "")),
                elapsed_ms=int(output_result.get("elapsed_ms", getattr(row, "execution_time_ms", 0)) or 0),
                created_at=getattr(row, "created_at", None),
            )
        )
    return records
