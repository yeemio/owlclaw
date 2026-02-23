"""Integration-like workflow tests for cli-db command chains with mocked boundaries."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from owlclaw.cli import (
    _dispatch_db_backup,
    _dispatch_db_restore,
    _dispatch_db_revision,
    _dispatch_db_rollback,
    app,
)
from owlclaw.cli.db_migrate import migrate_command
from owlclaw.cli.db_status import status_command

runner = CliRunner()


def test_workflow_init_migrate_status_with_mocks(monkeypatch) -> None:
    monkeypatch.setenv("OWLCLAW_ADMIN_URL", "postgresql://u:p@localhost/postgres")
    monkeypatch.setenv("OWLCLAW_DATABASE_URL", "postgresql://u:p@localhost/owlclaw")

    with patch("owlclaw.cli.db_init._init_impl", new_callable=AsyncMock) as init_impl, patch(
        "owlclaw.cli.db_migrate.command.upgrade"
    ) as upgrade, patch("owlclaw.cli.db_status.get_engine") as get_engine, patch(
        "owlclaw.cli.db_status._collect_status_info",
        new_callable=AsyncMock,
    ) as collect, patch("owlclaw.cli.db_status._print_status_table"):
        collect.return_value = {
            "connection": "postgresql://u:***@localhost/owlclaw",
            "server_version": "PostgreSQL 16",
            "extensions": [],
            "current_migration": "head",
            "pending_migrations": 0,
            "table_count": 0,
            "total_rows": 0,
            "disk_usage_bytes": 0,
        }
        get_engine.return_value = object()
        init_result = runner.invoke(app, ["db", "init", "--dry-run"])
        migrate_command(target="head", database_url="", dry_run=False)
        status_command(database_url="")

    assert init_result.exit_code == 0
    assert init_impl.call_count == 1
    assert upgrade.call_count == 1


def test_workflow_backup_restore_dispatch(monkeypatch, tmp_path) -> None:
    backup_file = tmp_path / "backup.sql"
    backup_file.write_text("select 1;", encoding="utf-8")

    called = {"backup": 0, "restore": 0}
    monkeypatch.setattr("owlclaw.cli.db_backup.backup_command", lambda **_k: called.__setitem__("backup", called["backup"] + 1))
    monkeypatch.setattr("owlclaw.cli.db_restore.restore_command", lambda **_k: called.__setitem__("restore", called["restore"] + 1))

    assert _dispatch_db_backup(["db", "backup", "--output", str(tmp_path / "x.sql"), "--database-url", "postgresql://u:p@localhost/owlclaw"])
    assert _dispatch_db_restore(["db", "restore", "--input", str(backup_file), "--database-url", "postgresql://u:p@localhost/owlclaw", "--yes"])
    assert called["backup"] == 1
    assert called["restore"] == 1


def test_workflow_revision_migrate_rollback_with_mocks(monkeypatch) -> None:
    monkeypatch.setenv("OWLCLAW_DATABASE_URL", "postgresql://u:p@localhost/owlclaw")

    with patch("owlclaw.cli.db_revision.command.revision") as revision, patch(
        "owlclaw.cli.db_migrate.command.upgrade"
    ) as upgrade, patch("owlclaw.cli.db_rollback.get_engine") as get_engine, patch(
        "owlclaw.cli.db_rollback._get_current_revision_sync",
        return_value="abc123",
    ), patch("owlclaw.cli.db_rollback.ScriptDirectory.from_config") as script_from_cfg, patch(
        "owlclaw.cli.db_rollback.command.downgrade"
    ) as downgrade:
        revision.return_value = None
        get_engine.return_value = type(
            "_E",
            (),
            {"sync_engine": type("_S", (), {"dispose": staticmethod(lambda: None)})()},
        )()
        script_from_cfg.return_value = type("_Script", (), {"iterate_revisions": staticmethod(lambda *_a, **_k: [])})()

        revision_result = _dispatch_db_revision(["db", "revision", "--message", "x"])
        migrate_command(target="head", database_url="", dry_run=False)
        rollback_result = _dispatch_db_rollback(["db", "rollback", "--target", "abc123", "--dry-run", "--yes"])

    assert revision_result is True
    assert rollback_result is True
    assert revision.call_count == 1
    assert upgrade.call_count == 1
    assert downgrade.call_count == 0
