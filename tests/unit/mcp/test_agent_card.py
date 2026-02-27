"""Unit tests for A2A agent card endpoint."""

from __future__ import annotations

from pathlib import Path

from starlette.testclient import TestClient

from owlclaw import OwlClaw
from owlclaw.mcp import McpProtocolServer, create_agent_card_app
from owlclaw.mcp.governance_tools import register_governance_mcp_tools
from owlclaw.mcp.task_tools import register_task_mcp_tools


class _NoopLedger:
    async def get_cost_summary(self, tenant_id: str, agent_id: str, start_date, end_date):  # type: ignore[no-untyped-def]  # noqa: ANN001
        class _Summary:
            total_cost = "0"

        _ = (tenant_id, agent_id, start_date, end_date)
        return _Summary()

    async def query_records(self, tenant_id: str, filters):  # type: ignore[no-untyped-def]  # noqa: ANN001
        _ = (tenant_id, filters)
        return []


class _NoopTaskClient:
    async def run_task_now(self, task_name: str, **kwargs):  # type: ignore[no-untyped-def]  # noqa: ANN001
        _ = (task_name, kwargs)
        return "run-1"

    async def schedule_task(self, task_name: str, delay_seconds: int, **kwargs):  # type: ignore[no-untyped-def]  # noqa: ANN001
        _ = (task_name, delay_seconds, kwargs)
        return "sched-1"

    async def get_task_status(self, task_id: str):  # type: ignore[no-untyped-def]  # noqa: ANN001
        return {"id": task_id, "status": "queued"}

    async def cancel_task(self, task_id: str) -> bool:
        _ = task_id
        return True


def _build_app(tmp_path: Path) -> OwlClaw:
    skill_dir = tmp_path / "capabilities" / "ops" / "echo-tool"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: echo-tool
description: Echo tool
metadata:
  version: "1.0.0"
owlclaw:
  task_type: test
---
# Echo Tool
""",
        encoding="utf-8",
    )
    app = OwlClaw("agent-card")
    app.mount_skills(str(tmp_path / "capabilities"))
    return app


def test_build_agent_card_contains_a2a_fields(tmp_path: Path) -> None:
    app = _build_app(tmp_path)
    assert app.registry is not None
    register_governance_mcp_tools(registry=app.registry, ledger=_NoopLedger())
    register_task_mcp_tools(registry=app.registry, task_client=_NoopTaskClient())

    server = McpProtocolServer.from_app(app)
    payload = server.build_agent_card(url="https://agent.example.com")

    assert payload["name"] == "OwlClaw"
    assert payload["url"] == "https://agent.example.com"
    assert payload["protocols"]["a2a"]["version"] == "0.1.0"
    assert payload["protocols"]["mcp"]["transport"] == ["http", "stdio"]
    assert "governance_budget_status" in payload["capabilities"]["governance"]
    assert "task_create" in payload["capabilities"]["tasks"]


def test_agent_card_http_endpoint_returns_json(tmp_path: Path) -> None:
    app = _build_app(tmp_path)
    assert app.registry is not None
    register_governance_mcp_tools(registry=app.registry, ledger=_NoopLedger())
    register_task_mcp_tools(registry=app.registry, task_client=_NoopTaskClient())

    server = McpProtocolServer.from_app(app)
    http_app = create_agent_card_app(server=server, url="https://agent.example.com")

    with TestClient(http_app) as client:
        response = client.get("/.well-known/agent.json")

    assert response.status_code == 200
    body = response.json()
    assert body["url"] == "https://agent.example.com"
    assert body["authentication"]["schemes"] == ["bearer"]
