"""owlclaw db status — show connection, version, extensions, table count."""

import os
from urllib.parse import urlsplit, urlunsplit

import typer
from typer.models import OptionInfo

from owlclaw.db import ConfigurationError, get_engine


def _normalize_optional_str_option(value: object) -> str | None:
    if isinstance(value, OptionInfo):
        return None
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    return value


def _mask_url(url: str) -> str:
    """Hide password in URL."""
    if "://" not in url:
        return url
    split = urlsplit(url)
    if split.username is None:
        return url
    userinfo = split.username
    if split.password is not None:
        userinfo = f"{userinfo}:***"
    host = split.hostname or ""
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    try:
        parsed_port = split.port
    except ValueError:
        return url
    port_suffix = f":{parsed_port}" if parsed_port is not None else ""
    netloc = f"{userinfo}@{host}{port_suffix}"
    return urlunsplit((split.scheme, netloc, split.path, split.query, split.fragment))


def status_command(
    database_url: str | None = typer.Option(
        None,
        "--database-url",
        help="Database URL (default: OWLCLAW_DATABASE_URL).",
    ),
) -> None:
    """Show database connection and migration status."""
    database_url = _normalize_optional_str_option(database_url)
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
