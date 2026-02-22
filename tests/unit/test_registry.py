"""Unit tests for Capability Registry (handlers and state providers)."""

import pytest

from owlclaw.capabilities.registry import CapabilityRegistry
from owlclaw.capabilities.skills import SkillsLoader


@pytest.fixture
def skills_loader_with_skill(tmp_path):
    """SkillsLoader with one Skill (entry-monitor) for registry tests."""
    skill_dir = tmp_path / "entry-monitor"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: entry-monitor\ndescription: Check entry\n---\n",
        encoding="utf-8",
    )
    loader = SkillsLoader(tmp_path)
    loader.scan()
    return loader


@pytest.fixture
def registry(skills_loader_with_skill):
    """CapabilityRegistry with given SkillsLoader."""
    return CapabilityRegistry(skills_loader_with_skill)


def test_register_handler(registry):
    """register_handler() stores handler and it appears in list_capabilities."""
    def my_handler(session):
        return {"ok": True}

    registry.register_handler("entry-monitor", my_handler)
    caps = registry.list_capabilities()
    assert len(caps) == 1
    assert caps[0]["name"] == "entry-monitor"
    assert caps[0]["handler"] == "my_handler"
    meta = registry.get_capability_metadata("entry-monitor")
    assert meta is not None
    assert meta["name"] == "entry-monitor"
    assert meta["handler"] == "my_handler"


def test_register_handler_duplicate_raises(registry):
    """Registering handler for same skill_name twice raises ValueError."""
    def h1():
        pass

    def h2():
        pass

    registry.register_handler("entry-monitor", h1)
    with pytest.raises(ValueError, match="already registered"):
        registry.register_handler("entry-monitor", h2)


@pytest.mark.asyncio
async def test_invoke_handler_success_sync(registry):
    """invoke_handler() calls sync handler and returns result."""
    def sync_handler(session):
        return {"result": session.get("x", 0) + 1}

    registry.register_handler("entry-monitor", sync_handler)
    result = await registry.invoke_handler("entry-monitor", session={"x": 2})
    assert result == {"result": 3}


@pytest.mark.asyncio
async def test_invoke_handler_success_async(registry):
    """invoke_handler() calls async handler and returns result."""
    async def async_handler(session):
        return {"async": True, "session": session}

    registry.register_handler("entry-monitor", async_handler)
    result = await registry.invoke_handler("entry-monitor", session={})
    assert result == {"async": True, "session": {}}


@pytest.mark.asyncio
async def test_invoke_handler_not_found_raises(registry):
    """invoke_handler() for unregistered skill raises ValueError."""
    with pytest.raises(ValueError, match="No handler registered"):
        await registry.invoke_handler("entry-monitor")


@pytest.mark.asyncio
async def test_invoke_handler_failure_wraps(registry):
    """invoke_handler() wraps handler exception in RuntimeError."""
    def failing_handler():
        raise ValueError("handler failed")

    registry.register_handler("entry-monitor", failing_handler)
    with pytest.raises(RuntimeError, match="failed"):
        await registry.invoke_handler("entry-monitor")


@pytest.mark.asyncio
async def test_invoke_handler_maps_kwargs_to_session_when_missing(registry):
    """If handler expects session, raw kwargs are mapped into session."""
    def sync_handler(session):
        return {"symbol": session.get("symbol")}

    registry.register_handler("entry-monitor", sync_handler)
    result = await registry.invoke_handler("entry-monitor", symbol="AAPL")
    assert result == {"symbol": "AAPL"}


@pytest.mark.asyncio
async def test_invoke_handler_filters_unknown_kwargs(registry):
    """Unknown kwargs are filtered out for explicitly typed handlers."""
    def sync_handler(symbol):
        return {"symbol": symbol}

    registry.register_handler("entry-monitor", sync_handler)
    result = await registry.invoke_handler(
        "entry-monitor",
        symbol="AAPL",
        unexpected="x",
    )
    assert result == {"symbol": "AAPL"}


