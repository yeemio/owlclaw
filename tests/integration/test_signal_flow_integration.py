"""Integration tests for signal multi-entry flows."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from starlette.testclient import TestClient

from owlclaw.agent.runtime.context import AgentRunContext
from owlclaw.agent.runtime.runtime import AgentRuntime
from owlclaw.cli.agent_signal import pause_command, status_command
from owlclaw.triggers.api import APITriggerServer
from owlclaw.triggers.api.auth import BearerTokenAuthProvider
from owlclaw.triggers.signal import AgentStateManager, Signal, SignalRouter, SignalSource, SignalType, default_handlers

pytestmark = pytest.mark.integration


def _make_app_dir(tmp_path) -> str:
    (tmp_path / "SOUL.md").write_text("You are a helpful assistant.", encoding="utf-8")
    (tmp_path / "IDENTITY.md").write_text("## My Capabilities\n- market_scan\n", encoding="utf-8")
    return str(tmp_path)


def _make_llm_response(content: str = "Done.") -> MagicMock:
    message = MagicMock()
    message.content = content
    message.tool_calls = []
    message.model_dump.return_value = {"role": "assistant", "content": content, "tool_calls": []}
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    usage = MagicMock()
    usage.prompt_tokens = 0
    usage.completion_tokens = 0
    response.usage = usage
    return response


class _Runtime:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def trigger_event(self, event_name: str, payload: dict, focus: str | None = None, tenant_id: str = "default") -> dict:
        self.calls.append({"event_name": event_name, "payload": payload, "focus": focus, "tenant_id": tenant_id})
        return {"run_id": "run-1"}


@pytest.mark.asyncio
async def test_http_api_signal_updates_state_through_router() -> None:
    runtime = _Runtime()
    state = AgentStateManager(max_pending_instructions=4)
    router = SignalRouter(handlers=default_handlers(state=state, runtime=runtime))
    server = APITriggerServer(auth_provider=BearerTokenAuthProvider({"token-1"}), agent_runtime=runtime)
    server.register_signal_admin(signal_router=router, require_auth=True)

    with TestClient(server.app) as client:
        response = client.post(
            "/admin/signal",
            headers={"Authorization": "Bearer token-1"},
            json={"type": "pause", "agent_id": "a1", "tenant_id": "default"},
        )
    assert response.status_code == 200
    snapshot = await state.get("a1", "default")
    assert snapshot.paused is True


def test_cli_signal_commands_change_state_in_process() -> None:
    pause_result = pause_command(agent="cli-a1", tenant="default", operator="op")
    assert pause_result["status"] in {"paused", "already_paused"}

    status_result = status_command(agent="cli-a1", tenant="default")
    assert status_result["paused"] is True


@pytest.mark.asyncio
async def test_pause_blocks_cron_run_and_resume_restores(tmp_path) -> None:
    state = AgentStateManager(max_pending_instructions=4)
    runtime = AgentRuntime(agent_id="bot", app_dir=_make_app_dir(tmp_path), signal_state_manager=state)
    await runtime.setup()
    await state.set_paused("bot", "default", True)

    with patch("owlclaw.agent.runtime.runtime.llm_integration.acompletion") as mock_llm:
        mock_llm.return_value = _make_llm_response("Done.")
        skipped = await runtime.run(AgentRunContext(agent_id="bot", trigger="market_open", payload={"trigger_type": "cron"}))
        assert skipped["status"] == "skipped"
        assert skipped["reason"] == "agent_paused"
        mock_llm.assert_not_called()

        await state.set_paused("bot", "default", False)
        resumed = await runtime.run(AgentRunContext(agent_id="bot", trigger="market_open", payload={"trigger_type": "cron"}))
        assert resumed["status"] == "completed"
        assert mock_llm.called


@pytest.mark.asyncio
async def test_instruct_signal_is_injected_into_next_run_payload(tmp_path) -> None:
    state = AgentStateManager(max_pending_instructions=4)
    runtime_stub = _Runtime()
    router = SignalRouter(handlers=default_handlers(state=state, runtime=runtime_stub))
    runtime = AgentRuntime(agent_id="bot", app_dir=_make_app_dir(tmp_path), signal_state_manager=state)
    await runtime.setup()

    instruct_result = await router.dispatch(
        Signal(
            type=SignalType.INSTRUCT,
            source=SignalSource.CLI,
            agent_id="bot",
            tenant_id="default",
            operator="ops",
            message="hold buy orders",
            ttl_seconds=3600,
        )
    )
    assert instruct_result.status == "instruction_queued"

    context = AgentRunContext(agent_id="bot", trigger="manual", payload={"task_type": "ops"})
    with patch("owlclaw.agent.runtime.runtime.llm_integration.acompletion") as mock_llm:
        mock_llm.return_value = _make_llm_response("Done.")
        result = await runtime.run(context)
    assert result["status"] == "completed"
    injected = context.payload.get("operator_instructions")
    assert isinstance(injected, list)
    assert injected[0]["content"] == "hold buy orders"
