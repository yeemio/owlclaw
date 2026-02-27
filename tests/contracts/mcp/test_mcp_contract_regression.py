"""MCP contract regression baseline tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from owlclaw import OwlClaw
from owlclaw.mcp import McpProtocolServer


def _create_test_app(tmp_path: Path) -> OwlClaw:
    capabilities_dir = tmp_path / "capabilities" / "contract" / "echo-tool"
    capabilities_dir.mkdir(parents=True)
    (capabilities_dir / "SKILL.md").write_text(
        """---
name: echo-tool
description: Echo input for contract testing
metadata:
  version: "1.0.0"
owlclaw:
  task_type: test
---
# Echo Tool
""",
        encoding="utf-8",
    )

    app = OwlClaw("contract-mcp")
    app.mount_skills(str(tmp_path / "capabilities"))

    @app.handler("echo-tool")
    async def echo_tool(message: str) -> dict[str, str]:
        """Echo message for contract checks."""
        return {"echo": message}

    return app


@pytest.mark.asyncio
async def test_mcp_initialize_contract_shape(tmp_path: Path) -> None:
    server = McpProtocolServer.from_app(_create_test_app(tmp_path))
    response = await server.handle_message({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    result = response["result"]
    assert result["protocolVersion"] == "1.0"
    assert "serverInfo" in result
    assert "capabilities" in result


@pytest.mark.asyncio
async def test_mcp_tools_list_and_call_contract_shape(tmp_path: Path) -> None:
    server = McpProtocolServer.from_app(_create_test_app(tmp_path))
    tools_response = await server.handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    tools = tools_response["result"]["tools"]
    assert len(tools) == 1
    assert tools[0]["name"] == "echo-tool"
    assert "inputSchema" in tools[0]

    call_response = await server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "echo-tool", "arguments": {"message": "hello"}},
        }
    )
    payload = call_response["result"]["content"][0]["text"]
    assert json.loads(payload) == {"echo": "hello"}


@pytest.mark.asyncio
async def test_mcp_resources_list_and_read_contract_shape(tmp_path: Path) -> None:
    server = McpProtocolServer.from_app(_create_test_app(tmp_path))
    resources = await server.handle_message({"jsonrpc": "2.0", "id": 4, "method": "resources/list"})
    listed = resources["result"]["resources"]
    assert listed
    uri = listed[0]["uri"]

    read_result = await server.handle_message(
        {"jsonrpc": "2.0", "id": 5, "method": "resources/read", "params": {"uri": uri}}
    )
    text = read_result["result"]["contents"][0]["text"]
    assert "echo-tool" in text


@pytest.mark.asyncio
async def test_mcp_error_semantics_regression(tmp_path: Path) -> None:
    server = McpProtocolServer.from_app(_create_test_app(tmp_path))
    missing_tool = await server.handle_message(
        {"jsonrpc": "2.0", "id": 6, "method": "tools/call", "params": {"name": "not-exist", "arguments": {}}}
    )
    error = missing_tool["error"]
    assert error["code"] == -32001
    assert "tool not found" in error["message"]
