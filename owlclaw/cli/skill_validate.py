"""owlclaw skill validate — check SKILL.md files for compliance."""

from pathlib import Path

import typer

from owlclaw.capabilities.skills import SkillsLoader


def _collect_skill_files(paths: list[Path]) -> list[Path]:
    """Resolve paths to a list of SKILL.md files (recursing into directories)."""
    files: list[Path] = []
    for p in paths:
        resolved = p.resolve()
        if not resolved.exists():
            continue
        if resolved.is_file():
            if resolved.name == "SKILL.md":
                files.append(resolved)
            else:
                files.append(resolved)
        else:
            files.extend(sorted(resolved.rglob("SKILL.md")))
    return files


def validate_command(
    paths: list[str] = typer.Argument(  # noqa: B008
        default=["."],
        help="Paths to SKILL.md files or directories containing them.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed error information.",
    ),
) -> None:
    """Validate SKILL.md files (frontmatter, name, description)."""
    if not paths:
        paths = ["."]
    skill_files = _collect_skill_files([Path(p) for p in paths])
    if not skill_files:
        typer.echo("No SKILL.md files found.", err=True)
        raise typer.Exit(1)

    loader = SkillsLoader(Path("."))
    failed: list[tuple[Path, str]] = []
    for file_path in skill_files:
        skill = loader._parse_skill_file(file_path)
        if skill is None:
            failed.append((file_path, "Invalid frontmatter or missing required fields (name, description)."))
        else:
            typer.echo(f"OK: {file_path}")

    if failed:
        for file_path, msg in failed:
            typer.echo(f"FAIL: {file_path} — {msg}", err=True)
        raise typer.Exit(1)
