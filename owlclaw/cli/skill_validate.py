"""owlclaw skill validate — check SKILL.md files for compliance."""

from pathlib import Path

import typer

from owlclaw.templates.skills import TemplateValidator


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off", ""}:
            return False
    return False


def _collect_skill_files(paths: list[Path]) -> list[Path]:
    """Resolve paths to a list of SKILL.md files (recursing into directories)."""
    files: list[Path] = []
    seen: set[Path] = set()
    for p in paths:
        resolved = p.resolve()
        if not resolved.exists():
            continue
        if resolved.is_file() and resolved.name == "SKILL.md":
            if resolved not in seen:
                seen.add(resolved)
                files.append(resolved)
        else:
            for file_path in sorted(resolved.rglob("SKILL.md")):
                if file_path not in seen:
                    seen.add(file_path)
                    files.append(file_path)
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
        is_flag=True,
    ),
    strict: bool = typer.Option(
        False,
        "--strict",
        "-s",
        help="Treat warnings as failures (exit 1 if any warnings).",
        is_flag=True,
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
    invalid_files = [p for p in resolved_paths if p.is_file() and p.name != "SKILL.md"]
    if invalid_files:
        for p in invalid_files:
            typer.echo(f"Error: file is not SKILL.md: {p}", err=True)
        raise typer.Exit(2)

    skill_files = _collect_skill_files(resolved_paths)
    if not skill_files:
        typer.echo("No SKILL.md files found.", err=True)
        raise typer.Exit(1)

    validator = TemplateValidator()
    failed: list[tuple[Path, list]] = []
    passed = 0
    strict_mode = _as_bool(strict)
    verbose_mode = _as_bool(verbose)

    for file_path in skill_files:
        errs = validator.validate_skill_file(file_path)
        has_error = any(e.severity == "error" for e in errs)
        has_warning = any(e.severity == "warning" for e in errs)
        fails = has_error or (strict_mode and has_warning)

        if fails:
            failed.append((file_path, errs))
        else:
            passed += 1
            typer.echo(f"OK: {file_path}")
            for e in errs:
                if e.severity == "warning":
                    typer.echo(f"  [warning] {e.field}: {e.message}")

    if failed:
        for file_path, errs in failed:
            typer.echo(f"FAIL: {file_path}", err=True)
            for e in errs:
                if e.severity == "error" or (strict_mode and e.severity == "warning"):
                    typer.echo(f"  [{e.severity}] {e.field}: {e.message}", err=True)
                elif verbose_mode:
                    typer.echo(f"  [warning] {e.field}: {e.message}", err=True)

    typer.echo(f"\nValidated {len(skill_files)} file(s): {passed} passed, {len(failed)} failed.")
    if failed:
        raise typer.Exit(1)
