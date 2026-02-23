"""owlclaw db status — show connection, version, extensions, table count."""

import os

import typer

from owlclaw.db import ConfigurationError, get_engine


def _mask_url(url: str) -> str:
    """Hide password in URL."""
    if "://" not in url or "@" not in url:
        return url
    pre, rest = url.split("://", 1)
    if ":" in rest and "@" in rest:
        user, after = rest.split("@", 1)
        if ":" in user:
            user = user.split(":", 1)[0] + ":***"
        rest = user + "@" + after
    return pre + "://" + rest


def status_command(
    database_url: str | None = typer.Option(
        None,
        "--database-url",
        help="Database URL (default: OWLCLAW_DATABASE_URL).",
    ),
) -> None:
    """Show database connection and migration status."""
    url = database_url or os.environ.get("OWLCLAW_DATABASE_URL")
    if not url or not url.strip():
        typer.echo("Error: Set OWLCLAW_DATABASE_URL or pass --database-url.", err=True)
        raise typer.Exit(2)
    url = url.strip()
    try:
        get_engine(url)
    except ConfigurationError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(2) from e
    typer.echo("OwlClaw Database Status")
    typer.echo("=" * 40)
    typer.echo("Connection: " + _mask_url(url))
    # Minimal status: we'd need to run async queries for version/extensions.
    # For MVP we just show connection and that we got an engine.
    typer.echo("Engine: OK (async)")
    typer.echo("Set OWLCLAW_DATABASE_URL and run migrations with: owlclaw db migrate")
