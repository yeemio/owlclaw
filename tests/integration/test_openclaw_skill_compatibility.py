"""Compatibility tests for owlclaw-for-openclaw skill package."""

from __future__ import annotations

import asyncio
import json
import re
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import pytest
import yaml  # type: ignore[import-untyped]

from owlclaw import OwlClaw
from owlclaw.governance.ledger_inmemory import InMemoryLedger
from owlclaw.mcp import McpProtocolServer, create_mcp_http_app, register_governance_mcp_tools, register_task_mcp_tools

pytestmark = pytest.mark.integration

_FRONTMATTER_PATTERN = re.compile(r"^---\r?\n(.*?)\r?\n---", re.DOTALL)


class _DurableTaskClient:
    def __init__(self) -> None:
        self._states: dict[str, dict[str, Any]] = {}
        self._seq = 0

    async def run_task_now(self, task_name: str, **kwargs: Any) -> str:
        self._seq += 1
        task_id = f"run-{self._seq}"
        self._states[task_id] = {"id": task_id, "status": "running", "task_name": task_name, "input": kwargs}
        asyncio.get_running_loop().create_task(self._complete_after_delay(task_id))
        return task_id

    async def schedule_task(self, task_name: str, delay_seconds: int, **kwargs: Any) -> str:
        self._seq += 1
        task_id = f"sched-{self._seq}"
        self._states[task_id] = {"id": task_id, "status": "scheduled", "task_name": task_name, "input": kwargs}
        asyncio.get_running_loop().create_task(self._complete_after_delay(task_id, delay=max(float(delay_seconds), 0.05)))
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
        if state is None or state.get("status") == "cancelled":
            return
        state["status"] = "completed"
        state["result"] = {"ok": True}


def _load_package_frontmatter() -> dict[str, Any]:
    skill_path = Path(__file__).resolve().parents[2] / "skills" / "owlclaw-for-openclaw" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")
    match = _FRONTMATTER_PATTERN.match(content)
    assert match is not None
    payload = yaml.safe_load(match.group(1))
    assert isinstance(payload, dict)
    return payload


def _load_openclaw_compatible_fields(frontmatter: dict[str, Any]) -> dict[str, Any]:
    allowed = {"name", "description", "version", "metadata", "tools", "tags", "industry"}
    return {key: value for key, value in frontmatter.items() if key in allowed}


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
    app = OwlClaw("openclaw-compat")
    app.mount_skills(str(tmp_path / "capabilities"))
    return app


def test_openclaw_latest_stable_skill_parse_compatibility() -> None:
    frontmatter = _load_package_frontmatter()
    assert frontmatter["name"] == "owlclaw-for-openclaw"
    assert "tools" in frontmatter and isinstance(frontmatter["tools"], dict)
    assert "governance_budget_status" in frontmatter["tools"]
    assert "task_create" in frontmatter["tools"]


def test_owlclaw_extension_field_does_not_block_openclaw_parse() -> None:
    frontmatter = _load_package_frontmatter()
    openclaw_view = _load_openclaw_compatible_fields(frontmatter)
    assert "owlclaw" in frontmatter
    assert "owlclaw" not in openclaw_view
    assert openclaw_view["name"] == frontmatter["name"]
    assert openclaw_view["description"] == frontmatter["description"]


@pytest.mark.asyncio
async def test_openclaw_agent_discovers_and_calls_owlclaw_mcp_tools(tmp_path: Path) -> None:
    app = _build_app(tmp_path)
    assert app.registry is not None

    ledger = InMemoryLedger()
    await ledger.record_execution(
        tenant_id="t-1",
        agent_id="openclaw-agent",
        run_id="seed-compat",
        capability_name="bootstrap-skill",
        task_type="ops",
        input_params={"source": "seed"},
        output_result={"ok": True},
        decision_reasoning="seed",
        execution_time_ms=5,
        llm_model="gpt-5",
        llm_tokens_input=10,
        llm_tokens_output=5,
        estimated_cost=Decimal("0.01"),
        status="success",
    )

    register_governance_mcp_tools(registry=app.registry, ledger=ledger)
    register_task_mcp_tools(registry=app.registry, task_client=_DurableTaskClient())

    server = McpProtocolServer.from_app(app)
    http_app = create_mcp_http_app(server=server, agent_card_url="http://127.0.0.1:8080")
    transport = httpx.ASGITransport(app=http_app)

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        init = await client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        assert init.status_code == 200

        tools = await client.post("/mcp", json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        assert tools.status_code == 200
        tool_names = {item["name"] for item in tools.json()["result"]["tools"]}
        assert "governance_budget_status" in tool_names
        assert "task_create" in tool_names

        budget_call = await client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "governance_budget_status",
                    "arguments": {"tenant_id": "t-1", "agent_id": "openclaw-agent"},
                },
            },
        )
        assert budget_call.status_code == 200

        task_call = await client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {"name": "task_create", "arguments": {"workflow_name": "nightly_sync"}},
            },
        )
        assert task_call.status_code == 200
        payload = json.loads(task_call.json()["result"]["content"][0]["text"])
        assert payload["task_id"]
        await asyncio.sleep(0.06)
