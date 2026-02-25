"""Unit tests for owlclaw db CLI (init, migrate, status)."""

from unittest.mock import AsyncMock, patch

from typer.models import OptionInfo
from typer.testing import CliRunner

from owlclaw.cli import app
from owlclaw.cli.db_migrate import migrate_command

runner = CliRunner()


def test_db_commands_registered():
    """owlclaw db has init, migrate, status (invoke without subcommand to see usage)."""
    import os

    os.environ.pop("OWLCLAW_DATABASE_URL", None)
    os.environ.pop("DATABASE_URL", None)
    result = runner.invoke(app, ["db"])
    # Typer may show help or "Missing command"; either way db is registered
    assert result.exit_code != 0 or "db" in result.output
    # Explicit subcommands work
    result2 = runner.invoke(app, ["db", "status"])
    assert result2.exit_code == 2  # no URL
    assert "OWLCLAW_DATABASE_URL" in result2.output or "database-url" in result2.output


def test_db_status_without_url():
    """status without OWLCLAW_DATABASE_URL exits 2."""
    import os

    os.environ.pop("OWLCLAW_DATABASE_URL", None)
    os.environ.pop("DATABASE_URL", None)
    result = runner.invoke(app, ["db", "status"])
    assert result.exit_code == 2
    assert "OWLCLAW_DATABASE_URL" in result.output or "database-url" in result.output


def test_db_migrate_without_url():
    """migrate without OWLCLAW_DATABASE_URL exits 2."""
    import os

    os.environ.pop("OWLCLAW_DATABASE_URL", None)
    os.environ.pop("DATABASE_URL", None)
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


def test_db_init_honors_explicit_dry_run_argument(monkeypatch):
    from owlclaw.cli.db_init import init_command

    monkeypatch.setenv("OWLCLAW_ADMIN_URL", "postgresql://u:p@localhost/postgres")
    captured: dict[str, object] = {}

    async def _fake_init_impl(**kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)

    def _run_coro(coro):  # type: ignore[no-untyped-def]
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    monkeypatch.setattr("owlclaw.cli.db_init.asyncio.run", _run_coro)
    monkeypatch.setattr("owlclaw.cli.db_init._init_impl", _fake_init_impl)
    init_command(
        admin_url=None,
        owlclaw_password=None,
        hatchet_password=None,
        skip_hatchet=False,
        dry_run=True,
    )
    assert captured.get("dry_run") is True


def test_db_init_honors_explicit_skip_hatchet_argument(monkeypatch):
    from owlclaw.cli.db_init import init_command

    monkeypatch.setenv("OWLCLAW_ADMIN_URL", "postgresql://u:p@localhost/postgres")
    captured: dict[str, object] = {}

    async def _fake_init_impl(**kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)

    def _run_coro(coro):  # type: ignore[no-untyped-def]
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    monkeypatch.setattr("owlclaw.cli.db_init.asyncio.run", _run_coro)
    monkeypatch.setattr("owlclaw.cli.db_init._init_impl", _fake_init_impl)
    init_command(
        admin_url=None,
        owlclaw_password=None,
        hatchet_password=None,
        skip_hatchet=True,
        dry_run=True,
    )
    assert captured.get("skip_hatchet") is True


def test_db_init_handles_optioninfo_inputs(monkeypatch):
    from owlclaw.cli.db_init import init_command

    monkeypatch.setenv("OWLCLAW_ADMIN_URL", "postgresql://u:p@localhost/postgres")
    captured: dict[str, object] = {}

    async def _fake_init_impl(**kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)

    def _run_coro(coro):  # type: ignore[no-untyped-def]
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    monkeypatch.setattr("owlclaw.cli.db_init.asyncio.run", _run_coro)
    monkeypatch.setattr("owlclaw.cli.db_init._init_impl", _fake_init_impl)
    init_command(
        admin_url=OptionInfo(default=None),  # type: ignore[arg-type]
        owlclaw_password=OptionInfo(default=None),  # type: ignore[arg-type]
        hatchet_password=OptionInfo(default=None),  # type: ignore[arg-type]
        skip_hatchet=OptionInfo(default=False),  # type: ignore[arg-type]
        dry_run=OptionInfo(default=False),  # type: ignore[arg-type]
    )
    assert captured.get("admin_url") == "postgresql://u:p@localhost/postgres"


