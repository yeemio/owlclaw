"""Unit tests for governance MCP tools."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from owlclaw import OwlClaw
from owlclaw.governance.ledger_inmemory import InMemoryLedger
from owlclaw.mcp import McpProtocolServer, register_governance_mcp_tools


def _create_app(tmp_path: Path) -> OwlClaw:
    capabilities_dir = tmp_path / "capabilities" / "ops" / "noop"
    capabilities_dir.mkdir(parents=True)
    (capabilities_dir / "SKILL.md").write_text(
        """---
name: noop
description: No-op skill
metadata:
  version: "1.0.0"
owlclaw:
  task_type: test
---
# No-op
""",
        encoding="utf-8",
    )
    app = OwlClaw("governance-mcp")
    app.mount_skills(str(tmp_path / "capabilities"))
    return app


async def _record(
    ledger: InMemoryLedger,
    *,
    tenant_id: str,
    agent_id: str,
    run_id: str,
    estimated_cost: Decimal,
    status: str = "success",
) -> None:
    await ledger.record_execution(
        tenant_id=tenant_id,
        agent_id=agent_id,
        run_id=run_id,
        capability_name="noop",
        task_type="test",
        input_params={"k": "v"},
        output_result={"ok": True},
        decision_reasoning="test",
        execution_time_ms=12,
        llm_model="gpt-5",
        llm_tokens_input=21,
        llm_tokens_output=9,
        estimated_cost=estimated_cost,
        status=status,
    )


@pytest.mark.asyncio
async def test_governance_budget_and_audit_tools_are_callable(tmp_path: Path) -> None:
    app = _create_app(tmp_path)
    assert app.registry is not None
    ledger = InMemoryLedger()
    await _record(ledger, tenant_id="t-1", agent_id="agent-a", run_id="run-1", estimated_cost=Decimal("1.25"))
    await _record(ledger, tenant_id="t-1", agent_id="agent-a", run_id="run-2", estimated_cost=Decimal("0.75"))

    register_governance_mcp_tools(registry=app.registry, ledger=ledger)
    server = McpProtocolServer.from_app(app)

    tools_response = await server.handle_message({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    tool_names = {item["name"] for item in tools_response["result"]["tools"]}
    assert "governance_budget_status" in tool_names
    assert "governance_audit_query" in tool_names
    assert "governance_rate_limit_status" in tool_names

    budget_response = await server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "governance_budget_status",
                "arguments": {"tenant_id": "t-1", "agent_id": "agent-a", "daily_limit": "10", "monthly_limit": "100"},
            },
        }
    )
    budget_payload = json.loads(budget_response["result"]["content"][0]["text"])
    assert budget_payload["daily_used"] == "2.00"
    assert budget_payload["daily_limit"] == "10"
    assert budget_payload["monthly_used"] == "2.00"
    assert budget_payload["monthly_limit"] == "100"

    audit_response = await server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "governance_audit_query",
                "arguments": {"tenant_id": "t-1", "caller": "agent-a", "limit": 1},
            },
        }
    )
    audit_payload = json.loads(audit_response["result"]["content"][0]["text"])
    assert audit_payload["count"] == 1
    assert len(audit_payload["records"]) == 1
    assert audit_payload["records"][0]["caller"] == "agent-a"
    assert audit_payload["records"][0]["model"] == "gpt-5"


@pytest.mark.asyncio
async def test_governance_rate_limit_status_uses_provider(tmp_path: Path) -> None:
    app = _create_app(tmp_path)
    assert app.registry is not None
    ledger = InMemoryLedger()

    async def _provider(service: str) -> dict[str, Any]:
        assert service == "erp"
        return {"current_qps": 2.5, "limit_qps": 8.0, "rejected_count": 3}

    register_governance_mcp_tools(registry=app.registry, ledger=ledger, rate_limit_provider=_provider)
    server = McpProtocolServer.from_app(app)

    response = await server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "governance_rate_limit_status", "arguments": {"service": "erp"}},
        }
    )
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload == {"service": "erp", "current_qps": 2.5, "limit_qps": 8.0, "rejected_count": 3}


@pytest.mark.asyncio
async def test_governance_audit_query_rejects_bad_iso_time(tmp_path: Path) -> None:
    app = _create_app(tmp_path)
    assert app.registry is not None
    ledger = InMemoryLedger()

    register_governance_mcp_tools(registry=app.registry, ledger=ledger)
    server = McpProtocolServer.from_app(app)

    response = await server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "governance_audit_query",
                "arguments": {"tenant_id": "t-1", "start_time": "not-time"},
            },
        }
    )
    assert response["error"]["code"] == -32005
