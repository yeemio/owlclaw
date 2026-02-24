"""Integration flows for signal router/API/runtime without external services."""

from __future__ import annotations

from typing import Any

import pytest
from starlette.applications import Starlette
from starlette.testclient import TestClient

from owlclaw.agent.runtime.runtime import AgentRuntime
from owlclaw.cli import agent_signal
from owlclaw.triggers.signal import (
    AgentStateManager,
    Signal,
    SignalRouter,
    SignalSource,
    SignalType,
    default_handlers,
    register_signal_admin_route,
)


class _Runtime:
    async def trigger_event(
        self,
        event_name: str,
        payload: dict[str, Any],
        focus: str | None = None,
        tenant_id: str = "default",
    ) -> dict[str, Any]:
        return {
            "event_name": event_name,
            "payload": payload,
            "focus": focus,
            "tenant_id": tenant_id,
            "run_id": "run-signal",
        }


class _Governance:
    async def allow_trigger(self, event_name: str, tenant_id: str) -> bool:  # noqa: ARG002
        return True


def _make_app_dir(tmp_path) -> str:
    (tmp_path / "SOUL.md").write_text("You are a helpful assistant.", encoding="utf-8")
    (tmp_path / "IDENTITY.md").write_text("## My Capabilities\n- x\n", encoding="utf-8")
    return str(tmp_path)


pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_pause_resume_and_trigger_flow_with_runtime_guard(monkeypatch, tmp_path) -> None:
    async def _fake_acompletion(**_: Any) -> dict[str, Any]:
        return {"choices": [{"message": {"role": "assistant", "content": "ok", "tool_calls": []}}]}

    monkeypatch.setattr("owlclaw.agent.runtime.runtime.llm_integration.acompletion", _fake_acompletion)

    state = AgentStateManager()
    runtime = AgentRuntime(
        agent_id="bot",
        app_dir=_make_app_dir(tmp_path),
        signal_state_manager=state,
    )
    await runtime.setup()
    router = SignalRouter(handlers=default_handlers(state=state, runtime=_Runtime(), governance=_Governance()))

    result_pause = await router.dispatch(
        Signal(
            type=SignalType.PAUSE,
            source=SignalSource.CLI,
            agent_id="bot",
            tenant_id="default",
            operator="op",
        )
    )
    assert result_pause.status == "paused"

    skipped = await runtime.trigger_event("cron")
    assert skipped["status"] == "skipped"
    assert skipped["reason"] == "agent_paused"

    result_resume = await router.dispatch(
        Signal(
            type=SignalType.RESUME,
            source=SignalSource.CLI,
            agent_id="bot",
            tenant_id="default",
            operator="op",
        )
    )
    assert result_resume.status == "resumed"

    completed = await runtime.trigger_event("cron")
    assert completed["status"] == "completed"


@pytest.mark.asyncio
async def test_http_admin_signal_endpoint_updates_state() -> None:
    state = AgentStateManager()
    router = SignalRouter(handlers=default_handlers(state=state, runtime=_Runtime(), governance=_Governance()))
    app = Starlette(routes=[])
    register_signal_admin_route(app_routes=app.router.routes, router=router, auth_provider=None, require_auth=False)

    with TestClient(app) as client:
        response = client.post("/admin/signal", json={"type": "pause", "agent_id": "a1", "tenant_id": "t1"})
        assert response.status_code == 200
        assert response.json()["status"] == "paused"

    current = await state.get("a1", "t1")
    assert current.paused is True


def test_cli_to_router_state_change_flow(monkeypatch) -> None:
    state = AgentStateManager()
    router = SignalRouter(handlers=default_handlers(state=state, runtime=_Runtime(), governance=_Governance()))
    monkeypatch.setattr(agent_signal, "_state_manager", state)
    monkeypatch.setattr(agent_signal, "_router", router)

    pause_result = agent_signal.pause_command(agent="a-cli", tenant="t-cli", operator="ops")
    assert pause_result["status"] == "paused"
    paused_state = agent_signal.status_command(agent="a-cli", tenant="t-cli")
    assert paused_state["paused"] is True

    resume_result = agent_signal.resume_command(agent="a-cli", tenant="t-cli", operator="ops")
    assert resume_result["status"] == "resumed"
    resumed_state = agent_signal.status_command(agent="a-cli", tenant="t-cli")
    assert resumed_state["paused"] is False


@pytest.mark.asyncio
async def test_instruct_then_runtime_run_contains_instruction(monkeypatch, tmp_path) -> None:
    async def _fake_acompletion(**_: Any) -> dict[str, Any]:
        return {"choices": [{"message": {"role": "assistant", "content": "ok", "tool_calls": []}}]}

    monkeypatch.setattr("owlclaw.agent.runtime.runtime.llm_integration.acompletion", _fake_acompletion)

    state = AgentStateManager()
    runtime = AgentRuntime(
        agent_id="bot",
        app_dir=_make_app_dir(tmp_path),
        signal_state_manager=state,
    )
    await runtime.setup()
    router = SignalRouter(handlers=default_handlers(state=state, runtime=_Runtime(), governance=_Governance()))
    instruct = await router.dispatch(
        Signal(
            type=SignalType.INSTRUCT,
            source=SignalSource.CLI,
            agent_id="bot",
            tenant_id="default",
            operator="ops",
            message="check risk limits first",
        )
    )
    assert instruct.status == "instruction_queued"

    recorded_messages: dict[str, Any] = {}

    async def _capture_decision_loop(context, trace=None):  # noqa: ANN001, ANN202
        recorded_messages["payload"] = context.payload
        return {"status": "completed", "run_id": context.run_id, "iterations": 1, "final_response": "ok", "tool_calls_total": 0}

    runtime._decision_loop = _capture_decision_loop  # type: ignore[method-assign]
    result = await runtime.trigger_event("cron")
    assert result["status"] == "completed"
    assert "signal_instructions" in recorded_messages["payload"]
    assert recorded_messages["payload"]["signal_instructions"][0]["content"] == "check risk limits first"
