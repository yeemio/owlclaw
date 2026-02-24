"""Unit tests for MCP protocol server."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from owlclaw import OwlClaw
from owlclaw.mcp import McpProtocolServer
from owlclaw.triggers.signal import (
    AgentStateManager,
    SignalResult,
    SignalRouter,
    default_handlers,
    register_signal_mcp_tools,
)


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


@pytest.mark.asyncio
async def test_request_validation_and_param_errors(tmp_path: Path) -> None:
    app = _create_test_app(tmp_path)
    server = McpProtocolServer.from_app(app)

    invalid_version = await server.handle_message({"jsonrpc": "1.0", "id": 1, "method": "tools/list"})
    assert invalid_version["error"]["code"] == -32600

    missing_method = await server.handle_message({"jsonrpc": "2.0", "id": 2})
    assert missing_method["error"]["code"] == -32600

    invalid_params = await server.handle_message(
        {"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": "not-dict"}
    )
    assert invalid_params["error"]["code"] == -32602

    missing_uri = await server.handle_message({"jsonrpc": "2.0", "id": 4, "method": "resources/read", "params": {}})
    assert missing_uri["error"]["code"] == -32602


@pytest.mark.asyncio
async def test_tool_and_resource_specific_errors(tmp_path: Path) -> None:
    app = _create_test_app(tmp_path)
    server = McpProtocolServer.from_app(app)

    invalid_tool_name = await server.handle_message(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "", "arguments": {}}}
    )
    assert invalid_tool_name["error"]["code"] == -32602

    invalid_arguments = await server.handle_message(
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "echo-tool", "arguments": []}}
    )
    assert invalid_arguments["error"]["code"] == -32602

    missing_resource = await server.handle_message(
        {"jsonrpc": "2.0", "id": 3, "method": "resources/read", "params": {"uri": "skill://x/y"}}
    )
    assert missing_resource["error"]["code"] == -32002


@pytest.mark.asyncio
async def test_from_app_requires_mounted_skills() -> None:
    app = OwlClaw("no-skills")
    with pytest.raises(ValueError):
        McpProtocolServer.from_app(app)


@pytest.mark.asyncio
async def test_stdio_line_parser_rejects_non_object_json(tmp_path: Path) -> None:
    app = _create_test_app(tmp_path)
    server = McpProtocolServer.from_app(app)
    line = await server.process_stdio_line('["not","object"]')
    payload = json.loads(line)
    assert payload["error"]["code"] == -32600


def test_annotation_to_schema_branches(tmp_path: Path) -> None:
    app = _create_test_app(tmp_path)
    server = McpProtocolServer.from_app(app)

    assert server._annotation_to_schema(float)["type"] == "number"
    assert server._annotation_to_schema(bool)["type"] == "boolean"
    assert server._annotation_to_schema(list[int])["type"] == "array"
    assert server._annotation_to_schema(dict[str, int])["type"] == "object"
    assert server._annotation_to_schema(tuple[int, int])["type"] == "array"
    assert server._annotation_to_schema(Any)["type"] == "object"
    union_schema = server._annotation_to_schema(str | int)
    assert "oneOf" in union_schema
    optional_schema = server._annotation_to_schema(str | None)
    assert optional_schema.get("nullable") is True


def test_build_input_schema_ignores_session_and_varargs(tmp_path: Path) -> None:
    app = _create_test_app(tmp_path)
    server = McpProtocolServer.from_app(app)

    def handler(session: dict[str, Any], name: str, *args: Any, **kwargs: Any) -> dict[str, str]:
        """Short doc."""
        return {"ok": name}

    schema = server._build_input_schema(handler)
    assert "session" not in schema["properties"]
    assert "name" in schema["properties"]


@pytest.mark.asyncio
async def test_mcp_tools_list_includes_signal_tools_when_router_present(tmp_path: Path) -> None:
    app = _create_test_app(tmp_path)

    class _Router:
        async def dispatch(self, signal: Any) -> SignalResult:  # noqa: ARG002
            return SignalResult(status="paused")

    server = McpProtocolServer.from_app(app)
    server.signal_router = _Router()  # type: ignore[assignment]

    tools_response = await server.handle_message({"jsonrpc": "2.0", "id": 10, "method": "tools/list"})
    tool_names = {item["name"] for item in tools_response["result"]["tools"]}
    assert "owlclaw_pause" in tool_names
    assert "owlclaw_resume" in tool_names
    assert "owlclaw_trigger" in tool_names
    assert "owlclaw_instruct" in tool_names


@pytest.mark.asyncio
async def test_mcp_signal_tool_dispatches_to_signal_router(tmp_path: Path) -> None:
    app = _create_test_app(tmp_path)
    captured: dict[str, Any] = {}

    class _Router:
        async def dispatch(self, signal: Any) -> SignalResult:
            captured["signal"] = signal
            return SignalResult(status="triggered", run_id="run-1")

    server = McpProtocolServer.from_app(app)
    server.signal_router = _Router()  # type: ignore[assignment]

    response = await server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 11,
            "method": "tools/call",
            "params": {
                "name": "owlclaw_trigger",
                "arguments": {"agent_id": "a1", "tenant_id": "t1", "operator": "op", "focus": "f", "message": "m"},
            },
        }
    )

    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["status"] == "triggered"
    assert payload["run_id"] == "run-1"
    assert captured["signal"].agent_id == "a1"
    assert captured["signal"].tenant_id == "t1"


@pytest.mark.asyncio
async def test_register_signal_mcp_tools_via_registry(tmp_path: Path) -> None:
    app = _create_test_app(tmp_path)
    assert app.registry is not None

    class _Runtime:
        async def trigger_event(
            self,
            event_name: str,
            payload: dict[str, Any],
            focus: str | None = None,
            tenant_id: str = "default",
        ) -> dict[str, Any]:
            _ = (event_name, payload, focus, tenant_id)
            return {"run_id": "run-mcp-registry"}

    state = AgentStateManager(max_pending_instructions=4)
    router = SignalRouter(handlers=default_handlers(state=state, runtime=_Runtime()))
    register_signal_mcp_tools(registry=app.registry, router=router)

    server = McpProtocolServer.from_app(app)
    tools_response = await server.handle_message({"jsonrpc": "2.0", "id": 21, "method": "tools/list"})
    tool_names = {item["name"] for item in tools_response["result"]["tools"]}
    assert {"owlclaw_pause", "owlclaw_resume", "owlclaw_trigger", "owlclaw_instruct"} <= tool_names

    trigger_response = await server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 22,
            "method": "tools/call",
            "params": {"name": "owlclaw_trigger", "arguments": {"agent_id": "agent-a", "message": "run"}},
        }
    )
    payload = json.loads(trigger_response["result"]["content"][0]["text"])
    assert payload["status"] == "triggered"
    assert payload["run_id"] == "run-mcp-registry"
