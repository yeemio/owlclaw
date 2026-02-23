"""Unit tests for owlclaw db rollback command helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from owlclaw.cli.db_rollback import rollback_command


class _FakeEngine:
    def __init__(self) -> None:
        self.sync_engine = SimpleNamespace(dispose=lambda: None)


class _FakeRevision:
    def __init__(self, revision: str, doc: str = "") -> None:
        self.revision = revision
        self.doc = doc


class _FakeScript:
    def __init__(self, revisions):  # type: ignore[no-untyped-def]
        self._revisions = revisions

    def iterate_revisions(self, upper, lower):  # type: ignore[no-untyped-def]
        if isinstance(self._revisions, Exception):
            raise self._revisions
        return self._revisions


def test_rollback_returns_when_already_at_target(monkeypatch, capsys) -> None:
    monkeypatch.setenv("OWLCLAW_DATABASE_URL", "postgresql://u:p@localhost/owlclaw")
    monkeypatch.setattr("owlclaw.cli.db_rollback.get_engine", lambda url: _FakeEngine())
    monkeypatch.setattr("owlclaw.cli.db_rollback._get_current_revision_sync", lambda engine: "abc123")
    monkeypatch.setattr(
        "owlclaw.cli.db_rollback.ScriptDirectory.from_config",
        lambda cfg: _FakeScript([]),
    )

    rollback_command(target="abc123", steps=0, database_url="", dry_run=True, yes=True)
    assert "Already at target revision." in capsys.readouterr().out


def test_rollback_invalid_target_exits_2(monkeypatch) -> None:
    monkeypatch.setenv("OWLCLAW_DATABASE_URL", "postgresql://u:p@localhost/owlclaw")
    monkeypatch.setattr("owlclaw.cli.db_rollback.get_engine", lambda url: _FakeEngine())
    monkeypatch.setattr("owlclaw.cli.db_rollback._get_current_revision_sync", lambda engine: "abc123")
    monkeypatch.setattr(
        "owlclaw.cli.db_rollback.ScriptDirectory.from_config",
        lambda cfg: _FakeScript(RuntimeError("unknown revision")),
    )

    with pytest.raises(Exception) as exc_info:
        rollback_command(target="bad-rev", steps=0, database_url="", dry_run=True, yes=True)
    assert getattr(exc_info.value, "exit_code", None) == 2


def test_rollback_target_not_behind_current_exits_2(monkeypatch) -> None:
    monkeypatch.setenv("OWLCLAW_DATABASE_URL", "postgresql://u:p@localhost/owlclaw")
    monkeypatch.setattr("owlclaw.cli.db_rollback.get_engine", lambda url: _FakeEngine())
    monkeypatch.setattr("owlclaw.cli.db_rollback._get_current_revision_sync", lambda engine: "abc123")
    monkeypatch.setattr(
        "owlclaw.cli.db_rollback.ScriptDirectory.from_config",
        lambda cfg: _FakeScript([]),
    )

    with pytest.raises(Exception) as exc_info:
        rollback_command(target="older-or-unrelated", steps=0, database_url="", dry_run=True, yes=True)
    assert getattr(exc_info.value, "exit_code", None) == 2
