"""CLI tools — owlclaw db, owlclaw skill, owlclaw scan, owlclaw migrate."""

import typer

from owlclaw.cli.db import db_app
from owlclaw.cli.skill import skill_app

app = typer.Typer(
    name="owlclaw",
    help="OwlClaw — Agent base for business applications.",
)
app.add_typer(db_app, name="db")
app.add_typer(skill_app, name="skill")


def main() -> None:
    """CLI entry point — dispatches to subcommands."""
    try:
        app()
    except TypeError as e:
        if "make_metavar" in str(e):
            # Work around Typer/Rich help bug when root aggregates subcommand params
            import sys
            if "--help" in sys.argv or "-h" in sys.argv:
                print("Usage: owlclaw [OPTIONS] COMMAND [ARGS]...")
                print("  db     Database: init, migrate, status")
                print("  skill  Create, validate, list Agent Skills (SKILL.md)")
                print("  Use: owlclaw db --help | owlclaw skill --help")
                sys.exit(0)
        raise


if __name__ == "__main__":
    main()
