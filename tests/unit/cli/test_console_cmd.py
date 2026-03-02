from __future__ import annotations

from pathlib import Path

from owlclaw.cli.console import console_command


def test_console_command_returns_url_without_static(tmp_path: Path, monkeypatch) -> None:
    fake_cli_file = tmp_path / "owlclaw" / "cli" / "console.py"
    fake_cli_file.parent.mkdir(parents=True)
    fake_cli_file.write_text("", encoding="utf-8")

    monkeypatch.setattr("owlclaw.cli.console.Path", lambda *_args, **_kwargs: fake_cli_file)
    url = console_command(port=9000, open_browser=False)
    assert url == "http://localhost:9000/console/"

