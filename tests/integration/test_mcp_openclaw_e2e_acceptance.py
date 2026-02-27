"""End-to-end acceptance tests for OpenClaw -> OwlClaw MCP flow."""

from __future__ import annotations

import asyncio
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import pytest

from owlclaw import OwlClaw
from owlclaw.cli.migrate.scan_cli import run_migrate_scan_command
from owlclaw.governance.ledger_inmemory import InMemoryLedger
from owlclaw.mcp import (
    McpProtocolServer,
    create_mcp_http_app,
    register_generated_mcp_tools,
    register_governance_mcp_tools,
    register_task_mcp_tools,
)

pytestmark = pytest.mark.integration


class _DurableTaskClient:
    """In-memory durable task client used for MCP acceptance tests."""

    def __init__(self) -> None:
        self._states: dict[str, dict[str, Any]] = {}
        self._seq = 0

    async def run_task_now(self, task_name: str, **kwargs: Any) -> str:
        self._seq += 1
        task_id = f"run-{self._seq}"
        self._states[task_id] = {"id": task_id, "status": "running", "task_name": task_name, "input": kwargs}
        loop = asyncio.get_running_loop()
        loop.create_task(self._complete_after_delay(task_id))
        return task_id

    async def schedule_task(self, task_name: str, delay_seconds: int, **kwargs: Any) -> str:
        self._seq += 1
        task_id = f"sched-{self._seq}"
        self._states[task_id] = {"id": task_id, "status": "scheduled", "task_name": task_name, "input": kwargs}
        loop = asyncio.get_running_loop()
        loop.create_task(self._complete_after_delay(task_id, delay=max(float(delay_seconds), 0.05)))
        return task_id

    async def get_task_status(self, task_id: str) -> dict[str, Any]:
        state = self._states.get(task_id)
        if state is None:
            return {"id": task_id, "status": "not_found"}
        return dict(state)

    async def cancel_task(self, task_id: str) -> bool:
        state = self._states.get(task_id)
        if state is None:
            return False
        state["status"] = "cancelled"
        return True

    async def _complete_after_delay(self, task_id: str, delay: float = 0.05) -> None:
        await asyncio.sleep(delay)
        state = self._states.get(task_id)
        if state is None:
            return
        if state.get("status") in {"cancelled", "not_found"}:
            return
        state["status"] = "completed"
        state["result"] = {"ok": True}


def _build_app(tmp_path: Path) -> OwlClaw:
    skill_dir = tmp_path / "capabilities" / "ops" / "bootstrap-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: bootstrap-skill
description: bootstrap holder skill
metadata:
  version: "1.0.0"
owlclaw:
  task_type: ops
---
# bootstrap
""",
        encoding="utf-8",
    )
    app = OwlClaw("openclaw-e2e")
    app.mount_skills(str(tmp_path / "capabilities"))
    return app


@pytest.mark.asyncio
async def test_openclaw_end_to_end_acceptance(tmp_path: Path) -> None:
    openapi = tmp_path / "openapi.yaml"
    openapi.write_text(
        (
            "openapi: 3.0.3\n"
            "servers:\n"
            "  - url: https://api.example.com\n"
            "paths:\n"
            "  /orders:\n"
            "    post:\n"
            "      operationId: create-order\n"
            "      description: create order\n"
            "      requestBody:\n"
            "        content:\n"
            "          application/json:\n"
            "            schema:\n"
            "              type: object\n"
            "              properties:\n"
            "                order_id: {type: string}\n"
            "              required: [order_id]\n"
            "      responses:\n"
            "        '201': {description: created}\n"
        ),
        encoding="utf-8",
    )
    run_migrate_scan_command(openapi=str(openapi), output_mode="mcp", output=str(tmp_path))

    app = _build_app(tmp_path)
    assert app.registry is not None

    ledger = InMemoryLedger()
    await ledger.record_execution(
        tenant_id="t-1",
        agent_id="openclaw-agent",
        run_id="seed-1",
        capability_name="bootstrap-skill",
        task_type="ops",
        input_params={"source": "seed"},
        output_result={"ok": True},
        decision_reasoning="seed",
        execution_time_ms=5,
        llm_model="gpt-5",
        llm_tokens_input=10,
        llm_tokens_output=5,
        estimated_cost=Decimal("0.12"),
        status="success",
    )

    register_governance_mcp_tools(registry=app.registry, ledger=ledger)
    register_task_mcp_tools(registry=app.registry, task_client=_DurableTaskClient())
    register_generated_mcp_tools(registry=app.registry, tools_dir=tmp_path / "mcp_tools")

    server = McpProtocolServer.from_app(app)
    http_app = create_mcp_http_app(server=server, agent_card_url="http://127.0.0.1:8080")
    transport = httpx.ASGITransport(app=http_app)

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        init = await client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        assert init.status_code == 200
        tools = await client.post("/mcp", json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        assert tools.status_code == 200
        call = await client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "governance_budget_status", "arguments": {"tenant_id": "t-1", "agent_id": "openclaw-agent"}},
            },
        )
        assert call.status_code == 200

        tool_names = {item["name"] for item in tools.json()["result"]["tools"]}
        assert {"governance_budget_status", "governance_audit_query", "governance_rate_limit_status"} <= tool_names
        assert "create-order" in tool_names

        audit = await client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {"name": "governance_audit_query", "arguments": {"tenant_id": "t-1", "caller": "openclaw-agent"}},
            },
        )
        assert audit.status_code == 200

        rate = await client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {"name": "governance_rate_limit_status", "arguments": {"service": "global"}},
            },
        )
        assert rate.status_code == 200

        business = await client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 6,
                "method": "tools/call",
                "params": {"name": "create-order", "arguments": {"order_id": "ord-1"}},
            },
        )
        assert business.status_code == 200

        task_create = await client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 7,
                "method": "tools/call",
                "params": {
                    "name": "task_create",
                    "arguments": {"workflow_name": "nightly_sync", "input_data": {"tenant_id": "t-1"}},
                },
            },
        )
        assert task_create.status_code == 200
        task_payload = json.loads(task_create.json()["result"]["content"][0]["text"])
        task_id = task_payload["task_id"]

    await asyncio.sleep(0.08)

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client2:
        task_status = await client2.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 8,
                "method": "tools/call",
                "params": {"name": "task_status", "arguments": {"task_id": task_id}},
            },
        )
        assert task_status.status_code == 200
        status_payload = json.loads(task_status.json()["result"]["content"][0]["text"])
        assert status_payload["status"] == "completed"
