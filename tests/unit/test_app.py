"""Basic tests for OwlClaw application."""

import pytest

from owlclaw import OwlClaw, __version__


def test_version():
    assert __version__ == "0.1.0"


def test_app_creation():
    app = OwlClaw("test-app")
    assert app.name == "test-app"


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


def test_create_agent_runtime_before_mount_skills_raises():
    app = OwlClaw("test-app")
    with pytest.raises(RuntimeError, match="mount_skills"):
        app.create_agent_runtime(app_dir="/tmp")


def test_run_raises_until_implemented():
    app = OwlClaw("test-app")
    with pytest.raises(RuntimeError, match="not implemented yet"):
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
