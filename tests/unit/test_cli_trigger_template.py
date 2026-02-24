"""Unit tests for trigger template CLI dispatch."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest


def test_trigger_template_db_change_generation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    monkeypatch.setattr(
        "sys.argv",
        [
            "owlclaw",
            "trigger",
            "template",
            "db-change",
            "--output",
            str(tmp_path),
            "--channel",
            "order_updates",
            "--table",
            "orders",
        ],
    )
    cli_main.main()
    out = capsys.readouterr().out
    assert "Generated:" in out
    target = tmp_path / "notify_trigger_order_updates.sql"
    assert target.exists()
    content = target.read_text(encoding="utf-8")
    assert "pg_notify('order_updates'" in content
    assert "ON orders" in content


def test_trigger_template_db_change_help(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    monkeypatch.setattr("sys.argv", ["owlclaw", "trigger", "template", "db-change", "--help"])
    with pytest.raises(SystemExit) as exc_info:
        cli_main.main()
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "Usage: owlclaw trigger template db-change [OPTIONS]" in out
