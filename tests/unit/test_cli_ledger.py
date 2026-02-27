"""Unit tests for ledger CLI dispatch."""

from __future__ import annotations

import importlib

import pytest


def test_main_dispatches_ledger_query(monkeypatch) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    captured: dict[str, object] = {}

    def _fake_query_command(**kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)

    monkeypatch.setattr("owlclaw.cli.ledger.query_command", _fake_query_command)
    monkeypatch.setattr(
        "sys.argv",
        [
            "owlclaw",
            "ledger",
            "query",
            "--tenant",
            "mionyee",
            "--caller-prefix",
            "mionyee.ai.",
            "--status",
            "blocked",
            "--limit",
            "5",
            "--order",
            "asc",
        ],
    )
    cli_main.main()

    assert captured["tenant"] == "mionyee"
    assert captured["caller_prefix"] == "mionyee.ai."
    assert captured["status"] == "blocked"
    assert captured["limit"] == 5
    assert captured["order_desc"] is False


def test_main_ledger_help_uses_plain_help(monkeypatch, capsys) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    monkeypatch.setattr("sys.argv", ["owlclaw", "ledger", "--help"])
    with pytest.raises(SystemExit) as exc_info:
        cli_main.main()
    assert exc_info.value.code == 0
    assert "Usage: owlclaw ledger [OPTIONS] COMMAND [ARGS]..." in capsys.readouterr().out


def test_main_ledger_query_help_uses_plain_help(monkeypatch, capsys) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    monkeypatch.setattr("sys.argv", ["owlclaw", "ledger", "query", "--help"])
    with pytest.raises(SystemExit) as exc_info:
        cli_main.main()
    assert exc_info.value.code == 0
    assert "Usage: owlclaw ledger query [OPTIONS]" in capsys.readouterr().out


def test_main_ledger_unknown_subcommand_exits_2(monkeypatch, capsys) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    monkeypatch.setattr("sys.argv", ["owlclaw", "ledger", "x"])
    with pytest.raises(SystemExit) as exc_info:
        cli_main.main()
    assert exc_info.value.code == 2
    assert "unknown ledger subcommand" in capsys.readouterr().err.lower()
