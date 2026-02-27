"""Integration tests for mionyee governance overlay glue."""

from __future__ import annotations

import importlib.util
from decimal import Decimal
from pathlib import Path

import pytest

from owlclaw.governance.ledger import LedgerQueryFilters
from owlclaw.governance.proxy import GovernanceProxy, GovernanceRejectedError


def _load_mionyee_client_class() -> type:
    client_path = Path("examples/mionyee-trading/ai/client.py")
    spec = importlib.util.spec_from_file_location("mionyee_example_client", client_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.MionyeeAIClient


@pytest.mark.asyncio
async def test_mionyee_client_uses_governance_proxy_and_records_audit() -> None:
    async def _ok_call(**_: object) -> dict[str, object]:
        return {"id": "resp-1", "usage": {"total_tokens": 1200}}

    MionyeeAIClient = _load_mionyee_client_class()
    proxy = GovernanceProxy(llm_call=_ok_call, tenant_id="mionyee", agent_id="mionyee.proxy")
    client = MionyeeAIClient(proxy=proxy, default_model="gpt-4o-mini")

    response = await client.acompletion(
        service="trading_decision",
        messages=[{"role": "user", "content": "check signals"}],
    )
    assert response["id"] == "resp-1"

    rows = await proxy.ledger.query_records(
        tenant_id="mionyee",
        filters=LedgerQueryFilters(capability_name="mionyee.ai.trading_decision", status="success"),
    )
    assert len(rows) == 1
    assert rows[0].agent_id == "mionyee.proxy"


@pytest.mark.asyncio
async def test_mionyee_client_budget_rejection_is_audited() -> None:
    async def _ok_call(**_: object) -> dict[str, object]:
        return {"usage": {"total_tokens": 2000}}

    MionyeeAIClient = _load_mionyee_client_class()
    proxy = GovernanceProxy(llm_call=_ok_call, daily_limit_usd=Decimal("0.001"), tenant_id="mionyee")
    client = MionyeeAIClient(proxy=proxy)

    await client.acompletion(service="trading_decision", messages=[{"role": "user", "content": "first"}])
    with pytest.raises(GovernanceRejectedError, match="budget_exhausted_daily"):
        await client.acompletion(service="trading_decision", messages=[{"role": "user", "content": "second"}])

    blocked_rows = await proxy.ledger.query_records(
        tenant_id="mionyee",
        filters=LedgerQueryFilters(capability_name="mionyee.ai.trading_decision", status="blocked"),
    )
    assert len(blocked_rows) == 1


def test_mionyee_client_from_config_loads_example_yaml() -> None:
    MionyeeAIClient = _load_mionyee_client_class()
    client = MionyeeAIClient.from_config("examples/mionyee-trading/owlclaw.yaml")
    assert client.proxy.daily_limit_usd == Decimal("10.0")
    assert client.proxy.monthly_limit_usd == Decimal("200.0")
    assert client.proxy.per_service_qps["mionyee.ai.trading_decision"] == 5
    assert client.proxy.failure_threshold == 5
