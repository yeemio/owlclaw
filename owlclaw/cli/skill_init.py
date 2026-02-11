"""owlclaw skill init — create a new Skill directory and SKILL.md."""

from pathlib import Path

import typer

DEFAULT_SKILL_TEMPLATE = """---
name: {name}
description: Description for {name}.
metadata: {{}}
owlclaw: {{}}
---

# Instructions

Describe when and how to use this skill.
"""


def init_command(
    name: str = typer.Argument(..., help="Skill name (directory and frontmatter name)."),
    path: str = typer.Argument(
        ".",
        help="Base path where to create the skill directory.",
    ),
    template: str = typer.Option(
        "default",
        "--template",
        "-t",
        help="Template to use (MVP: only 'default').",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing SKILL.md if present.",
    ),
) -> None:
    """Create a new Skill directory and SKILL.md with default frontmatter."""
    base = Path(path).resolve()
    if not base.is_dir():
        typer.echo(f"Error: path is not a directory: {base}", err=True)
        raise typer.Exit(2)

    skill_dir = base / name
    skill_file = skill_dir / "SKILL.md"

    if skill_file.exists() and not force:
        typer.echo(f"Error: {skill_file} already exists. Use --force to overwrite.", err=True)
        raise typer.Exit(2)

    skill_dir.mkdir(parents=True, exist_ok=True)
    content = DEFAULT_SKILL_TEMPLATE.format(name=name)
    skill_file.write_text(content, encoding="utf-8")
    typer.echo(f"Created: {skill_file}")
