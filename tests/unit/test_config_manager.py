"""Unit tests for ConfigManager."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from owlclaw.config.manager import ConfigManager


def _write_yaml(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def test_config_manager_singleton() -> None:
    ConfigManager._reset_for_tests()
    m1 = ConfigManager.instance()
    m2 = ConfigManager.instance()
    assert m1 is m2


def test_config_manager_load_get_and_override(tmp_path: Path) -> None:
    ConfigManager._reset_for_tests()
    cfg_path = tmp_path / "owlclaw.yaml"
    _write_yaml(
        cfg_path,
        "agent:\n  heartbeat_interval_minutes: 45\nintegrations:\n  llm:\n    model: gpt-4o\n",
    )
    manager = ConfigManager.load(
        config_path=str(cfg_path),
        overrides={"agent": {"heartbeat_interval_minutes": 60}},
    )
    cfg = manager.get()
    assert cfg.agent.heartbeat_interval_minutes == 60
    assert cfg.integrations.llm.model == "gpt-4o"


def test_config_manager_on_change_is_notified(tmp_path: Path) -> None:
    ConfigManager._reset_for_tests()
    cfg_path = tmp_path / "owlclaw.yaml"
    _write_yaml(cfg_path, "agent:\n  heartbeat_interval_minutes: 30\n")
    manager = ConfigManager.load(config_path=str(cfg_path))

    seen: list[tuple[int, int]] = []

    def _listener(old_cfg, new_cfg) -> None:  # type: ignore[no-untyped-def]
        seen.append(
            (
                old_cfg.agent.heartbeat_interval_minutes,
                new_cfg.agent.heartbeat_interval_minutes,
            )
        )

    manager.on_change(_listener)
    ConfigManager.load(
        config_path=str(cfg_path),
        overrides={"agent": {"heartbeat_interval_minutes": 90}},
    )
    assert seen[-1] == (30, 90)


def test_config_manager_get_is_thread_safe(tmp_path: Path) -> None:
    ConfigManager._reset_for_tests()
    cfg_path = tmp_path / "owlclaw.yaml"
    _write_yaml(cfg_path, "agent:\n  heartbeat_interval_minutes: 35\n")
    manager = ConfigManager.load(config_path=str(cfg_path))

    def _read_value() -> int:
        return manager.get().agent.heartbeat_interval_minutes

    with ThreadPoolExecutor(max_workers=8) as pool:
        values = list(pool.map(lambda _: _read_value(), range(32)))
    assert all(v == 35 for v in values)


def test_config_manager_env_overrides_yaml(monkeypatch, tmp_path: Path) -> None:
    ConfigManager._reset_for_tests()
    cfg_path = tmp_path / "owlclaw.yaml"
    _write_yaml(
        cfg_path,
        "agent:\n  heartbeat_interval_minutes: 40\nsecurity:\n  sanitizer:\n    enabled: true\n",
    )
    monkeypatch.setenv("OWLCLAW_AGENT__HEARTBEAT_INTERVAL_MINUTES", "55")
    monkeypatch.setenv("OWLCLAW_SECURITY__SANITIZER__ENABLED", "false")
    manager = ConfigManager.load(config_path=str(cfg_path))
    cfg = manager.get()
    assert cfg.agent.heartbeat_interval_minutes == 55
    assert cfg.security.sanitizer.enabled is False


def test_config_manager_runtime_overrides_env(monkeypatch, tmp_path: Path) -> None:
    ConfigManager._reset_for_tests()
    cfg_path = tmp_path / "owlclaw.yaml"
    _write_yaml(cfg_path, "agent:\n  heartbeat_interval_minutes: 20\n")
    monkeypatch.setenv("OWLCLAW_AGENT__HEARTBEAT_INTERVAL_MINUTES", "45")
    manager = ConfigManager.load(
        config_path=str(cfg_path),
        overrides={"agent": {"heartbeat_interval_minutes": 70}},
    )
    assert manager.get().agent.heartbeat_interval_minutes == 70


def test_reload_applies_only_hot_reloadable_fields(tmp_path: Path) -> None:
    ConfigManager._reset_for_tests()
    cfg_path = tmp_path / "owlclaw.yaml"
    _write_yaml(
        cfg_path,
        "agent:\n  heartbeat_interval_minutes: 30\nsecurity:\n  sanitizer:\n    enabled: true\n",
    )
    manager = ConfigManager.load(config_path=str(cfg_path))
    assert manager.get().agent.heartbeat_interval_minutes == 30
    assert manager.get().security.sanitizer.enabled is True

    _write_yaml(
        cfg_path,
        "agent:\n  heartbeat_interval_minutes: 99\nsecurity:\n  sanitizer:\n    enabled: false\n",
    )
    result = manager.reload()
    cfg = manager.get()
    assert cfg.security.sanitizer.enabled is False
    assert cfg.agent.heartbeat_interval_minutes == 99
    assert "security.sanitizer.enabled" in result.applied
    assert "agent.heartbeat_interval_minutes" in result.applied


def test_reload_notifies_listeners_for_applied_changes(tmp_path: Path) -> None:
    ConfigManager._reset_for_tests()
    cfg_path = tmp_path / "owlclaw.yaml"
    _write_yaml(cfg_path, "security:\n  sanitizer:\n    enabled: true\n")
    manager = ConfigManager.load(config_path=str(cfg_path))

    seen: list[tuple[bool, bool]] = []

    def _listener(old_cfg, new_cfg) -> None:  # type: ignore[no-untyped-def]
        seen.append((old_cfg.security.sanitizer.enabled, new_cfg.security.sanitizer.enabled))

    manager.on_change(_listener)
    _write_yaml(cfg_path, "security:\n  sanitizer:\n    enabled: false\n")
    manager.reload()
    assert seen[-1] == (True, False)