def test_db_migrate_handles_optioninfo_defaults_without_crashing(monkeypatch):
    monkeypatch.setenv("OWLCLAW_DATABASE_URL", "postgresql://u:p@localhost/owlclaw")
    with patch("owlclaw.cli.db_migrate.command.upgrade") as mock_upgrade:
        migrate_command(
            target=OptionInfo(default="head"),  # type: ignore[arg-type]
            database_url=OptionInfo(default=None),  # type: ignore[arg-type]
            dry_run=OptionInfo(default=False),  # type: ignore[arg-type]
        )
    assert mock_upgrade.call_count == 1


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
    with patch("owlclaw.cli.db_status.get_engine") as mock_get_engine, patch(
        "owlclaw.cli.db_status._collect_status_info",
        new_callable=AsyncMock,
    ) as mock_collect, patch("owlclaw.cli.db_status._print_status_table"):
        mock_collect.return_value = {
            "connection": "x",
            "server_version": "x",
            "extensions": [],
            "current_migration": "x",
            "pending_migrations": 0,
            "table_count": 0,
            "total_rows": 0,
            "disk_usage_bytes": 0,
        }
        status_command(database_url=None)
    mock_get_engine.assert_called_once_with("postgresql://u:p@localhost/owlclaw")


def test_db_status_mask_url_hides_password_and_keeps_query():
    from owlclaw.cli.db_status import _mask_url

    masked = _mask_url("postgresql://user:secret@localhost:5432/dbname?sslmode=require")
    assert "secret" not in masked
    assert "user:***@" in masked
    assert "?sslmode=require" in masked


def test_db_status_mask_url_without_password_keeps_userinfo():
    from owlclaw.cli.db_status import _mask_url

    masked = _mask_url("postgresql://user@localhost/dbname")
    assert masked == "postgresql://user@localhost/dbname"


def test_db_status_mask_url_invalid_port_returns_original():
    from owlclaw.cli.db_status import _mask_url

    original = "postgresql://user:secret@localhost:bad/dbname"
    assert _mask_url(original) == original


def test_db_init_parse_pg_url_accepts_case_insensitive_schemes():
    from owlclaw.cli.db_init import _parse_pg_url

    parsed1 = _parse_pg_url("PostgreSQL://u:p@localhost:5432/postgres")
    parsed2 = _parse_pg_url("PostgreSQL+AsyncPG://u:p@localhost:5432/postgres")
    assert parsed1["database"] == "postgres"
    assert parsed2["database"] == "postgres"


def test_db_status_handles_optioninfo_database_url(monkeypatch):
    from owlclaw.cli.db_status import status_command

    monkeypatch.setenv("OWLCLAW_DATABASE_URL", "postgresql://u:p@localhost/owlclaw")
    with patch("owlclaw.cli.db_status.get_engine") as mock_get_engine, patch(
        "owlclaw.cli.db_status._collect_status_info",
        new_callable=AsyncMock,
    ) as mock_collect, patch("owlclaw.cli.db_status._print_status_table"):
        mock_collect.return_value = {
            "connection": "x",
            "server_version": "x",
            "extensions": [],
            "current_migration": "x",
            "pending_migrations": 0,
            "table_count": 0,
            "total_rows": 0,
            "disk_usage_bytes": 0,
        }
        status_command(database_url=OptionInfo(default=None))  # type: ignore[arg-type]
    mock_get_engine.assert_called_once_with("postgresql://u:p@localhost/owlclaw")


def test_db_status_falls_back_to_sync_probe_when_async_probe_fails(monkeypatch):
    from owlclaw.cli.db_status import status_command

    monkeypatch.setenv("OWLCLAW_DATABASE_URL", "postgresql://u:p@localhost/owlclaw")
    def _raise_and_close(coro):  # type: ignore[no-untyped-def]
        coro.close()
        raise RuntimeError("WinError 64")

    with patch("owlclaw.cli.db_status.get_engine"), patch(
        "owlclaw.cli.db_status.asyncio.run",
        side_effect=_raise_and_close,
    ), patch(
        "owlclaw.cli.db_status._collect_status_info_sync"
    ) as mock_sync, patch(
        "owlclaw.cli.db_status._print_status_table"
    ) as mock_print, patch(
        "owlclaw.cli.db_status.typer.echo"
    ) as mock_echo:
        mock_sync.return_value = {
            "connection": "x",
            "server_version": "x",
            "extensions": [],
            "current_migration": "x",
            "pending_migrations": 0,
            "table_count": 0,
            "total_rows": 0,
            "disk_usage_bytes": 0,
        }
        status_command(database_url=None)
    assert mock_sync.call_count == 1
    assert mock_print.call_count == 1
    assert any(
        "falling back to sync probe" in str(call.args[0]) for call in mock_echo.call_args_list if call.args
    )


def test_db_status_to_sync_postgres_url_converts_asyncpg_scheme():
    from owlclaw.cli.db_status import _to_sync_postgres_url

    assert (
        _to_sync_postgres_url("postgresql+asyncpg://u:p@localhost:5432/owlclaw")
        == "postgresql://u:p@localhost:5432/owlclaw"
    )
    assert _to_sync_postgres_url("postgresql://u:p@localhost:5432/owlclaw") == "postgresql://u:p@localhost:5432/owlclaw"
