"""Unit tests for owlclaw db restore command."""

from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path

import pytest

from owlclaw.cli.db_restore import restore_command


def test_restore_from_sql_file(monkeypatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    backup = tmp_path / "backup.sql"
    backup.write_text("select 1;", encoding="utf-8")
    monkeypatch.setenv("OWLCLAW_DATABASE_URL", "postgresql://u:p@localhost/owlclaw")
    monkeypatch.setattr("owlclaw.cli.db_restore.progress_after", lambda *_a, **_k: nullcontext())
    monkeypatch.setattr("owlclaw.cli.db_restore._check_database_empty_sync", lambda _u: True)
    monkeypatch.setattr("owlclaw.cli.db_restore._get_restore_stats_sync", lambda _u: {"table_count": 2, "total_rows": 10})

    called = {"sql": False}

    def _fake_restore_sql(conn_str: str, path: Path, clean: bool, env: dict[str, str]) -> None:
        called["sql"] = True
        assert path == backup
        assert clean is False
        assert conn_str.startswith("postgresql://")
        assert isinstance(env, dict)

    monkeypatch.setattr("owlclaw.cli.db_restore._restore_from_sql", _fake_restore_sql)
    monkeypatch.setattr("owlclaw.cli.db_restore._restore_from_custom", lambda *_a, **_k: None)

    restore_command(input_path=str(backup), clean=False, database_url="", yes=True, verbose=False)
    assert called["sql"] is True
    assert "Restore complete. Tables: 2, total rows: 10" in capsys.readouterr().out


def test_restore_from_custom_file_with_clean(monkeypatch, tmp_path: Path) -> None:
    backup = tmp_path / "backup.dump"
    backup.write_bytes(b"PGDMP123")
    monkeypatch.setenv("OWLCLAW_DATABASE_URL", "postgresql://u:p@localhost/owlclaw")
    monkeypatch.setattr("owlclaw.cli.db_restore.progress_after", lambda *_a, **_k: nullcontext())
    monkeypatch.setattr("owlclaw.cli.db_restore._check_database_empty_sync", lambda _u: True)
    monkeypatch.setattr("owlclaw.cli.db_restore._get_restore_stats_sync", lambda _u: {"table_count": 0, "total_rows": 0})

    called = {"custom": False}

    def _fake_restore_custom(conn_str: str, path: Path, clean: bool, env: dict[str, str]) -> None:
        called["custom"] = True
        assert path == backup
        assert clean is True
        assert conn_str.startswith("postgresql://")
        assert isinstance(env, dict)

    monkeypatch.setattr("owlclaw.cli.db_restore._restore_from_sql", lambda *_a, **_k: None)
    monkeypatch.setattr("owlclaw.cli.db_restore._restore_from_custom", _fake_restore_custom)

    restore_command(input_path=str(backup), clean=True, database_url="", yes=True, verbose=False)
    assert called["custom"] is True


def test_restore_warns_when_database_not_empty(monkeypatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    backup = tmp_path / "backup.sql"
    backup.write_text("select 1;", encoding="utf-8")
    monkeypatch.setenv("OWLCLAW_DATABASE_URL", "postgresql://u:p@localhost/owlclaw")
    monkeypatch.setattr("owlclaw.cli.db_restore.progress_after", lambda *_a, **_k: nullcontext())
    monkeypatch.setattr("owlclaw.cli.db_restore._check_database_empty_sync", lambda _u: False)
    monkeypatch.setattr("owlclaw.cli.db_restore._restore_from_sql", lambda *_a, **_k: None)
    monkeypatch.setattr("owlclaw.cli.db_restore._get_restore_stats_sync", lambda _u: {"table_count": 1, "total_rows": 1})

    restore_command(input_path=str(backup), clean=False, database_url="", yes=True, verbose=False)
    err = capsys.readouterr().err
    assert "not empty" in err


def test_restore_missing_file_exits_2(monkeypatch, tmp_path: Path) -> None:
    missing = tmp_path / "missing.sql"
    monkeypatch.setenv("OWLCLAW_DATABASE_URL", "postgresql://u:p@localhost/owlclaw")
    with pytest.raises(Exception) as exc_info:
        restore_command(input_path=str(missing), clean=False, database_url="", yes=True, verbose=False)
    assert getattr(exc_info.value, "exit_code", None) == 2
