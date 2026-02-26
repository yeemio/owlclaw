"""Migration gate integration tests for AgentRuntime tool execution."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlclaw.agent.runtime.context import AgentRunContext
from owlclaw.agent.runtime.runtime import AgentRuntime
from owlclaw.capabilities.registry import CapabilityRegistry
from owlclaw.capabilities.skills import SkillsLoader
from owlclaw.governance import InMemoryLedger


def _make_runtime_app(tmp_path: Path, migration_weight: int) -> tuple[AgentRuntime, CapabilityRegistry]:
    (tmp_path / "SOUL.md").write_text("You are a helper.", encoding="utf-8")
    (tmp_path / "IDENTITY.md").write_text("## My Capabilities\n- inventory-check\n", encoding="utf-8")
    (tmp_path / "owlclaw.yaml").write_text(
        f"skills:\n  inventory-check:\n    migration_weight: {migration_weight}\n",
        encoding="utf-8",
    )
    skill_dir = tmp_path / "skills" / "inventory-check"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: inventory-check
description: Inventory check
owlclaw:
  task_type: monitor
---
# Inventory Check
""",
        encoding="utf-8",
    )
    loader = SkillsLoader(tmp_path / "skills")
    loader.scan()
    registry = CapabilityRegistry(loader)
    registry.register_handler("inventory-check", AsyncMock(return_value={"action": "ok"}))
    runtime = AgentRuntime(
        agent_id="bot",
        app_dir=str(tmp_path),
        registry=registry,
        ledger=InMemoryLedger(),
    )
    return runtime, registry


def _make_llm_response(*, tool_call: bool) -> MagicMock:
    message = MagicMock()
    if tool_call:
        tc = MagicMock()
        tc.id = "tc_1"
        tc.function.name = "inventory-check"
        tc.function.arguments = json.dumps({"amount": 10})
        message.tool_calls = [tc]
        message.content = ""
    else:
        message.tool_calls = []
        message.content = "done"
    message.model_dump.return_value = {"role": "assistant", "content": message.content, "tool_calls": message.tool_calls}
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    usage = MagicMock()
    usage.prompt_tokens = 1
    usage.completion_tokens = 1
    response.usage = usage
    return response


@pytest.mark.asyncio
@patch("owlclaw.agent.runtime.runtime.llm_integration.acompletion")
async def test_runtime_observe_only_skips_handler(mock_llm: MagicMock, tmp_path: Path) -> None:
    mock_llm.side_effect = [_make_llm_response(tool_call=True), _make_llm_response(tool_call=False)]
    runtime, registry = _make_runtime_app(tmp_path, migration_weight=0)
    await runtime.setup()
    result = await runtime.run(AgentRunContext(agent_id="bot", trigger="cron"))
    assert result["status"] == "completed"
    assert result["tool_calls_total"] == 1
    registry.handlers["inventory-check"].assert_not_called()  # type: ignore[union-attr]


@pytest.mark.asyncio
@patch("owlclaw.agent.runtime.runtime.llm_integration.acompletion")
async def test_runtime_require_approval_creates_pending_request(mock_llm: MagicMock, tmp_path: Path) -> None:
    mock_llm.side_effect = [_make_llm_response(tool_call=True), _make_llm_response(tool_call=False)]
    runtime, registry = _make_runtime_app(tmp_path, migration_weight=30)
    assert runtime._migration_gate is not None  # noqa: SLF001
    runtime._migration_gate._random_fn = lambda: 0.99  # noqa: SLF001
    await runtime.setup()
    result = await runtime.run(AgentRunContext(agent_id="bot", trigger="cron"))
    assert result["status"] == "completed"
    registry.handlers["inventory-check"].assert_not_called()  # type: ignore[union-attr]
    assert runtime._approval_queue is not None  # noqa: SLF001
    pending = await runtime._approval_queue.list(tenant_id="default")  # noqa: SLF001
    assert len(pending) == 1
    assert pending[0].status.value == "pending"
