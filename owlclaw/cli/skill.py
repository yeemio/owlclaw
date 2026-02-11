"""owlclaw skill — init, validate, list (local Skills CLI)."""

import typer

from owlclaw.cli.skill_init import init_command
from owlclaw.cli.skill_list import list_command
from owlclaw.cli.skill_validate import validate_command

skill_app = typer.Typer(
    name="skill",
    help="Create, validate, and list Agent Skills (SKILL.md). Local only.",
)

skill_app.command("init")(init_command)
skill_app.command("validate")(validate_command)
skill_app.command("list")(list_command)
