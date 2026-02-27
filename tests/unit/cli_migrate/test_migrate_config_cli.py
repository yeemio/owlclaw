"""Unit tests for migrate config commands."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.exceptions import Exit

from owlclaw.cli.migrate.config_cli import (
    init_migrate_config_command,
    validate_migrate_config_command,
)


def test_init_migrate_config_command_non_interactive(tmp_path: Path) -> None:
    init_migrate_config_command(
        path=str(tmp_path),
        project="./legacy",
        output="./out",
        output_mode="both",
        force=False,
        interactive=False,
    )
    config = tmp_path / ".owlclaw-migrate.yaml"
    text = config.read_text(encoding="utf-8")
    assert "project: ./legacy" in text
    assert "output_mode: both" in text


def test_validate_migrate_config_command_ok(tmp_path: Path) -> None:
    config = tmp_path / ".owlclaw-migrate.yaml"
    config.write_text(
        (
            "project: ./legacy\n"
            "output: ./out\n"
            "output_mode: handler\n"
            "include: ['**/*.py']\n"
            "exclude: ['tests/**']\n"
        ),
        encoding="utf-8",
    )
    validate_migrate_config_command(config=str(config))


def test_validate_migrate_config_command_rejects_unknown_key(tmp_path: Path) -> None:
    config = tmp_path / ".owlclaw-migrate.yaml"
    config.write_text("project: ./legacy\nunknown: 1\n", encoding="utf-8")
    with pytest.raises(Exit) as exc_info:
        validate_migrate_config_command(config=str(config))
    assert exc_info.value.exit_code == 2


def test_validate_migrate_config_command_accepts_mcp_mode(tmp_path: Path) -> None:
    config = tmp_path / ".owlclaw-migrate.yaml"
    config.write_text(
        (
            "openapi: ./openapi.yaml\n"
            "output: ./out\n"
            "output_mode: mcp\n"
        ),
        encoding="utf-8",
    )
    validate_migrate_config_command(config=str(config))
