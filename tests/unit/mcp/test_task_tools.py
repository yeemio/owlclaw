"""Unit tests for MCP task tools."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from owlclaw import OwlClaw
from owlclaw.mcp import McpProtocolServer, register_task_mcp_tools


class _FakeTaskClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def run_task_now(self, task_name: str, **kwargs: Any) -> str:
        self.calls.append(("run_task_now", {"task_name": task_name, "kwargs": kwargs}))
        return "run-now-1"

    async def schedule_task(self, task_name: str, delay_seconds: int, **kwargs: Any) -> str:
        self.calls.append(
            ("schedule_task", {"task_name": task_name, "delay_seconds": delay_seconds, "kwargs": kwargs})
        )
        return "run-scheduled-1"

    async def get_task_status(self, task_id: str) -> dict[str, Any]:
        self.calls.append(("get_task_status", {"task_id": task_id}))
        return {"id": task_id, "status": "queued"}

    async def cancel_task(self, task_id: str) -> bool:
        self.calls.append(("cancel_task", {"task_id": task_id}))
        return task_id == "run-scheduled-1"


def _create_app(tmp_path: Path) -> OwlClaw:
    skill_dir = tmp_path / "capabilities" / "ops" / "noop"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: noop
description: no-op
metadata:
  version: "1.0.0"
owlclaw:
  task_type: test
---
# noop
""",
        encoding="utf-8",
    )
    app = OwlClaw("task-mcp")
    app.mount_skills(str(tmp_path / "capabilities"))
    return app


@pytest.mark.asyncio
async def test_task_create_run_and_schedule(tmp_path: Path) -> None:
    app = _create_app(tmp_path)
    assert app.registry is not None
    client = _FakeTaskClient()
    register_task_mcp_tools(registry=app.registry, task_client=client)
    server = McpProtocolServer.from_app(app)

    run_resp = await server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "task_create",
                "arguments": {"workflow_name": "sync_orders", "input_data": {"tenant_id": "t-1"}},
            },
        }
    )
    run_payload = json.loads(run_resp["result"]["content"][0]["text"])
    assert run_payload == {"task_id": "run-now-1", "status": "running"}

    scheduled_resp = await server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "task_create",
                "arguments": {
                    "workflow_name": "sync_orders",
                    "input_data": {"tenant_id": "t-1"},
                    "schedule": {"delay_seconds": 30},
                },
            },
        }
    )
    scheduled_payload = json.loads(scheduled_resp["result"]["content"][0]["text"])
    assert scheduled_payload == {"task_id": "run-scheduled-1", "status": "scheduled"}
    assert client.calls[0][0] == "run_task_now"
    assert client.calls[1][0] == "schedule_task"


@pytest.mark.asyncio
async def test_task_status_and_cancel(tmp_path: Path) -> None:
    app = _create_app(tmp_path)
    assert app.registry is not None
    client = _FakeTaskClient()
    register_task_mcp_tools(registry=app.registry, task_client=client)
    server = McpProtocolServer.from_app(app)

    status_resp = await server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "task_status", "arguments": {"task_id": "run-scheduled-1"}},
        }
    )
    status_payload = json.loads(status_resp["result"]["content"][0]["text"])
    assert status_payload == {"task_id": "run-scheduled-1", "status": "queued"}

    cancel_resp = await server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "task_cancel", "arguments": {"task_id": "run-scheduled-1"}},
        }
    )
    cancel_payload = json.loads(cancel_resp["result"]["content"][0]["text"])
    assert cancel_payload == {"task_id": "run-scheduled-1", "cancelled": True}


@pytest.mark.asyncio
async def test_task_create_rejects_invalid_schedule(tmp_path: Path) -> None:
    app = _create_app(tmp_path)
    assert app.registry is not None
    client = _FakeTaskClient()
    register_task_mcp_tools(registry=app.registry, task_client=client)
    server = McpProtocolServer.from_app(app)

    bad_resp = await server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {"name": "task_create", "arguments": {"workflow_name": "w1", "schedule": {"delay_seconds": 0}}},
        }
    )
    assert bad_resp["error"]["code"] == -32005
