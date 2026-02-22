"""owlclaw skill init — create a new Skill from template or default scaffold."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated, Any

import click
import typer

from owlclaw.templates.skills import (
    TemplateRegistry,
    TemplateRenderer,
    TemplateValidator,
    get_default_templates_dir,
)
from owlclaw.templates.skills.models import TemplateCategory

DEFAULT_SKILL_TEMPLATE = """---
name: {name}
description: Description for {name}.
metadata: {{}}
owlclaw: {{}}
---

# Instructions

Describe when and how to use this skill.
"""


def _parse_param_args(param_args: list[str]) -> dict[str, Any]:
    """Parse --param key=value into a dict."""
    result: dict[str, Any] = {}
    for s in param_args:
        if "=" not in s:
            raise ValueError(f"Invalid --param entry (expected key=value): {s}")
        k, _, v = s.partition("=")
        key = k.strip()
        if not key:
            raise ValueError(f"Invalid --param entry (empty key): {s}")
        result[key] = v.strip()
    return result


def _load_params_file(path: Path) -> dict[str, Any]:
    """Load params from JSON or YAML file."""
    import json

    import yaml

    content = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".json",):
        return json.loads(content)
    if path.suffix.lower() in (".yaml", ".yml"):
        return yaml.safe_load(content) or {}
    raise ValueError(f"Unsupported params file format: {path.suffix}")


def _run_interactive_wizard(
    registry: TemplateRegistry,
    category: TemplateCategory | None,
    prefill_name: str | None,
) -> tuple[str, dict[str, Any]]:
    """Interactive wizard: select template, collect parameters. Returns (template_id, params)."""
    templates = registry.list_templates(category=category)
    if not templates:
        typer.echo("No templates found.", err=True)
        raise typer.Exit(1)

    # Show category/template selection
    typer.echo("\nAvailable templates:")
    for i, t in enumerate(templates, 1):
        typer.echo(f"  {i}. {t.id} — {t.name}")

    choices = [str(i) for i in range(1, len(templates) + 1)]
    sel = typer.prompt(
        f"Select template (1-{len(templates)})",
        default="1",
        type=click.Choice(choices),
    )
    meta = templates[int(sel) - 1]

    # Collect parameters
    params: dict[str, Any] = {}
    for p in meta.parameters:
        default_val: Any = p.default
        if p.name == "skill_name" and prefill_name:
            default_val = prefill_name
        if p.required or default_val is None:
            prompt_text = p.description or p.name
            if default_val is not None:
                val = typer.prompt(prompt_text, default=str(default_val))
            else:
                val = typer.prompt(prompt_text)
            params[p.name] = val
        else:
            params[p.name] = default_val

    return meta.id, params


def _normalize_skill_name(raw_name: str) -> str:
    """Normalize user input into kebab-case skill name."""
    kebab = re.sub(r"[^\w\s-]", "", str(raw_name))
    kebab = re.sub(r"[\s_]+", "-", kebab).strip("-").lower()
    return kebab


def init_command(
    name: Annotated[str, typer.Option("--name", help="Skill name. Required for default template.", is_flag=False)] = "",
    path: Annotated[str, typer.Option("--output", "--path", "-o", "-p", help="Output directory.", is_flag=False)] = ".",
    template: Annotated[
        str,
        typer.Option(
            "--template",
            help="Template ID (e.g. monitoring/health-check). Leave empty for interactive wizard. Use 'default' for legacy scaffold.",
            is_flag=False,
        ),
    ] = "",
    category: Annotated[
        str,
        typer.Option("--category", "-c", help="Filter templates by category (monitoring, analysis, workflow, integration, report).", is_flag=False),
    ] = "",
    params_file: Annotated[
        str,
        typer.Option("--params-file", help="JSON or YAML file path with template parameters (non-interactive).", is_flag=False),
    ] = "",
    param: Annotated[
        str,
        typer.Option("--param", help="Template parameters as key=value, comma-separated (e.g. skill_name=X,skill_description=Y).", is_flag=False),
    ] = "",
    force: Annotated[bool, typer.Option("--force", "-f", help="Overwrite existing SKILL.md if present.")] = False,
) -> None:
    """Create a new Skill directory and SKILL.md from template or default scaffold."""
    base = Path(path).resolve()
    if base.exists() and not base.is_dir():
        typer.echo(f"Error: output path is not a directory: {base}", err=True)
        raise typer.Exit(2)
    if not base.is_dir():
        base.mkdir(parents=True, exist_ok=True)

    validator = TemplateValidator()

    def _validate_generated_skill(skill_file: Path) -> None:
        errs = validator.validate_skill_file(skill_file)
        if errs:
            for e in errs:
                level = "Error" if e.severity == "error" else "Warning"
                typer.echo(f"{level}: {e.field}: {e.message}", err=True)
            if any(e.severity == "error" for e in errs):
                raise typer.Exit(1)

    # Legacy default template (no template library)
    use_default = template == "default"
    if use_default and name.strip():
        normalized_name = _normalize_skill_name(name.strip())
        if not normalized_name:
            typer.echo("Error: --name must contain at least one alphanumeric character.", err=True)
            raise typer.Exit(2)
        skill_dir = base / normalized_name
        skill_file = skill_dir / "SKILL.md"
        if skill_file.exists() and not force:
            typer.echo(f"Error: {skill_file} already exists. Use --force to overwrite.", err=True)
            raise typer.Exit(2)
        skill_dir.mkdir(parents=True, exist_ok=True)
        content = DEFAULT_SKILL_TEMPLATE.format(name=normalized_name)
        skill_file.write_text(content, encoding="utf-8")
        _validate_generated_skill(skill_file)
        typer.echo(f"Created: {skill_file}")
        return

    if use_default and not name.strip():
        typer.echo("Error: provide --name for default template (e.g. owlclaw skill init --name myname).", err=True)
        raise typer.Exit(2)

    # Template library mode
    templates_dir = get_default_templates_dir()
    registry = TemplateRegistry(templates_dir)
    renderer = TemplateRenderer(registry)

    cat_enum: TemplateCategory | None = None
    if category:
        try:
            cat_enum = TemplateCategory(category.strip().lower())
        except ValueError:
            typer.echo(f"Error: invalid category '{category}'. Use: monitoring, analysis, workflow, integration, report.", err=True)
            raise typer.Exit(2) from None

    params: dict[str, Any] = {}
    template_id: str
    non_interactive = bool(params_file or param.strip())

    if params_file:
        p = Path(params_file)
        if not p.exists():
            typer.echo(f"Error: params file not found: {p}", err=True)
            raise typer.Exit(2)
        try:
            loaded = _load_params_file(p)
        except Exception as e:
            typer.echo(f"Error: cannot load params file: {e}", err=True)
            raise typer.Exit(2) from e
        if not isinstance(loaded, dict):
            typer.echo("Error: params file must contain a JSON/YAML object.", err=True)
            raise typer.Exit(2)
        params = loaded
    if param.strip():
        # Parse "k1=v1,k2=v2" or "k1=v1"
        parts = [p.strip() for p in param.split(",") if p.strip()]
        try:
            params.update(_parse_param_args(parts))
        except ValueError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(2) from e
    if non_interactive and not template:
        typer.echo(
            "Error: --template is required in non-interactive mode when using --params-file or --param.",
            err=True,
        )
        raise typer.Exit(2)

    if not template:
        # Full interactive wizard
        template_id, wiz_params = _run_interactive_wizard(registry, cat_enum, name)
        params.update(wiz_params)
    else:
        meta = registry.get_template(template)
        if meta is None:
            typer.echo(f"Error: template not found: {template}", err=True)
            raise typer.Exit(2)
        template_id = template
        missing_required: list[str] = []
        # Prompt for missing required params
        for p in meta.parameters:
            if p.required and p.name not in params:
                if non_interactive:
                    missing_required.append(p.name)
                    continue
                default_val = p.default
                if p.name == "skill_name" and name.strip():
                    default_val = name
                prompt_text = p.description or p.name
                if default_val is not None:
                    val = typer.prompt(prompt_text, default=str(default_val))
                else:
                    val = typer.prompt(prompt_text)
                params[p.name] = val
            elif not p.required and p.default is not None and p.name not in params:
                params[p.name] = p.default
        if missing_required:
            typer.echo(
                "Error: missing required template parameters in non-interactive mode: "
                + ", ".join(missing_required),
                err=True,
            )
            raise typer.Exit(2)

    content = renderer.render(template_id, params)

    # Determine output path: use skill_name (kebab) as subdir
    skill_name_val = params.get("skill_name") or (name.strip() or None)
    if not skill_name_val:
        typer.echo("Error: skill_name is required.", err=True)
        raise typer.Exit(2)

    # kebab-case for directory name
    kebab = _normalize_skill_name(str(skill_name_val))
    if not kebab:
        typer.echo("Error: skill_name must contain at least one alphanumeric character.", err=True)
        raise typer.Exit(2)

    skill_dir = base / kebab
    skill_file = skill_dir / "SKILL.md"

    if skill_file.exists() and not force:
        typer.echo(f"Error: {skill_file} already exists. Use --force to overwrite.", err=True)
        raise typer.Exit(2)

    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file.write_text(content, encoding="utf-8")

    _validate_generated_skill(skill_file)
    typer.echo(f"Created: {skill_file}")
