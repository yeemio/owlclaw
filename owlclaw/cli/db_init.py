"""owlclaw db init — create database, role, and pgvector extension."""

import asyncio
import os
import secrets
from urllib.parse import urlparse

import typer

try:
    import asyncpg
except ImportError:
    asyncpg = None


def _parse_pg_url(url: str) -> dict:
    """Parse postgresql:// or postgresql+asyncpg:// URL into connection kwargs."""
    u = url.strip()
    if u.startswith("postgresql+asyncpg://"):
        u = "postgresql://" + u[len("postgresql+asyncpg://"):]
    elif not u.startswith("postgresql://"):
        return {}
    parsed = urlparse(u)
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "user": parsed.username or "postgres",
        "password": parsed.password or "",
        "database": (parsed.path or "/").lstrip("/") or "postgres",
    }


async def _init_impl(
    admin_url: str,
    owlclaw_password: str | None,
    hatchet_password: str | None,
    skip_hatchet: bool,
    dry_run: bool,
) -> None:
    if asyncpg is None:
        typer.echo("Error: asyncpg is required for db init. Install with: pip install asyncpg", err=True)
        raise typer.Exit(1)
    params = _parse_pg_url(admin_url)
    if not params:
        typer.echo("Error: admin-url must be postgresql://user:pass@host:port/postgres", err=True)
        raise typer.Exit(2)
    if params["database"] != "postgres":
        typer.echo("Warning: admin-url should connect to database 'postgres'. Using it anyway.", err=True)
    if dry_run:
        typer.echo("--dry-run: would create role owlclaw, database owlclaw, extension vector")
        if not skip_hatchet:
            typer.echo("Would create role hatchet, database hatchet")
        if not owlclaw_password:
            typer.echo("Would generate random owlclaw password")
        return
    pw_owl = owlclaw_password or secrets.token_urlsafe(16)
    pw_hatchet = hatchet_password or secrets.token_urlsafe(16)
    conn = await asyncpg.connect(
        host=params["host"],
        port=params["port"],
        user=params["user"],
        password=params["password"],
        database=params["database"],
    )
    try:
        await conn.execute("CREATE ROLE owlclaw WITH LOGIN PASSWORD $1", pw_owl)
        typer.echo("Created role owlclaw")
    except asyncpg.DuplicateObjectError:
        typer.echo("Role owlclaw already exists")
    try:
        await conn.execute("CREATE DATABASE owlclaw OWNER owlclaw")
        typer.echo("Created database owlclaw")
    except asyncpg.DuplicateObjectError:
        typer.echo("Database owlclaw already exists")
    await conn.close()
    conn_owl = await asyncpg.connect(
        host=params["host"],
        port=params["port"],
        user="owlclaw",
        password=pw_owl,
        database="owlclaw",
    )
    try:
        await conn_owl.execute("CREATE EXTENSION IF NOT EXISTS vector")
        typer.echo("Enabled extension vector in database owlclaw")
    finally:
        await conn_owl.close()
    if not skip_hatchet:
        conn2 = await asyncpg.connect(
            host=params["host"],
            port=params["port"],
            user=params["user"],
            password=params["password"],
            database=params["database"],
        )
        try:
            try:
                await conn2.execute("CREATE ROLE hatchet WITH LOGIN PASSWORD $1", pw_hatchet)
                typer.echo("Created role hatchet")
            except asyncpg.DuplicateObjectError:
                typer.echo("Role hatchet already exists")
            try:
                await conn2.execute("CREATE DATABASE hatchet OWNER hatchet")
                typer.echo("Created database hatchet")
            except asyncpg.DuplicateObjectError:
                typer.echo("Database hatchet already exists")
        finally:
            await conn2.close()
    if not owlclaw_password:
        typer.echo("OwlClaw password (save it): " + pw_owl)


def init_command(
    admin_url: str | None = typer.Option(
        None,
        "--admin-url",
        help="PostgreSQL superuser URL (default: OWLCLAW_ADMIN_URL).",
    ),
    owlclaw_password: str | None = typer.Option(
        None,
        "--owlclaw-password",
        help="Password for role owlclaw (default: random).",
    ),
    hatchet_password: str | None = typer.Option(
        None,
        "--hatchet-password",
        help="Password for role hatchet (default: random).",
    ),
    skip_hatchet: bool = typer.Option(
        False,
        "--skip-hatchet",
        help="Do not create hatchet database/role.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        is_flag=True,
        help="Show what would be done without executing.",
    ),
) -> None:
    """Create owlclaw (and optionally hatchet) database, role, and pgvector."""
    url = admin_url or os.environ.get("OWLCLAW_ADMIN_URL")
    if not url or not url.strip():
        typer.echo("Error: Set --admin-url or OWLCLAW_ADMIN_URL.", err=True)
        raise typer.Exit(2)
    asyncio.run(
        _init_impl(
            admin_url=url,
            owlclaw_password=owlclaw_password,
            hatchet_password=hatchet_password,
            skip_hatchet=skip_hatchet,
            dry_run=dry_run,
        )
    )
