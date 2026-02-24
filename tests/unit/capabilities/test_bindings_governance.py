from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import pytest

from owlclaw.capabilities.registry import CapabilityRegistry
from owlclaw.capabilities.skills import SkillsLoader, auto_register_binding_tools
from owlclaw.governance.constraints.budget import BudgetConstraint
from owlclaw.governance.constraints.rate_limit import RateLimitConstraint
from owlclaw.governance.constraints.risk_confirmation import RiskConfirmationConstraint
from owlclaw.governance.ledger import CostSummary, LedgerQueryFilters
from owlclaw.governance.visibility import CapabilityView, RunContext, VisibilityFilter


def _write_skill(path: Path) -> None:
    path.write_text(
        """---
name: demo-skill
description: demo
metadata:
  tools_schema:
    fetch-order:
      description: fetch order
      parameters:
        type: object
      binding:
        type: http
        method: GET
        url: https://svc.local/orders/{order_id}
owlclaw:
  task_type: trading_decision
  constraints:
    estimated_cost: 1.0
    max_daily_calls: 1
  risk_level: high
---
# Demo
""",
        encoding="utf-8",
    )


@dataclass
class _Ledger:
    total_cost: Decimal
    call_count: int

    async def get_cost_summary(self, tenant_id: str, agent_id: str, start_date, end_date) -> CostSummary:  # type: ignore[no-untyped-def]  # noqa: ANN001
        return CostSummary(total_cost=self.total_cost, by_agent={agent_id: self.total_cost}, by_capability={})

    async def query_records(self, tenant_id: str, filters: LedgerQueryFilters):  # type: ignore[no-untyped-def]  # noqa: ANN001
        return [
            type(
                "_Record",
                (),
                {"created_at": datetime.now(timezone.utc), "capability_name": filters.capability_name},
            )()
            for _ in range(self.call_count)
        ]


def _to_capability_view(data: dict[str, object]) -> CapabilityView:
    constraints: dict[str, Any] | None = None
    constraints_raw = data.get("constraints")
    if isinstance(constraints_raw, dict):
        constraints = cast(dict[str, Any], constraints_raw)
    focus: list[str] | None = None
    focus_raw = data.get("focus")
    if isinstance(focus_raw, list):
        focus = [str(item) for item in focus_raw]
    task_type: str | None = None
    task_type_raw = data.get("task_type")
    if isinstance(task_type_raw, str):
        task_type = task_type_raw
    risk_level: str | None = None
    risk_level_raw = data.get("risk_level")
    if isinstance(risk_level_raw, str):
        risk_level = risk_level_raw
    requires_confirmation: bool | None = None
    requires_confirmation_raw = data.get("requires_confirmation")
    if isinstance(requires_confirmation_raw, bool):
        requires_confirmation = requires_confirmation_raw
    return CapabilityView(
        name=str(data.get("name", "")),
        description=str(data.get("description", "")),
        task_type=task_type,
        constraints=constraints,
        focus=focus,
        risk_level=risk_level,
        requires_confirmation=requires_confirmation,
    )


@pytest.mark.asyncio
async def test_binding_tool_metadata_is_visible_to_registry_and_filtering(tmp_path: Path) -> None:
    skill_dir = tmp_path / "demo"
    skill_dir.mkdir()
    _write_skill(skill_dir / "SKILL.md")

    loader = SkillsLoader(tmp_path)
    loader.scan()
    registry = CapabilityRegistry(loader)
    auto_register_binding_tools(loader, registry)

    caps = registry.list_capabilities()
    assert len(caps) == 1
    assert caps[0]["name"] == "fetch-order"
    assert caps[0]["task_type"] == "trading_decision"
    assert caps[0]["risk_level"] == "high"
    assert caps[0]["requires_confirmation"] is True

    vf = VisibilityFilter()
    vf.register_evaluator(RiskConfirmationConstraint())
    visible = await vf.filter_capabilities(
        [_to_capability_view(caps[0])],
        "agent1",
        RunContext(tenant_id="default"),
    )
    assert visible == []


@pytest.mark.asyncio
async def test_binding_tool_participates_budget_and_rate_limit_constraints(tmp_path: Path) -> None:
    skill_dir = tmp_path / "demo"
    skill_dir.mkdir()
    _write_skill(skill_dir / "SKILL.md")

    loader = SkillsLoader(tmp_path)
    loader.scan()
    registry = CapabilityRegistry(loader)
    auto_register_binding_tools(loader, registry)
    cap = _to_capability_view(registry.list_capabilities()[0])

    budget_vf = VisibilityFilter()
    budget_vf.register_evaluator(
        BudgetConstraint(cast(Any, _Ledger(total_cost=Decimal("100"), call_count=0)), {"budget_limits": {"agent1": "10"}})
    )
    budget_visible = await budget_vf.filter_capabilities([cap], "agent1", RunContext(tenant_id="default", confirmed_capabilities={"fetch-order"}))
    assert budget_visible == []

    rate_vf = VisibilityFilter()
    rate_vf.register_evaluator(RateLimitConstraint(cast(Any, _Ledger(total_cost=Decimal("0"), call_count=1))))
    rate_visible = await rate_vf.filter_capabilities([cap], "agent1", RunContext(tenant_id="default", confirmed_capabilities={"fetch-order"}))
    assert rate_visible == []
