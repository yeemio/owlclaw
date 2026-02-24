"""owlclaw skill hub commands: search/install/installed."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import typer

from owlclaw.cli.api_client import SkillHubApiClient
from owlclaw.owlhub import OwlHubClient

logger = logging.getLogger(__name__)


def _create_index_client(index_url: str, install_dir: str, lock_file: str, *, no_cache: bool = False) -> OwlHubClient:
    return OwlHubClient(
        index_url=index_url,
        install_dir=Path(install_dir).resolve(),
        lock_file=Path(lock_file).resolve(),
        no_cache=no_cache,
    )


def search_command(
    query: str = typer.Option("", "--query", "-q", help="Search query.", is_flag=False),
    index_url: str = typer.Option("./index.json", "--index-url", help="Path/URL to index.json.", is_flag=False),
    tags: str = typer.Option("", "--tags", help="Comma-separated tags filter.", is_flag=False),
    tag_mode: str = typer.Option("and", "--tag-mode", help="Tag filter mode: and/or.", is_flag=False),
    include_draft: bool = typer.Option(False, "--include-draft", help="Include draft versions in results."),
    mode: str = typer.Option("auto", "--mode", help="Hub mode: auto/index/api.", is_flag=False),
    api_base_url: str = typer.Option("", "--api-base-url", help="OwlHub API base URL.", is_flag=False),
    api_token: str = typer.Option("", "--api-token", help="OwlHub API token.", is_flag=False),
    no_cache: bool = typer.Option(False, "--no-cache", help="Bypass local cache."),
    install_dir: str = typer.Option(
        "./.owlhub/skills", "--install-dir", help="Install directory for skills.", is_flag=False
    ),
    lock_file: str = typer.Option("./skill-lock.json", "--lock-file", help="Lock file path.", is_flag=False),
) -> None:
    """Search skills in OwlHub index."""
    index_client = _create_index_client(index_url=index_url, install_dir=install_dir, lock_file=lock_file, no_cache=no_cache)
    client = SkillHubApiClient(
        index_client=index_client,
        api_base_url=api_base_url,
        api_token=api_token,
        mode=mode,
        no_cache=no_cache,
    )
    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else []
    results = client.search(query=query, tags=tag_list, tag_mode=tag_mode, include_draft=include_draft)
    if not results:
        typer.echo("No skills found.")
        return
    for item in results:
        rendered_tags = ",".join(item.tags) if item.tags else "-"
        typer.echo(f"{item.name}@{item.version} [{item.version_state}] ({item.publisher}) [{rendered_tags}] - {item.description}")


def install_command(
    name: str = typer.Argument(..., help="Skill name to install."),
    version: str = typer.Option("", "--version", help="Exact version to install.", is_flag=False),
    no_deps: bool = typer.Option(False, "--no-deps", help="Skip dependency installation."),
    force: bool = typer.Option(False, "--force", help="Force install on checksum/moderation errors."),
    mode: str = typer.Option("auto", "--mode", help="Hub mode: auto/index/api.", is_flag=False),
    api_base_url: str = typer.Option("", "--api-base-url", help="OwlHub API base URL.", is_flag=False),
    api_token: str = typer.Option("", "--api-token", help="OwlHub API token.", is_flag=False),
    no_cache: bool = typer.Option(False, "--no-cache", help="Bypass local cache."),
    index_url: str = typer.Option("./index.json", "--index-url", help="Path/URL to index.json.", is_flag=False),
    install_dir: str = typer.Option(
        "./.owlhub/skills", "--install-dir", help="Install directory for skills.", is_flag=False
    ),
    lock_file: str = typer.Option("./skill-lock.json", "--lock-file", help="Lock file path.", is_flag=False),
) -> None:
    """Install one skill from OwlHub index."""
    index_client = _create_index_client(index_url=index_url, install_dir=install_dir, lock_file=lock_file, no_cache=no_cache)
    client = SkillHubApiClient(
        index_client=index_client,
        api_base_url=api_base_url,
        api_token=api_token,
        mode=mode,
        no_cache=no_cache,
    )
    if not no_deps:
        candidates = index_client.search(query=name, include_draft=True)
        selected = [item for item in candidates if item.name == name and (not version or item.version == version)]
        if selected:
            dependencies = selected[-1].dependencies
            if dependencies:
                typer.echo("Dependencies:")
                for dep_name, constraint in sorted(dependencies.items()):
                    typer.echo(f"  - {dep_name} ({constraint})")
    try:
        installed_path = client.install(name=name, version=version or None, no_deps=no_deps, force=force)
    except Exception as exc:
        logger.exception(
            "Skill install failed: %s",
            json.dumps({"event": "skill_install_error", "name": name, "version": version or "latest"}, ensure_ascii=False),
        )
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc
    logger.info(
        "%s",
        json.dumps(
            {
                "event": "skill_install",
                "name": name,
                "version": version or "latest",
                "path": str(installed_path),
                "mode": mode,
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
    )
    if client.last_install_warning:
        typer.echo(f"Warning: {client.last_install_warning}")
    typer.echo(f"Installed: {name} -> {installed_path}")


def installed_command(
    mode: str = typer.Option("auto", "--mode", help="Hub mode: auto/index/api.", is_flag=False),
    api_base_url: str = typer.Option("", "--api-base-url", help="OwlHub API base URL.", is_flag=False),
    api_token: str = typer.Option("", "--api-token", help="OwlHub API token.", is_flag=False),
    no_cache: bool = typer.Option(False, "--no-cache", help="Bypass local cache."),
    index_url: str = typer.Option("./index.json", "--index-url", help="Path/URL to index.json.", is_flag=False),
    install_dir: str = typer.Option(
        "./.owlhub/skills", "--install-dir", help="Install directory for skills.", is_flag=False
    ),
    lock_file: str = typer.Option("./skill-lock.json", "--lock-file", help="Lock file path.", is_flag=False),
) -> None:
    """List installed skills from lock file."""
    client = SkillHubApiClient(
        index_client=_create_index_client(index_url=index_url, install_dir=install_dir, lock_file=lock_file, no_cache=no_cache),
        api_base_url=api_base_url,
        api_token=api_token,
        mode=mode,
        no_cache=no_cache,
    )
    installed = client.list_installed()
    if not installed:
        typer.echo("No installed skills.")
        return
    for item in installed:
        state = item.get("version_state", "released")
        typer.echo(f"{item.get('name')}@{item.get('version')} [{state}] ({item.get('publisher')})")


def update_command(
    name: str = typer.Argument("", help="Optional skill name to update."),
    mode: str = typer.Option("auto", "--mode", help="Hub mode: auto/index/api.", is_flag=False),
    api_base_url: str = typer.Option("", "--api-base-url", help="OwlHub API base URL.", is_flag=False),
    api_token: str = typer.Option("", "--api-token", help="OwlHub API token.", is_flag=False),
    no_cache: bool = typer.Option(False, "--no-cache", help="Bypass local cache."),
    index_url: str = typer.Option("./index.json", "--index-url", help="Path/URL to index.json.", is_flag=False),
    install_dir: str = typer.Option(
        "./.owlhub/skills", "--install-dir", help="Install directory for skills.", is_flag=False
    ),
    lock_file: str = typer.Option("./skill-lock.json", "--lock-file", help="Lock file path.", is_flag=False),
) -> None:
    """Update one skill or all installed skills."""
    client = SkillHubApiClient(
        index_client=_create_index_client(index_url=index_url, install_dir=install_dir, lock_file=lock_file, no_cache=no_cache),
        api_base_url=api_base_url,
        api_token=api_token,
        mode=mode,
        no_cache=no_cache,
    )
    changes = client.update(name=name or None)
    if not changes:
        typer.echo("No updates available.")
        return
    for change in changes:
        typer.echo(f"Updated: {change['name']} {change['from_version']} -> {change['to_version']}")


def publish_command(
    path: str = typer.Argument(".", help="Skill package directory path."),
    mode: str = typer.Option("api", "--mode", help="Hub mode: auto/index/api.", is_flag=False),
    api_base_url: str = typer.Option("", "--api-base-url", help="OwlHub API base URL.", is_flag=False),
    api_token: str = typer.Option("", "--api-token", help="OwlHub API token.", is_flag=False),
    no_cache: bool = typer.Option(False, "--no-cache", help="Bypass local cache."),
    index_url: str = typer.Option("./index.json", "--index-url", help="Path/URL to index.json.", is_flag=False),
    install_dir: str = typer.Option(
        "./.owlhub/skills", "--install-dir", help="Install directory for skills.", is_flag=False
    ),
    lock_file: str = typer.Option("./skill-lock.json", "--lock-file", help="Lock file path.", is_flag=False),
) -> None:
    """Publish one local skill to OwlHub API."""
    client = SkillHubApiClient(
        index_client=_create_index_client(index_url=index_url, install_dir=install_dir, lock_file=lock_file, no_cache=no_cache),
        api_base_url=api_base_url,
        api_token=api_token,
        mode=mode,
        no_cache=no_cache,
    )
    try:
        result = client.publish(skill_path=Path(path).resolve())
    except Exception as exc:
        logger.exception(
            "Skill publish failed: %s",
            json.dumps({"event": "skill_publish_error", "path": str(Path(path).resolve()), "mode": mode}, ensure_ascii=False),
        )
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc
    logger.info(
        "%s",
        json.dumps(
            {
                "event": "skill_publish",
                "path": str(Path(path).resolve()),
                "mode": mode,
                "review_id": result.get("review_id", ""),
                "status": result.get("status", ""),
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
    )
    typer.echo(f"Published: review_id={result.get('review_id', '')} status={result.get('status', '')}")


def cache_clear_command(
    index_url: str = typer.Option("./index.json", "--index-url", help="Path/URL to index.json.", is_flag=False),
    install_dir: str = typer.Option(
        "./.owlhub/skills", "--install-dir", help="Install directory for skills.", is_flag=False
    ),
    lock_file: str = typer.Option("./skill-lock.json", "--lock-file", help="Lock file path.", is_flag=False),
) -> None:
    """Clear local OwlHub cache files."""
    client = _create_index_client(index_url=index_url, install_dir=install_dir, lock_file=lock_file, no_cache=False)
    removed = client.clear_cache()
    typer.echo(f"Cache cleared: {removed} files")
