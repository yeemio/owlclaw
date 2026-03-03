"""Basic tests for OwlClaw application."""

import asyncio
import logging
from unittest.mock import AsyncMock, patch

import pytest

from owlclaw import OwlClaw, __version__
from owlclaw.integrations import llm as llm_integration


def test_version():
    assert __version__ == "0.1.0"


def test_app_creation():
    app = OwlClaw("test-app")
    assert app.name == "test-app"


def test_app_creation_validates_name():
    with pytest.raises(ValueError, match="non-empty string"):
        OwlClaw("   ")
    with pytest.raises(ValueError, match="non-empty string"):
        OwlClaw(None)  # type: ignore[arg-type]


def test_mount_skills_and_decorators(tmp_path):
    """mount_skills() scans directory; @handler and @state register with registry."""
    (tmp_path / "entry-monitor").mkdir()
    (tmp_path / "entry-monitor" / "SKILL.md").write_text(
        "---\nname: entry-monitor\ndescription: Check entry\n---\n",
        encoding="utf-8",
    )
    app = OwlClaw("test-app")
    app.mount_skills(str(tmp_path))
    assert app.skills_loader is not None
    assert app.registry is not None
    assert app.knowledge_injector is not None
    assert len(app.skills_loader.list_skills()) == 1

    @app.handler("entry-monitor")
    async def check_entry(session):
        return {"done": True}

    @app.state("market_state")
    def get_market():
        return {"price": 100}

    assert app.registry.list_capabilities() == [
        {
            "name": "entry-monitor",
            "description": "Check entry",
            "task_type": None,
            "constraints": {},
            "focus": [],
            "risk_level": "low",
            "requires_confirmation": False,
            "handler": "check_entry",
        }
    ]


def test_mount_skills_validates_path():
    app = OwlClaw("test-app")
    with pytest.raises(ValueError, match="path must be a non-empty string"):
        app.mount_skills("   ")
    with pytest.raises(ValueError, match="path must be a non-empty string"):
        app.mount_skills(None)  # type: ignore[arg-type]


def test_handler_before_mount_skills_raises():
    """Using @handler before mount_skills() raises RuntimeError."""
    app = OwlClaw("test-app")

    with pytest.raises(RuntimeError, match="mount_skills"):
        @app.handler("x")
        def h():
            pass


def test_state_before_mount_skills_raises():
    """Using @state before mount_skills() raises RuntimeError."""
    app = OwlClaw("test-app")

    with pytest.raises(RuntimeError, match="mount_skills"):
        @app.state("x")
        def s():
            return {}


def test_create_agent_runtime_returns_runtime_with_builtin_tools(tmp_path):
    """create_agent_runtime() returns AgentRuntime with registry, builtin_tools."""
    (tmp_path / "entry-monitor").mkdir()
    (tmp_path / "entry-monitor" / "SKILL.md").write_text(
        "---\nname: entry-monitor\ndescription: Check entry\n---\n",
        encoding="utf-8",
    )
    (tmp_path / "SOUL.md").write_text("# Soul\nYou are a trading agent.", encoding="utf-8")
    app = OwlClaw("test-app")
    app.mount_skills(str(tmp_path))
    rt = app.create_agent_runtime(app_dir=str(tmp_path))
    assert rt.agent_id == "test-app"
    assert rt.app_dir == str(tmp_path)
    assert rt.registry is app.registry
    assert rt.builtin_tools is not None
    schemas = rt.builtin_tools.get_tool_schemas()
    names = [s["function"]["name"] for s in schemas]
    assert "query_state" in names
    assert "log_decision" in names
    assert "schedule_once" in names


def test_create_agent_runtime_passes_configured_model(tmp_path):
    (tmp_path / "entry-monitor").mkdir()
    (tmp_path / "entry-monitor" / "SKILL.md").write_text(
        "---\nname: entry-monitor\ndescription: Check entry\n---\n",
        encoding="utf-8",
    )
    (tmp_path / "SOUL.md").write_text("# Soul\nYou are a trading agent.", encoding="utf-8")
    app = OwlClaw("test-app-model")
    app.mount_skills(str(tmp_path))
    app.configure(model="deepseek/deepseek-chat")
    rt = app.create_agent_runtime(app_dir=str(tmp_path))
    assert rt.model == "deepseek/deepseek-chat"


