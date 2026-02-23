"""Unit tests for owlclaw db backup command."""

from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest

from owlclaw.cli.db_backup import _build_pg_dump_args, backup_command


def test_backup_command_success(monkeypatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    output = tmp_path / "backup.sql"
    monkeypatch.setenv("OWLCLAW_DATABASE_URL", "postgresql://u:p@localhost/owlclaw")
    monkeypatch.setattr("owlclaw.cli.db_backup._check_pg_dump_available", lambda: True)
    monkeypatch.setattr("owlclaw.cli.db_backup.progress_after", lambda *_a, **_k: nullcontext())

    def _fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        output_path = Path(args[args.index("-f") + 1])
        output_path.write_text("-- dump", encoding="utf-8")
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr("owlclaw.cli.db_backup.subprocess.run", _fake_run)

    backup_command(output=str(output), format_name="plain", schema_only=False, data_only=False, database_url="")
    out = capsys.readouterr().out
    assert "Backup written:" in out
    assert "Size:" in out


def test_build_pg_dump_args_custom_format_and_schema_only() -> None:
    args = _build_pg_dump_args(
        "postgresql://u:p@localhost/owlclaw",
        Path("out.dump"),
        "custom",
        schema_only=True,
        data_only=False,
    )
    assert "-F" in args and "c" in args
    assert "--schema-only" in args
    assert "--data-only" not in args


def test_backup_command_existing_file_abort(monkeypatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    output = tmp_path / "exists.sql"
    output.write_text("old", encoding="utf-8")
    monkeypatch.setenv("OWLCLAW_DATABASE_URL", "postgresql://u:p@localhost/owlclaw")
    monkeypatch.setattr("owlclaw.cli.db_backup._check_pg_dump_available", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _p: "n")
    called = {"run": False}

    def _fake_run(*_a, **_k):  # type: ignore[no-untyped-def]
        called["run"] = True
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr("owlclaw.cli.db_backup.subprocess.run", _fake_run)
    backup_command(output=str(output), format_name="plain", schema_only=False, data_only=False, database_url="")
    assert called["run"] is False
    assert "Aborted." in capsys.readouterr().out


def test_backup_command_pg_dump_unavailable_exits_2(monkeypatch, tmp_path: Path) -> None:
    output = tmp_path / "backup.sql"
    monkeypatch.setenv("OWLCLAW_DATABASE_URL", "postgresql://u:p@localhost/owlclaw")
    monkeypatch.setattr("owlclaw.cli.db_backup._check_pg_dump_available", lambda: False)
    with pytest.raises(Exception) as exc_info:
        backup_command(output=str(output), format_name="plain", schema_only=False, data_only=False, database_url="")
    assert getattr(exc_info.value, "exit_code", None) == 2
