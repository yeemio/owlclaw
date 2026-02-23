"""Unit tests for owlclaw db CLI (init, migrate, status)."""

from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from owlclaw.cli import app
from owlclaw.cli.db_migrate import migrate_command

runner = CliRunner()


def test_db_commands_registered():
    """owlclaw db has init, migrate, status (invoke without subcommand to see usage)."""
    result = runner.invoke(app, ["db"])
    # Typer may show help or "Missing command"; either way db is registered
    assert result.exit_code != 0 or "db" in result.output
    # Explicit subcommands work
    result2 = runner.invoke(app, ["db", "status"])
    assert result2.exit_code == 2  # no URL
    assert "OWLCLAW_DATABASE_URL" in result2.output or "database-url" in result2.output


def test_db_status_without_url():
    """status without OWLCLAW_DATABASE_URL exits 2."""
    result = runner.invoke(app, ["db", "status"])
    assert result.exit_code == 2
    assert "OWLCLAW_DATABASE_URL" in result.output or "database-url" in result.output


def test_db_migrate_without_url():
    """migrate without OWLCLAW_DATABASE_URL exits 2."""
    result = runner.invoke(app, ["db", "migrate"])
    assert result.exit_code == 2
    assert "OWLCLAW_DATABASE_URL" in result.output or "database-url" in result.output


def test_db_init_with_env_url(monkeypatch):
    """init runs with OWLCLAW_ADMIN_URL and receives URL (mock impl to avoid DB)."""
    monkeypatch.setenv("OWLCLAW_ADMIN_URL", "postgresql://u:p@localhost/postgres")
    with patch("owlclaw.cli.db_init._init_impl", new_callable=AsyncMock) as mock_impl:
        mock_impl.return_value = None
        result = runner.invoke(app, ["db", "init", "--dry-run"])
    assert result.exit_code == 0, (result.output or str(result.exception))
    mock_impl.assert_called_once()
    assert mock_impl.call_args[1]["admin_url"] == "postgresql://u:p@localhost/postgres"


def test_db_migrate_rejects_blank_target(monkeypatch):
    """migrate with blank --target should fail fast."""
    monkeypatch.setenv("OWLCLAW_DATABASE_URL", "postgresql://u:p@localhost/owlclaw")
    result = runner.invoke(app, ["db", "migrate", "--target", "   "])
    assert result.exit_code == 2


def test_db_migrate_trims_database_url_before_use(monkeypatch):
    monkeypatch.setenv("OWLCLAW_DATABASE_URL", "  postgresql://u:p@localhost/owlclaw  ")
    with patch("owlclaw.cli.db_migrate.command.current") as mock_current, patch(
        "owlclaw.cli.db_migrate.command.heads"
    ) as mock_heads:
        migrate_command(target="head", database_url=None, dry_run=True)
    assert mock_current.call_count == 1
    assert mock_heads.call_count == 1


def test_db_status_trims_database_url_before_engine_check(monkeypatch):
    from owlclaw.cli.db_status import status_command

    monkeypatch.setenv("OWLCLAW_DATABASE_URL", "  postgresql://u:p@localhost/owlclaw  ")
    with patch("owlclaw.cli.db_status.get_engine") as mock_get_engine:
        status_command(database_url=None)
    mock_get_engine.assert_called_once_with("postgresql://u:p@localhost/owlclaw")