def test_create_agent_runtime_before_mount_skills_raises():
    app = OwlClaw("test-app")
    with pytest.raises(RuntimeError, match="mount_skills"):
        app.create_agent_runtime(app_dir="/tmp")


def test_create_agent_runtime_validates_app_dir_when_provided(tmp_path):
    (tmp_path / "entry-monitor").mkdir()
    (tmp_path / "entry-monitor" / "SKILL.md").write_text(
        "---\nname: entry-monitor\ndescription: Check entry\n---\n",
        encoding="utf-8",
    )
    app = OwlClaw("test-app")
    app.mount_skills(str(tmp_path))
    with pytest.raises(ValueError, match="app_dir must be a non-empty string"):
        app.create_agent_runtime(app_dir="   ")


def test_run_requires_mount_skills():
    app = OwlClaw("test-app")
    with pytest.raises(RuntimeError, match="mount_skills"):
        app.run()


@pytest.mark.asyncio
async def test_e2e_skill_load_and_invoke(tmp_path):
    """End-to-end: mount_skills, register handler, invoke via registry."""
    (tmp_path / "entry-monitor").mkdir()
    (tmp_path / "entry-monitor" / "SKILL.md").write_text(
        "---\nname: entry-monitor\ndescription: Check entry\n---\n",
        encoding="utf-8",
    )
    app = OwlClaw("test-app")
    app.mount_skills(str(tmp_path))

    @app.handler("entry-monitor")
    async def check_entry(session):
        return {"signal": session.get("ticker", "unknown")}

    result = await app.registry.invoke_handler("entry-monitor", session={"ticker": "AAPL"})
    assert result == {"signal": "AAPL"}


@pytest.mark.asyncio
async def test_start_registers_cron_and_exposes_health(tmp_path):
    (tmp_path / "entry-monitor").mkdir()
    (tmp_path / "entry-monitor" / "SKILL.md").write_text(
        "---\nname: entry-monitor\ndescription: Check entry\n---\n",
        encoding="utf-8",
    )
    (tmp_path / "SOUL.md").write_text("# Soul\nYou are a test agent.", encoding="utf-8")
    (tmp_path / "IDENTITY.md").write_text("# Identity\nTest identity.", encoding="utf-8")
    app = OwlClaw("test-app")
    app.mount_skills(str(tmp_path / "entry-monitor"))

    @app.cron("0 * * * *", event_name="hourly_job")
    async def hourly_job():
        return {"ok": True}

    from unittest.mock import MagicMock

    hatchet = MagicMock()
    hatchet.task = MagicMock(return_value=lambda fn: fn)

    runtime = await app.start(app_dir=str(tmp_path), hatchet_client=hatchet)
    assert runtime.is_initialized is True
    assert hatchet.task.call_count >= 1

    health = app.health_status()
    assert health["runtime_initialized"] is True
    assert health["cron"]["total_triggers"] >= 1

    await app.stop()


# --- Lite Mode tests ---


def test_lite_creates_app_with_lite_flag():
    app = OwlClaw.lite("demo")
    assert app._lite_mode is True
    assert app.name == "demo"


def test_lite_governance_uses_inmemory_ledger():
    app = OwlClaw.lite("demo-gov")
    app._ensure_governance()
    assert type(app._ledger).__name__ == "InMemoryLedger"
    assert app._visibility_filter is not None


def test_lite_custom_mock_responses():
    app = OwlClaw.lite(
        "demo-custom",
        mock_responses={"monitor": {"content": "all clear"}},
    )
    assert app._lite_mode is True


@pytest.mark.asyncio
async def test_lite_runtime_disables_heartbeat_checker(tmp_path) -> None:
    (tmp_path / "inventory-check").mkdir()
    (tmp_path / "inventory-check" / "SKILL.md").write_text(
        "---\nname: inventory-check\ndescription: Check inventory\n---\n",
        encoding="utf-8",
    )
    (tmp_path / "SOUL.md").write_text("# Soul\nLite mode test.", encoding="utf-8")
    (tmp_path / "IDENTITY.md").write_text("# Identity\nLite mode test.", encoding="utf-8")
    app = OwlClaw.lite("lite-heartbeat", skills_path=str(tmp_path))
    runtime = app.create_agent_runtime(app_dir=str(tmp_path))
    await runtime.setup()
    try:
        assert runtime._heartbeat_checker is None  # noqa: SLF001
    finally:
        await app.stop()


