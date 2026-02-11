"""owlclaw skill list — list discovered Skills in a directory."""

from pathlib import Path

import typer

from owlclaw.capabilities.skills import SkillsLoader


def list_command(
    path: str = typer.Option(
        ".",
        "--path",
        "-p",
        help="Directory to scan for SKILL.md files.",
    ),
) -> None:
    """List Skills (name and description) found under the given path."""
    base = Path(path).resolve()
    if not base.is_dir():
        typer.echo(f"Error: path is not a directory: {base}", err=True)
        raise typer.Exit(2)

    loader = SkillsLoader(base)
    skills = loader.scan()
    if not skills:
        typer.echo("No skills found.")
        return

    max_desc_len = 60
    for s in skills:
        desc = (s.description[: max_desc_len] + "…") if len(s.description) > max_desc_len else s.description
        typer.echo(f"  {s.name}: {desc}")
