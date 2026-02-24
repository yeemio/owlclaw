"""Integration tests for MCP server minimal end-to-end flow."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from owlclaw import OwlClaw
from owlclaw.mcp import McpProtocolServer


def _build_app(tmp_path: Path) -> OwlClaw:
    root = tmp_path / "capabilities" / "ops" / "sum-tool"
    root.mkdir(parents=True)
    (root / "SKILL.md").write_text(
        """---
name: sum-tool
description: Sum two integers
metadata:
  version: "1.0.0"
owlclaw:
  task_type: calculation
---
# Sum Tool
""",
        encoding="utf-8",
    )

    app = OwlClaw("mcp-integration")
    app.mount_skills(str(tmp_path / "capabilities"))

    @app.handler("sum-tool")
    async def sum_tool(a: int, b: int) -> dict[str, int]:
        """Add two integers."""
        return {"total": a + b}

    return app


@pytest.mark.asyncio
async def test_mcp_end_to_end_call_flow(tmp_path: Path) -> None:
    app = _build_app(tmp_path)
    server = McpProtocolServer.from_app(app)

    initialize = await server.process_stdio_line(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"}))
    init_payload = json.loads(initialize)
    assert init_payload["result"]["serverInfo"]["name"] == "owlclaw-mcp-server"

    tools = await server.process_stdio_line(json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}))
    tools_payload = json.loads(tools)
    assert tools_payload["result"]["tools"][0]["name"] == "sum-tool"

    call = await server.process_stdio_line(
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "sum-tool", "arguments": {"a": 2, "b": 3}},
            }
        )
    )
    call_payload = json.loads(call)
    assert json.loads(call_payload["result"]["content"][0]["text"]) == {"total": 5}

    resources = await server.process_stdio_line(json.dumps({"jsonrpc": "2.0", "id": 4, "method": "resources/list"}))
    resources_payload = json.loads(resources)
    uri = resources_payload["result"]["resources"][0]["uri"]
    read = await server.process_stdio_line(
        json.dumps({"jsonrpc": "2.0", "id": 5, "method": "resources/read", "params": {"uri": uri}})
    )
    read_payload = json.loads(read)
    assert "Sum two integers" in read_payload["result"]["contents"][0]["text"]

