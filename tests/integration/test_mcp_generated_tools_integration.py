"""Integration tests for migrate-generated MCP tool definitions."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from owlclaw import OwlClaw
from owlclaw.cli.migrate.scan_cli import run_migrate_scan_command
from owlclaw.mcp import McpProtocolServer, register_generated_mcp_tools

pytestmark = pytest.mark.integration


def _build_app(tmp_path: Path) -> OwlClaw:
    skill_root = tmp_path / "capabilities" / "ops" / "bootstrap-skill"
    skill_root.mkdir(parents=True)
    (skill_root / "SKILL.md").write_text(
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
    app = OwlClaw("mcp-generated")
    app.mount_skills(str(tmp_path / "capabilities"))
    return app


@pytest.mark.asyncio
async def test_generated_mcp_tool_can_be_listed_and_called(tmp_path: Path) -> None:
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
    registered = register_generated_mcp_tools(registry=app.registry, tools_dir=tmp_path / "mcp_tools")
    assert "create-order" in registered

    server = McpProtocolServer.from_app(app)
    list_resp = await server.handle_message({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    tool_names = {item["name"] for item in list_resp["result"]["tools"]}
    assert "create-order" in tool_names

    call_resp = await server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "create-order", "arguments": {"order_id": "ord-1"}},
        }
    )
    payload = json.loads(call_resp["result"]["content"][0]["text"])
    assert payload["status"] == "generated"
    assert payload["binding"]["type"] == "http"
    assert payload["binding"]["method"] == "POST"
    assert payload["arguments"] == {"order_id": "ord-1"}
