"""Integration tests for configuration pipeline."""

from __future__ import annotations

from pathlib import Path

from owlclaw.config import ConfigManager, register_runtime_reload_listener


def test_config_manager_full_load_chain(monkeypatch, tmp_path: Path) -> None:
    """defaults -> yaml -> env -> runtime overrides."""
    ConfigManager._reset_for_tests()
    cfg = tmp_path / "owlclaw.yaml"
    cfg.write_text(
        "agent:\n  heartbeat_interval_minutes: 20\nintegrations:\n  llm:\n    model: gpt-4o-mini\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("OWLCLAW_AGENT__HEARTBEAT_INTERVAL_MINUTES", "40")
    manager = ConfigManager.load(
        config_path=str(cfg),
        overrides={"agent": {"heartbeat_interval_minutes": 60}},
    )
    assert manager.get().agent.heartbeat_interval_minutes == 60


def test_reload_end_to_end_with_listener(tmp_path: Path) -> None:
    """Reload should apply hot fields and notify runtime listener."""
    ConfigManager._reset_for_tests()
    cfg = tmp_path / "owlclaw.yaml"
    cfg.write_text("agent:\n  heartbeat_interval_minutes: 30\n", encoding="utf-8")
    manager = ConfigManager.load(config_path=str(cfg))

    class RuntimeStub:
        agent_id = "agent-x"
        config = {"heartbeat": {"enabled": True}}
        _heartbeat_checker = None

    runtime = RuntimeStub()
    register_runtime_reload_listener(runtime, manager=manager)

    cfg.write_text("agent:\n  heartbeat_interval_minutes: 15\n", encoding="utf-8")
    result = manager.reload()
    assert "agent.heartbeat_interval_minutes" in result.applied
    assert runtime.config["heartbeat"]["interval_minutes"] == 15
    assert runtime._heartbeat_checker is not None

