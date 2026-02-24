"""owlclaw skill hub commands: search/install/installed."""

from __future__ import annotations

from pathlib import Path

import typer

from owlclaw.owlhub import OwlHubClient


def _create_client(index_url: str, install_dir: str, lock_file: str) -> OwlHubClient:
    return OwlHubClient(
        index_url=index_url,
        install_dir=Path(install_dir).resolve(),
        lock_file=Path(lock_file).resolve(),
    )


def search_command(
    query: str = typer.Option("", "--query", "-q", help="Search query.", is_flag=False),
    index_url: str = typer.Option("./index.json", "--index-url", help="Path/URL to index.json.", is_flag=False),
    tags: str = typer.Option("", "--tags", help="Comma-separated tags filter.", is_flag=False),
    tag_mode: str = typer.Option("and", "--tag-mode", help="Tag filter mode: and/or.", is_flag=False),
    install_dir: str = typer.Option(
        "./.owlhub/skills", "--install-dir", help="Install directory for skills.", is_flag=False
    ),
    lock_file: str = typer.Option("./skill-lock.json", "--lock-file", help="Lock file path.", is_flag=False),
) -> None:
    """Search skills in OwlHub index."""
    client = _create_client(index_url=index_url, install_dir=install_dir, lock_file=lock_file)
    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else []
    results = client.search(query=query, tags=tag_list, tag_mode=tag_mode)
    if not results:
        typer.echo("No skills found.")
        return
    for item in results:
        rendered_tags = ",".join(item.tags) if item.tags else "-"
        typer.echo(f"{item.name}@{item.version} ({item.publisher}) [{rendered_tags}] - {item.description}")


def install_command(
    name: str = typer.Argument(..., help="Skill name to install."),
    version: str = typer.Option("", "--version", help="Exact version to install.", is_flag=False),
    index_url: str = typer.Option("./index.json", "--index-url", help="Path/URL to index.json.", is_flag=False),
    install_dir: str = typer.Option(
        "./.owlhub/skills", "--install-dir", help="Install directory for skills.", is_flag=False
    ),
    lock_file: str = typer.Option("./skill-lock.json", "--lock-file", help="Lock file path.", is_flag=False),
) -> None:
    """Install one skill from OwlHub index."""
    client = _create_client(index_url=index_url, install_dir=install_dir, lock_file=lock_file)
    try:
        installed_path = client.install(name=name, version=version or None)
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"Installed: {name} -> {installed_path}")


def installed_command(
    index_url: str = typer.Option("./index.json", "--index-url", help="Path/URL to index.json.", is_flag=False),
    install_dir: str = typer.Option(
        "./.owlhub/skills", "--install-dir", help="Install directory for skills.", is_flag=False
    ),
    lock_file: str = typer.Option("./skill-lock.json", "--lock-file", help="Lock file path.", is_flag=False),
) -> None:
    """List installed skills from lock file."""
    client = _create_client(index_url=index_url, install_dir=install_dir, lock_file=lock_file)
    installed = client.list_installed()
    if not installed:
        typer.echo("No installed skills.")
        return
    for item in installed:
        typer.echo(f"{item.get('name')}@{item.get('version')} ({item.get('publisher')})")


def update_command(
    name: str = typer.Argument("", help="Optional skill name to update."),
    index_url: str = typer.Option("./index.json", "--index-url", help="Path/URL to index.json.", is_flag=False),
    install_dir: str = typer.Option(
        "./.owlhub/skills", "--install-dir", help="Install directory for skills.", is_flag=False
    ),
    lock_file: str = typer.Option("./skill-lock.json", "--lock-file", help="Lock file path.", is_flag=False),
) -> None:
    """Update one skill or all installed skills."""
    client = _create_client(index_url=index_url, install_dir=install_dir, lock_file=lock_file)
    changes = client.update(name=name or None)
    if not changes:
        typer.echo("No updates available.")
        return
    for change in changes:
        typer.echo(f"Updated: {change['name']} {change['from_version']} -> {change['to_version']}")
