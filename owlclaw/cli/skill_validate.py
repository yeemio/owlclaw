"""owlclaw skill validate — check SKILL.md files for compliance."""

from pathlib import Path

import typer

from owlclaw.templates.skills import TemplateValidator


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
        help="Show detailed error information (field, message, severity).",
    ),
    strict: bool = typer.Option(
        False,
        "--strict",
        "-s",
        help="Treat warnings as failures (exit 1 if any warnings).",
    ),
) -> None:
    """Validate SKILL.md files (frontmatter, name, description, body)."""
    if not paths:
        paths = ["."]
    resolved_paths = [Path(p).resolve() for p in paths]
    missing_paths = [p for p in resolved_paths if not p.exists()]
    if missing_paths:
        for p in missing_paths:
            typer.echo(f"Error: path not found: {p}", err=True)
        raise typer.Exit(2)

    skill_files = _collect_skill_files(resolved_paths)
    if not skill_files:
        typer.echo("No SKILL.md files found.", err=True)
        raise typer.Exit(1)

    validator = TemplateValidator()
    failed: list[tuple[Path, list]] = []
    passed = 0

    for file_path in skill_files:
        errs = validator.validate_skill_file(file_path)
        has_error = any(e.severity == "error" for e in errs)
        has_warning = any(e.severity == "warning" for e in errs)
        fails = has_error or (strict and has_warning)

        if fails:
            failed.append((file_path, errs))
        else:
            passed += 1
            typer.echo(f"OK: {file_path}")

    if failed:
        for file_path, errs in failed:
            typer.echo(f"FAIL: {file_path}", err=True)
            for e in errs:
                if e.severity == "error" or (strict and e.severity == "warning"):
                    typer.echo(f"  [{e.severity}] {e.field}: {e.message}", err=True)
                elif verbose:
                    typer.echo(f"  [warning] {e.field}: {e.message}", err=True)

    typer.echo(f"\nValidated {len(skill_files)} file(s): {passed} passed, {len(failed)} failed.")
    if failed:
        raise typer.Exit(1)