@pytest.mark.asyncio
async def test_lite_configures_global_llm_mock_and_stop_clears_it() -> None:
    app = OwlClaw.lite(
        "demo-mock",
        mock_responses={
            "default": {
                "content": "mock ok",
                "function_calls": [{"name": "inventory_check", "arguments": {"sku": "A1"}}],
            }
        },
    )
    mock_result = await llm_integration.acompletion(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "check"}],
    )
    assert mock_result.model == "mock"
    assert mock_result.choices[0].message.tool_calls[0].function.name == "inventory_check"
    await app.stop()
    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_real:
        mock_real.return_value = mock_result
        await llm_integration.acompletion(model="gpt-4o-mini", messages=[])
    mock_real.assert_awaited_once()


def test_normal_mode_no_inmemory_ledger_by_default():
    app = OwlClaw("normal")
    app.configure(governance={"router": {}})
    app._ensure_governance()
    assert app._ledger is None


def test_normal_mode_inmemory_ledger_opt_in():
    app = OwlClaw("opt-in")
    app.configure(governance={"use_inmemory_ledger": True, "router": {}})
    app._ensure_governance()
    assert type(app._ledger).__name__ == "InMemoryLedger"


def test_ensure_logging_does_not_override_existing_handler() -> None:
    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)
    try:
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)
        custom_handler = logging.StreamHandler()
        root_logger.addHandler(custom_handler)
        OwlClaw._ensure_logging()
        assert root_logger.handlers == [custom_handler]
    finally:
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)
        for handler in original_handlers:
            root_logger.addHandler(handler)


@pytest.mark.asyncio
async def test_run_once_uses_runtime_trigger_event_and_returns_decision_info() -> None:
    app = OwlClaw("run-once")
    runtime = AsyncMock()
    runtime.trigger_event = AsyncMock(
        return_value={
            "status": "completed",
            "run_id": "run-1",
            "iterations": 1,
            "tool_calls_total": 2,
            "final_response": "done",
        }
    )
    app.start = AsyncMock(return_value=runtime)  # type: ignore[method-assign]
    app.stop = AsyncMock()  # type: ignore[method-assign]

    result = await app._run_once_async(
        event_name="manual",
        payload={"source": "test"},
        focus="ops",
        app_dir=None,
        hatchet_client=None,
        tenant_id="default",
    )

    runtime.trigger_event.assert_awaited_once_with(
        event_name="manual",
        payload={"source": "test"},
        focus="ops",
        tenant_id="default",
    )
    assert result["status"] == "completed"
    assert result["decision"]["tool_calls_total"] == 2
    assert result["decision"]["final_response"] == "done"


@pytest.mark.asyncio
async def test_heartbeat_loop_logs_trigger_and_result(caplog) -> None:
    app = OwlClaw("hb-logs")
    shutdown_event = asyncio.Event()

    async def _trigger_event(**_: object) -> dict[str, object]:
        shutdown_event.set()
        return {"status": "completed", "tool_calls_total": 1}

    runtime = AsyncMock()
    runtime.trigger_event = AsyncMock(side_effect=_trigger_event)

    with caplog.at_level(logging.INFO):
        await app._heartbeat_loop(
            runtime=runtime,
            interval_minutes=0.00001,
            tenant_id="default",
            shutdown_event=shutdown_event,
        )

    assert "Heartbeat tick" in caplog.text
    assert "Heartbeat result" in caplog.text


@pytest.mark.asyncio
async def test_inmemory_ledger_record_and_query():
    from datetime import date
    from decimal import Decimal

    from owlclaw.governance import InMemoryLedger
    from owlclaw.governance.ledger import LedgerQueryFilters

    ledger = InMemoryLedger()
    await ledger.start()
    await ledger.record_execution(
        tenant_id="t1",
        agent_id="a1",
        run_id="r1",
        capability_name="check",
        task_type="monitor",
        input_params={"key": "val"},
        output_result=None,
        decision_reasoning=None,
        execution_time_ms=100,
        llm_model="mock",
        llm_tokens_input=10,
        llm_tokens_output=5,
        estimated_cost=Decimal("0.001"),
        status="success",
    )
    records = await ledger.query_records("t1", LedgerQueryFilters(agent_id="a1"))
    assert len(records) == 1
    assert records[0].capability_name == "check"

    summary = await ledger.get_cost_summary("t1", "a1", date.today(), date.today())
    assert summary.total_cost == Decimal("0.001")
    await ledger.stop()
