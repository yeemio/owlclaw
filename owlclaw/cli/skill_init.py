"""owlclaw skill init — create a new Skill from template or default scaffold."""

from __future__ import annotations

from pathlib import Path
from typing import Any

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
        if "=" in s:
            k, _, v = s.partition("=")
            result[k.strip()] = v.strip()
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


def init_command(
    name: str = typer.Option(
        "",
        "--name",
        help="Skill name. Required for default template.",
    ),
    path: str = typer.Option(
        ".",
        "--output",
        "--path",
        "-o",
        "-p",
        help="Output directory.",
    ),
    template: str = typer.Option(
        "",
        "--template",
        help="Template ID (e.g. monitoring/health-check). Leave empty for interactive wizard. Use 'default' for legacy scaffold.",
    ),
    category: str = typer.Option(
        "",
        "--category",
        "-c",
        help="Filter templates by category (monitoring, analysis, workflow, integration, report).",
    ),
    params_file: str = typer.Option(
        "",
        "--params-file",
        help="JSON or YAML file path with template parameters (non-interactive).",
    ),
    param: str = typer.Option(
        "",
        "--param",
        help="Template parameters as key=value, comma-separated (e.g. skill_name=X,skill_description=Y).",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing SKILL.md if present.",
    ),
) -> None:
    """Create a new Skill directory and SKILL.md from template or default scaffold."""
    base = Path(path).resolve()
    if not base.is_dir():
        base.mkdir(parents=True, exist_ok=True)

    # Legacy default template (no template library)
    use_default = template == "default"
    if use_default and name.strip():
        skill_dir = base / name.strip()
        skill_file = skill_dir / "SKILL.md"
        if skill_file.exists() and not force:
            typer.echo(f"Error: {skill_file} already exists. Use --force to overwrite.", err=True)
            raise typer.Exit(2)
        skill_dir.mkdir(parents=True, exist_ok=True)
        content = DEFAULT_SKILL_TEMPLATE.format(name=name.strip())
        skill_file.write_text(content, encoding="utf-8")
        typer.echo(f"Created: {skill_file}")
        return

    if use_default and not name.strip():
        typer.echo("Error: provide --name for default template (e.g. owlclaw skill init --name myname).", err=True)
        raise typer.Exit(2)

    # Template library mode
    templates_dir = get_default_templates_dir()
    registry = TemplateRegistry(templates_dir)
    renderer = TemplateRenderer(registry)
    validator = TemplateValidator()

    cat_enum: TemplateCategory | None = None
    if category:
        try:
            cat_enum = TemplateCategory(category)
        except ValueError:
            typer.echo(f"Error: invalid category '{category}'. Use: monitoring, analysis, workflow, integration, report.", err=True)
            raise typer.Exit(2)

    params: dict[str, Any] = {}
    template_id: str

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
        parts = [p.strip() for p in param.split(",") if "=" in p]
        params.update(_parse_param_args(parts))

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
        # Prompt for missing required params
        for p in meta.parameters:
            if p.required and p.name not in params:
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

    content = renderer.render(template_id, params)

    # Determine output path: use skill_name (kebab) as subdir
    skill_name_val = params.get("skill_name") or (name.strip() or None)
    if not skill_name_val:
        typer.echo("Error: skill_name is required.", err=True)
        raise typer.Exit(2)

    # kebab-case for directory name
    import re

    kebab = re.sub(r"[^\w\s-]", "", str(skill_name_val))
    kebab = re.sub(r"[\s_]+", "-", kebab).strip("-").lower()

    skill_dir = base / kebab
    skill_file = skill_dir / "SKILL.md"

    if skill_file.exists() and not force:
        typer.echo(f"Error: {skill_file} already exists. Use --force to overwrite.", err=True)
        raise typer.Exit(2)

    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file.write_text(content, encoding="utf-8")

    # Validate generated file
    errs = validator.validate_skill_file(skill_file)
    if errs:
        for e in errs:
            typer.echo(f"Warning: {e.field}: {e.message}", err=True)
    else:
        typer.echo(f"Created: {skill_file}")
