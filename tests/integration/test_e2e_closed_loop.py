"""Closed-loop release gate test (Decision 14 / D14-2)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from owlclaw.agent.runtime.runtime import AgentRuntime
from owlclaw.capabilities.registry import CapabilityRegistry
from owlclaw.capabilities.skills import SkillsLoader
from owlclaw.governance import InMemoryLedger
from owlclaw.triggers.api import APITriggerConfig, APITriggerServer
from owlclaw.triggers.api.auth import APIKeyAuthProvider

pytestmark = pytest.mark.integration


def _write_closed_loop_app_dir(tmp_path: Path) -> Path:
    app_dir = tmp_path / "closed_loop_app"
    skills_root = app_dir / "skills" / "order-store"
    skills_root.mkdir(parents=True, exist_ok=True)
    (app_dir / "SOUL.md").write_text("You are a business agent.", encoding="utf-8")
    (app_dir / "IDENTITY.md").write_text("- order-store", encoding="utf-8")
    (skills_root / "SKILL.md").write_text(
        """---
name: order-store
description: Persist incoming order payload to downstream business system.
owlclaw:
  task_type: operations
---
# Usage
Store validated order payload.
""",
        encoding="utf-8",
    )
    return app_dir


def _make_tool_call(name: str, arguments: dict[str, Any]) -> MagicMock:
    tool_call = MagicMock()
    tool_call.id = "tc_closed_loop_1"
    tool_call.function.name = name
    tool_call.function.arguments = json.dumps(arguments)
    return tool_call


def _make_llm_response(content: str = "ok", tool_calls: list[MagicMock] | None = None) -> MagicMock:
    message = MagicMock()
    message.content = content
    message.tool_calls = tool_calls or []
    message.model_dump.return_value = {
        "role": "assistant",
        "content": content,
        "tool_calls": tool_calls or [],
    }
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    usage = MagicMock()
    usage.prompt_tokens = 11
    usage.completion_tokens = 7
    response.usage = usage
    return response


@pytest.mark.asyncio
@patch("owlclaw.agent.runtime.runtime.llm_integration.acompletion")
async def test_e2e_closed_loop_release_gate(mock_llm: Any, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """External trigger -> runtime decision -> capability writeback -> ledger -> logs."""
    app_dir = _write_closed_loop_app_dir(tmp_path)
    loader = SkillsLoader(app_dir / "skills")
    loader.scan()
    registry = CapabilityRegistry(loader)
    writeback_store: list[dict[str, Any]] = []

    async def order_store_handler(session: dict[str, Any]) -> dict[str, Any]:
        payload = dict(session["payload"]["body"])
        writeback_store.append(payload)
        return {"written": True, "order_id": payload["order_id"]}
    registry.register_handler("order-store", order_store_handler)

    ledger = InMemoryLedger()
    await ledger.start()
    runtime = AgentRuntime(
        agent_id="closed-loop-agent",
        app_dir=str(app_dir),
        registry=registry,
        ledger=ledger,
    )
    await runtime.setup()

    tool_call = _make_tool_call("order-store", {})
    mock_llm.side_effect = [
        _make_llm_response(tool_calls=[tool_call]),
        _make_llm_response(content="done"),
    ]

    server = APITriggerServer(
        auth_provider=APIKeyAuthProvider({"k1"}),
        agent_runtime=runtime,
        ledger=ledger,
        agent_id="api-trigger",
    )
    server.register(
        APITriggerConfig(
            path="/api/v1/orders",
            method="POST",
            event_name="order_ingest",
            tenant_id="tenant-1",
            response_mode="sync",
        )
    )

    caplog.set_level(logging.INFO)
    transport = httpx.ASGITransport(app=server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/orders",
            headers={"X-API-Key": "k1"},
            json={"order_id": "ORD-1001", "amount": 99},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert writeback_store == [{"order_id": "ORD-1001", "amount": 99}]

    records = list(ledger._records)  # noqa: SLF001
    assert any(r.capability_name == "api_trigger" and r.agent_id == "api-trigger" for r in records)
    assert any(r.capability_name == "order-store" and r.status == "success" for r in records)
    llm_records = [r for r in records if r.capability_name == "llm_completion"]
    assert llm_records
    assert llm_records[-1].llm_tokens_input == 11
    assert llm_records[-1].llm_tokens_output == 7

    logs = caplog.text
    assert "Agent run started" in logs
    assert "trigger=order_ingest" in logs

    await ledger.stop()
