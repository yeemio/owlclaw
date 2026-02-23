"""Unit tests for owlclaw init config generation."""

from __future__ import annotations

from pathlib import Path

import pytest

from owlclaw.cli.init_config import init_config_command


def test_init_config_command_generates_yaml(tmp_path: Path) -> None:
    out = init_config_command(path=str(tmp_path))
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "security:" in text
    assert "agent:" in text


def test_init_config_command_refuses_overwrite_without_force(tmp_path: Path) -> None:
    target = tmp_path / "owlclaw.yaml"
    target.write_text("existing", encoding="utf-8")
    with pytest.raises(FileExistsError):
        init_config_command(path=str(tmp_path))


def test_init_config_command_overwrites_with_force(tmp_path: Path) -> None:
    target = tmp_path / "owlclaw.yaml"
    target.write_text("existing", encoding="utf-8")
    init_config_command(path=str(tmp_path), force=True)
    assert "security:" in target.read_text(encoding="utf-8")

