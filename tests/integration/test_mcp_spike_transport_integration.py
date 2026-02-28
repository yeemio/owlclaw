"""Integration spike tests for MCP HTTP/stdio transport experience."""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter

import pytest
from starlette.testclient import TestClient

from owlclaw import OwlClaw
from owlclaw.mcp import McpProtocolServer, create_mcp_http_app

pytestmark = pytest.mark.integration


def _build_app(tmp_path: Path) -> OwlClaw:
    skill_dir = tmp_path / "capabilities" / "ops" / "sum-tool"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
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
    app = OwlClaw("mcp-spike")
    app.mount_skills(str(tmp_path / "capabilities"))

    @app.handler("sum-tool")
    async def sum_tool(a: int, b: int) -> dict[str, int]:
        return {"total": a + b}

    return app


@pytest.mark.asyncio
async def test_mcp_http_transport_flow_and_latency(tmp_path: Path) -> None:
    app = _build_app(tmp_path)
    server = McpProtocolServer.from_app(app)
    http_app = create_mcp_http_app(server=server, agent_card_url="http://127.0.0.1:8080")

    with TestClient(http_app) as client:
        init = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        assert init.status_code == 200
        assert init.json()["result"]["serverInfo"]["name"] == "owlclaw-mcp-server"

        tool_list = client.post("/mcp", json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        assert tool_list.status_code == 200
        tool_names = {item["name"] for item in tool_list.json()["result"]["tools"]}
        assert "sum-tool" in tool_names

        call = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "sum-tool", "arguments": {"a": 2, "b": 3}},
            },
        )
        assert json.loads(call.json()["result"]["content"][0]["text"]) == {"total": 5}

        card = client.get("/.well-known/agent.json")
        assert card.status_code == 200
        assert card.json()["protocols"]["a2a"]["version"] == "0.1.0"

        samples_ms: list[float] = []
        for i in range(120):
            started = perf_counter()
            response = client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 100 + i,
                    "method": "tools/call",
                    "params": {"name": "sum-tool", "arguments": {"a": i, "b": 1}},
                },
            )
            elapsed_ms = (perf_counter() - started) * 1000
            assert response.status_code == 200
            samples_ms.append(elapsed_ms)

    sorted_samples = sorted(samples_ms)
    p95_ms = sorted_samples[int(len(sorted_samples) * 0.95) - 1]
    assert p95_ms < 500


@pytest.mark.asyncio
async def test_mcp_stdio_transport_latency(tmp_path: Path) -> None:
    app = _build_app(tmp_path)
    server = McpProtocolServer.from_app(app)

    samples_ms: list[float] = []
    for i in range(120):
        request = {
            "jsonrpc": "2.0",
            "id": i,
            "method": "tools/call",
            "params": {"name": "sum-tool", "arguments": {"a": i, "b": 1}},
        }
        started = perf_counter()
        line = await server.process_stdio_line(json.dumps(request))
        elapsed_ms = (perf_counter() - started) * 1000
        payload = json.loads(line)
        assert "result" in payload
        samples_ms.append(elapsed_ms)

    sorted_samples = sorted(samples_ms)
    p95_ms = sorted_samples[int(len(sorted_samples) * 0.95) - 1]
    assert p95_ms < 500


@pytest.mark.asyncio
async def test_mcp_http_transport_returns_parse_error_for_invalid_json(tmp_path: Path) -> None:
    app = _build_app(tmp_path)
    server = McpProtocolServer.from_app(app)
    http_app = create_mcp_http_app(server=server, agent_card_url="http://127.0.0.1:8080")

    with TestClient(http_app) as client:
        response = client.post(
            "/mcp",
            content="{invalid-json",
            headers={"content-type": "application/json"},
        )
        assert response.status_code == 400
        payload = response.json()
        assert payload["error"]["code"] == -32700
