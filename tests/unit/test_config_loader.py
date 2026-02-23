"""Unit tests for YAMLConfigLoader."""

from __future__ import annotations

from pathlib import Path

import pytest

from owlclaw.config.loader import ConfigLoadError, YAMLConfigLoader


def test_resolve_path_uses_env_first(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OWLCLAW_CONFIG", "/tmp/from-env.yaml")
    resolved = YAMLConfigLoader.resolve_path("/tmp/from-cli.yaml")
    assert str(resolved).endswith("from-env.yaml")


def test_resolve_path_uses_cli_when_env_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OWLCLAW_CONFIG", raising=False)
    resolved = YAMLConfigLoader.resolve_path("/tmp/from-cli.yaml")
    assert str(resolved).endswith("from-cli.yaml")


def test_load_dict_missing_file_returns_empty(tmp_path: Path) -> None:
    target = tmp_path / "missing.yaml"
    assert YAMLConfigLoader.load_dict(target) == {}


def test_load_dict_empty_file_returns_empty(tmp_path: Path) -> None:
    target = tmp_path / "owlclaw.yaml"
    target.write_text("", encoding="utf-8")
    assert YAMLConfigLoader.load_dict(target) == {}


def test_load_dict_returns_mapping(tmp_path: Path) -> None:
    target = tmp_path / "owlclaw.yaml"
    target.write_text("agent:\n  heartbeat_interval_minutes: 45\n", encoding="utf-8")
    loaded = YAMLConfigLoader.load_dict(target)
    assert loaded["agent"]["heartbeat_interval_minutes"] == 45


def test_load_dict_yaml_error_has_line_column(tmp_path: Path) -> None:
    target = tmp_path / "owlclaw.yaml"
    target.write_text("agent:\n  heartbeat_interval_minutes: [\n", encoding="utf-8")
    with pytest.raises(ConfigLoadError) as exc_info:
        YAMLConfigLoader.load_dict(target)
    message = str(exc_info.value)
    assert "owlclaw.yaml" in message
    assert ":" in message


def test_load_dict_non_mapping_root_raises(tmp_path: Path) -> None:
    target = tmp_path / "owlclaw.yaml"
    target.write_text("- invalid\n- root\n", encoding="utf-8")
    with pytest.raises(ConfigLoadError, match="root must be mapping"):
        YAMLConfigLoader.load_dict(target)