@pytest.mark.asyncio
async def test_invoke_handler_single_param_without_args_raises(registry):
    """No args should not be coerced to empty dict for single-param handlers."""
    def sync_handler(symbol):
        return {"symbol": symbol}

    registry.register_handler("entry-monitor", sync_handler)
    with pytest.raises(RuntimeError, match="missing 1 required positional argument"):
        await registry.invoke_handler("entry-monitor")


def test_register_state(registry):
    """register_state() accepts sync and async providers."""
    def sync_state():
        return {"count": 1}

    registry.register_state("market_state", sync_state)
    assert "market_state" in registry.states


def test_register_state_duplicate_raises(registry):
    """Registering state for same name twice raises ValueError."""
    def p1():
        return {}

    def p2():
        return {}

    registry.register_state("market_state", p1)
    with pytest.raises(ValueError, match="already registered"):
        registry.register_state("market_state", p2)


@pytest.mark.asyncio
async def test_get_state_success_sync(registry):
    """get_state() returns dict from sync provider."""
    def sync_provider():
        return {"key": "value"}

    registry.register_state("market_state", sync_provider)
    result = await registry.get_state("market_state")
    assert result == {"key": "value"}


@pytest.mark.asyncio
async def test_get_state_success_async(registry):
    """get_state() returns dict from async provider."""
    async def async_provider():
        return {"async": True}

    registry.register_state("market_state", async_provider)
    result = await registry.get_state("market_state")
    assert result == {"async": True}


@pytest.mark.asyncio
async def test_get_state_not_found_raises(registry):
    """get_state() for unregistered state raises ValueError."""
    with pytest.raises(ValueError, match="No state provider registered"):
        await registry.get_state("nonexistent")


@pytest.mark.asyncio
async def test_get_state_non_dict_raises(registry):
    """get_state() when provider returns non-dict raises (TypeError wrapped in RuntimeError)."""
    def bad_provider():
        return "not a dict"

    registry.register_state("bad_state", bad_provider)
    with pytest.raises(RuntimeError, match="must return dict"):
        await registry.get_state("bad_state")


def test_filter_by_task_type(tmp_path):
    """filter_by_task_type() returns skill names matching task_type."""
    for name, task_type in [("a", "t1"), ("b", "t1"), ("c", "t2")]:
        (tmp_path / name).mkdir()
        (tmp_path / name / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: Skill {name}\nowlclaw:\n  task_type: {task_type}\n---\n",
            encoding="utf-8",
        )
    loader = SkillsLoader(tmp_path)
    loader.scan()
    reg = CapabilityRegistry(loader)
    reg.register_handler("a", lambda: None)
    reg.register_handler("b", lambda: None)
    reg.register_handler("c", lambda: None)
    t1 = reg.filter_by_task_type("t1")
    assert set(t1) == {"a", "b"}
    t2 = reg.filter_by_task_type("t2")
    assert t2 == ["c"]


def test_capability_metadata_includes_focus_and_risk(tmp_path):
    """list/get metadata should expose v4.1 risk and focus extensions."""
    (tmp_path / "x").mkdir()
    (tmp_path / "x" / "SKILL.md").write_text(
        "---\n"
        "name: x\n"
        "description: Skill x\n"
        "owlclaw:\n"
        "  task_type: t1\n"
        "  focus: [inventory_monitor]\n"
        "  risk_level: high\n"
        "---\n",
        encoding="utf-8",
    )
    loader = SkillsLoader(tmp_path)
    loader.scan()
    reg = CapabilityRegistry(loader)
    reg.register_handler("x", lambda: None)
    caps = reg.list_capabilities()
    assert caps[0]["focus"] == ["inventory_monitor"]
    assert caps[0]["risk_level"] == "high"
    assert caps[0]["requires_confirmation"] is True
    meta = reg.get_capability_metadata("x")
    assert meta is not None
    assert meta["focus"] == ["inventory_monitor"]
    assert meta["risk_level"] == "high"
    assert meta["requires_confirmation"] is True
