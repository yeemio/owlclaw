"""owlclaw skill validate — check SKILL.md files for compliance."""

import os
import re
import shutil
from pathlib import Path
from typing import Any

import typer
import yaml  # type: ignore[import-untyped]

from owlclaw.capabilities.bindings import CredentialResolver, validate_binding_config
from owlclaw.templates.skills import TemplateValidator
from owlclaw.templates.skills.models import ValidationError

ENV_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


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


def _load_frontmatter(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8").lstrip("\ufeff")
    except OSError:
        return {}
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    raw = parts[1].strip()
    try:
        loaded = yaml.safe_load(raw)
    except yaml.YAMLError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
    return out


def _extract_tools_schema(frontmatter: dict[str, Any]) -> dict[str, Any]:
    metadata = frontmatter.get("metadata")
    if isinstance(metadata, dict):
        nested = metadata.get("tools_schema")
        if isinstance(nested, dict):
            return nested
    top_level = frontmatter.get("tools_schema")
    if isinstance(top_level, dict):
        return top_level
    return {}


def _extract_prerequisites(frontmatter: dict[str, Any]) -> dict[str, Any]:
    owlclaw = frontmatter.get("owlclaw")
    if isinstance(owlclaw, dict):
        nested = owlclaw.get("prerequisites")
        if isinstance(nested, dict):
            return nested
    top_level = frontmatter.get("prerequisites")
    if isinstance(top_level, dict):
        return top_level
    return {}


def _iter_string_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        out: list[str] = []
        for item in value.values():
            out.extend(_iter_string_values(item))
        return out
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            out.extend(_iter_string_values(item))
        return out
    return []


def _collect_env_refs(value: Any) -> set[str]:
    refs: set[str] = set()
    for text in _iter_string_values(value):
        refs.update(ENV_VAR_PATTERN.findall(text))
    return refs


def _validate_binding_semantics(path: Path) -> list[ValidationError]:
    frontmatter = _load_frontmatter(path)
    if not frontmatter:
        return []

    tools_schema = _extract_tools_schema(frontmatter)
    prerequisites = _extract_prerequisites(frontmatter)
    prerequisite_env = set(_as_str_list(prerequisites.get("env")))
    prerequisite_bins = _as_str_list(prerequisites.get("bins"))

    errors: list[ValidationError] = []
    for name, tool_def in tools_schema.items():
        if not isinstance(name, str):
            continue
        if not isinstance(tool_def, dict):
            errors.append(ValidationError(field=f"metadata.tools_schema.{name}", message="tool definition must be object", severity="error"))
            continue

        binding = tool_def.get("binding")
        if binding is None:
            continue
        if not isinstance(binding, dict):
            errors.append(ValidationError(field=f"metadata.tools_schema.{name}.binding", message="binding must be object", severity="error"))
            continue
        try:
            validate_binding_config(binding)
        except ValueError as exc:
            errors.append(
                ValidationError(
                    field=f"metadata.tools_schema.{name}.binding",
                    message=str(exc),
                    severity="error",
                )
            )

        for text in _iter_string_values(binding):
            if CredentialResolver.contains_potential_secret(text) and not ENV_VAR_PATTERN.search(text):
                errors.append(
                    ValidationError(
                        field=f"metadata.tools_schema.{name}.binding",
                        message="binding may contain plaintext secret; use ${ENV_VAR} reference",
                        severity="warning",
                    )
                )
                break

        used_env_refs = _collect_env_refs(binding)
        missing_in_prereq = sorted(ref for ref in used_env_refs if ref not in prerequisite_env)
        if missing_in_prereq:
            errors.append(
                ValidationError(
                    field=f"metadata.tools_schema.{name}.binding",
                    message=f"env refs not declared in prerequisites.env: {', '.join(missing_in_prereq)}",
                    severity="error",
                )
            )

    for env_name in sorted(prerequisite_env):
        if env_name not in os.environ:
            errors.append(
                ValidationError(
                    field="owlclaw.prerequisites.env",
                    message=f"missing environment variable: {env_name}",
                    severity="warning",
                )
            )
    for bin_name in sorted(set(prerequisite_bins)):
        if shutil.which(bin_name) is None:
            errors.append(
                ValidationError(
                    field="owlclaw.prerequisites.bins",
                    message=f"binary not found in PATH: {bin_name}",
                    severity="warning",
                )
            )
    return errors


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
        errs.extend(_validate_binding_semantics(file_path))
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
