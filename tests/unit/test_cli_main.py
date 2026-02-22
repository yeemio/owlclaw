"""Unit tests for owlclaw CLI main entrypoint dispatch behavior."""

from __future__ import annotations

import contextlib
import importlib

from click.exceptions import Exit


def test_main_dispatches_skill_templates_with_option_value(monkeypatch) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")

    captured: dict[str, object] = {}

    def _fake_templates_command(**kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)

    monkeypatch.setattr("owlclaw.cli.skill_list.templates_command", _fake_templates_command)
    monkeypatch.setattr("sys.argv", ["owlclaw", "skill", "templates", "--category", "MONITORING"])
    cli_main.main()

    assert captured["category"] == "MONITORING"
    assert captured["search"] == ""
    assert captured["json_output"] is False


def test_main_dispatches_skill_init_with_template_value(monkeypatch, tmp_path) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")

    captured: dict[str, object] = {}

    def _fake_init_command(**kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)
        raise Exit(0)

    monkeypatch.setattr("owlclaw.cli.skill_init.init_command", _fake_init_command)
    monkeypatch.setattr(
        "sys.argv",
        [
            "owlclaw",
            "skill",
            "init",
            "--template",
            "monitoring/health-check",
            "--output",
            str(tmp_path),
        ],
    )
    with contextlib.suppress(Exit):
        cli_main.main()

    assert captured["template"] == "monitoring/health-check"
    assert captured["path"] == str(tmp_path)
