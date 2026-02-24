"""Unit tests for owlclaw agent signal CLI dispatch."""

from __future__ import annotations

import importlib

import pytest


def test_main_dispatches_agent_pause(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")

    monkeypatch.setattr(
        "owlclaw.cli.agent_signal.pause_command",
        lambda **kwargs: {"status": "paused", "kwargs": kwargs},
    )
    monkeypatch.setattr(
        "sys.argv",
        ["owlclaw", "agent", "pause", "--agent", "a1", "--tenant", "t1", "--operator", "op"],
    )
    cli_main.main()
    out = capsys.readouterr().out
    assert "paused" in out


def test_main_dispatches_agent_pause_with_agent_id_alias(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")

    monkeypatch.setattr(
        "owlclaw.cli.agent_signal.pause_command",
        lambda **kwargs: {"status": "paused", "kwargs": kwargs},
    )
    monkeypatch.setattr(
        "sys.argv",
        ["owlclaw", "agent", "pause", "--agent-id", "a1", "--tenant", "t1", "--operator", "op"],
    )
    cli_main.main()
    out = capsys.readouterr().out
    assert "paused" in out


def test_main_agent_status_help_uses_plain_help(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    monkeypatch.setattr("sys.argv", ["owlclaw", "agent", "status", "--help"])
    with pytest.raises(SystemExit) as exc_info:
        cli_main.main()
    assert exc_info.value.code == 0
    assert "Usage: owlclaw agent status --agent-id <id> [OPTIONS]" in capsys.readouterr().out


def test_main_agent_unknown_subcommand_exits_2(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    monkeypatch.setattr("sys.argv", ["owlclaw", "agent", "unknown-sub"])
    with pytest.raises(SystemExit) as exc_info:
        cli_main.main()
    assert exc_info.value.code == 2
    assert "unknown agent subcommand" in capsys.readouterr().err.lower()
