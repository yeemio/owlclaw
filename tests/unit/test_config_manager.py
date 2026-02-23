"""Unit tests for ConfigManager precedence and listener behavior."""

from __future__ import annotations

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from owlclaw.config.manager import ConfigManager


def test_config_manager_load_precedence_defaults_yaml_env_overrides(
    monkeypatch,
    tmp_path: Path,
) -> None:
    yaml_path = tmp_path / "owlclaw.yaml"
    yaml_path.write_text(
        "agent:\n"
        "  heartbeat_interval_minutes: 45\n"
        "integrations:\n"
        "  llm:\n"
        "    model: from-yaml\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("OWLCLAW_AGENT__HEARTBEAT_INTERVAL_MINUTES", "50")
    monkeypatch.setenv("OWLCLAW_INTEGRATIONS__LLM__MODEL", "from-env")

    manager = ConfigManager.load(
        config_path=str(yaml_path),
        overrides={"agent": {"heartbeat_interval_minutes": 60}},
    )
    cfg = manager.get()
    assert cfg.agent.heartbeat_interval_minutes == 60
    assert cfg.integrations.llm.model == "from-env"


def test_config_manager_load_notifies_listener(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("OWLCLAW_AGENT__HEARTBEAT_INTERVAL_MINUTES", raising=False)
    ConfigManager._instance = None
    manager = ConfigManager.instance()
    events: list[tuple[int, int]] = []

    def _listener(old, new) -> None:
        events.append((old.agent.heartbeat_interval_minutes, new.agent.heartbeat_interval_minutes))

    manager.on_change(_listener)

    yaml_path = tmp_path / "owlclaw.yaml"
    yaml_path.write_text("agent:\n  heartbeat_interval_minutes: 41\n", encoding="utf-8")
    ConfigManager.load(config_path=str(yaml_path))

    assert events
    assert events[-1][1] == 41


def test_config_manager_instance_thread_safe_singleton() -> None:
    ConfigManager._instance = None

    def _get_id() -> int:
        return id(ConfigManager.instance())

    with ThreadPoolExecutor(max_workers=8) as pool:
        ids = list(pool.map(lambda _: _get_id(), range(32)))

    assert len(set(ids)) == 1
