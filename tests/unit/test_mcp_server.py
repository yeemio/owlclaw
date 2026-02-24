"""Unit tests for MCP protocol server."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from owlclaw import OwlClaw
from owlclaw.mcp import McpProtocolServer


def _create_test_app(tmp_path: Path) -> OwlClaw:
    capabilities_dir = tmp_path / "capabilities" / "demo" / "echo-tool"
    capabilities_dir.mkdir(parents=True)
    (capabilities_dir / "SKILL.md").write_text(
        """---
name: echo-tool
description: Echo input for testing
metadata:
  version: "1.0.0"
owlclaw:
  task_type: test
  constraints:
    max_daily_calls: 10
---
# Echo Tool
""",
        encoding="utf-8",
    )

    app = OwlClaw("test-mcp")
    app.mount_skills(str(tmp_path / "capabilities"))

    @app.handler("echo-tool")
    async def echo_tool(message: str) -> dict[str, str]:
        """Echo message input."""
        return {"echo": message}

    return app


@pytest.mark.asyncio
async def test_initialize_and_tools_list(tmp_path: Path) -> None:
    app = _create_test_app(tmp_path)
    server = McpProtocolServer.from_app(app)

    init_response = await server.handle_message({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    assert init_response["result"]["protocolVersion"] == "1.0"

    tools_response = await server.handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    tools = tools_response["result"]["tools"]
    assert len(tools) == 1
    assert tools[0]["name"] == "echo-tool"
    assert tools[0]["inputSchema"]["properties"]["message"]["type"] == "string"


@pytest.mark.asyncio
async def test_tools_call_and_resource_read(tmp_path: Path) -> None:
    app = _create_test_app(tmp_path)
    server = McpProtocolServer.from_app(app)

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

    resources_list = await server.handle_message({"jsonrpc": "2.0", "id": 4, "method": "resources/list"})
    uri = resources_list["result"]["resources"][0]["uri"]
    read_response = await server.handle_message(
        {"jsonrpc": "2.0", "id": 5, "method": "resources/read", "params": {"uri": uri}}
    )
    assert "echo-tool" in read_response["result"]["contents"][0]["text"]


@pytest.mark.asyncio
async def test_error_codes_for_unknown_method_and_missing_tool(tmp_path: Path) -> None:
    app = _create_test_app(tmp_path)
    server = McpProtocolServer.from_app(app)

    unknown_method = await server.handle_message({"jsonrpc": "2.0", "id": 6, "method": "unknown/method"})
    assert unknown_method["error"]["code"] == -32601

    missing_tool = await server.handle_message(
        {"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {"name": "not-exist", "arguments": {}}}
    )
    assert missing_tool["error"]["code"] == -32001


@pytest.mark.asyncio
async def test_stdio_line_parser_returns_parse_error(tmp_path: Path) -> None:
    app = OwlClaw("test-empty")
    app.mount_skills(str(tmp_path))
    server = McpProtocolServer.from_app(app)

    line = await server.process_stdio_line("{invalid-json")
    payload = json.loads(line)
    assert payload["error"]["code"] == -32700
