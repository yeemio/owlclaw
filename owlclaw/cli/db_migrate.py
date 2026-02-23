"""owlclaw db migrate — run Alembic upgrade."""

import os

import typer
from alembic import command
from alembic.config import Config


def migrate_command(
    target: str = typer.Option(
        "head",
        "--target",
        "-t",
        help="Revision to upgrade to (default: head).",
    ),
    database_url: str | None = typer.Option(
        None,
        "--database-url",
        help="Database URL (default: OWLCLAW_DATABASE_URL).",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show pending migrations without applying.",
    ),
) -> None:
    """Run schema migrations (Alembic upgrade)."""
    normalized_target = target.strip()
    if not normalized_target:
        typer.echo("Error: --target must be a non-empty revision string.", err=True)
        raise typer.Exit(2)
    url = database_url or os.environ.get("OWLCLAW_DATABASE_URL")
    if not url or not url.strip():
        typer.echo("Error: Set OWLCLAW_DATABASE_URL or pass --database-url.", err=True)
        raise typer.Exit(2)
    if database_url:
        os.environ["OWLCLAW_DATABASE_URL"] = url
    alembic_cfg = Config("alembic.ini")
    if dry_run:
        command.current(alembic_cfg)
        command.heads(alembic_cfg)
        typer.echo("--dry-run: run without --dry-run to apply migrations.")
        return
    command.upgrade(alembic_cfg, normalized_target)
    typer.echo("Migrations applied.")
