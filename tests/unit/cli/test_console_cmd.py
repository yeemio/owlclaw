"""Unit tests for `owlclaw console` command."""

from __future__ import annotations

import importlib


def test_console_command_dispatches_with_port(monkeypatch) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    captured: dict[str, object] = {}

    def _fake_console_command(**kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)
        return "http://localhost:9000/console/"

    monkeypatch.setattr("owlclaw.cli.console.console_command", _fake_console_command)
    monkeypatch.setattr("sys.argv", ["owlclaw", "console", "--port", "9000"])
    cli_main.main()
    assert captured["port"] == 9000


def test_console_help_uses_plain_help(monkeypatch, capsys) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    monkeypatch.setattr("sys.argv", ["owlclaw", "console", "--help"])
    try:
        cli_main.main()
    except SystemExit as exc:
        assert exc.code == 0
    out = capsys.readouterr().out
    assert "Usage: owlclaw console [OPTIONS]" in out

