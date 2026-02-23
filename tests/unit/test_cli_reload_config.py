"""Unit tests for owlclaw reload config command."""

from __future__ import annotations

from pathlib import Path

from owlclaw.cli.reload_config import reload_config_command
from owlclaw.config.manager import ConfigManager


def test_reload_config_command_returns_applied_and_skipped(tmp_path: Path) -> None:
    ConfigManager._reset_for_tests()
    cfg = tmp_path / "owlclaw.yaml"
    cfg.write_text(
        "agent:\n  heartbeat_interval_minutes: 30\nsecurity:\n  sanitizer:\n    enabled: true\n",
        encoding="utf-8",
    )
    manager = ConfigManager.load(config_path=str(cfg))
    assert manager.get().security.sanitizer.enabled is True

    cfg.write_text(
        "agent:\n  heartbeat_interval_minutes: 90\nsecurity:\n  sanitizer:\n    enabled: false\n",
        encoding="utf-8",
    )
    applied, skipped = reload_config_command(config=str(cfg))
    assert "security.sanitizer.enabled" in applied
    assert "agent.heartbeat_interval_minutes" in applied
    assert skipped == {}
