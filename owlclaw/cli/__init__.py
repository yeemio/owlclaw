"""CLI tools — owlclaw db, owlclaw skill, owlclaw scan, owlclaw migrate."""

import sys

import typer

from owlclaw.cli.db import db_app
from owlclaw.cli.skill import skill_app

app = typer.Typer(
    name="owlclaw",
    help="OwlClaw — Agent base for business applications.",
)
app.add_typer(db_app, name="db")
app.add_typer(skill_app, name="skill")


def _print_help_and_exit(argv: list[str]) -> None:
    """Print plain help when Typer/Rich make_metavar bug triggers (--help)."""
    argv = [a for a in argv if a not in ("--help", "-h")]
    if not argv:
        print("Usage: owlclaw [OPTIONS] COMMAND [ARGS]...")
        print("\n  OwlClaw — Agent base for business applications.\n")
        print("Commands:")
        print("  db     Database: init, migrate, status")
        print("  skill  Create, validate, list Agent Skills (SKILL.md)")
        print("\n  owlclaw db --help   owlclaw skill --help")
        sys.exit(0)
    if argv == ["db"]:
        print("Usage: owlclaw db [OPTIONS] COMMAND [ARGS]...")
        print("\n  Database operations: init, migrate, status.\n")
        print("Commands:")
        print("  init     Create owlclaw (and optionally hatchet) database, role, pgvector")
        print("  migrate  Run Alembic migrations (owlclaw schema)")
        print("  status   Show connection and migration status")
        print("\n  owlclaw db init --help | owlclaw db migrate --help | owlclaw db status --help")
        sys.exit(0)
    if argv == ["db", "init"]:
        print("Usage: owlclaw db init [OPTIONS]")
        print("\n  Create owlclaw (and optionally hatchet) database, role, and pgvector.\n")
        print("Options:")
        print("  --admin-url TEXT       PostgreSQL superuser URL (default: OWLCLAW_ADMIN_URL)")
        print("  --owlclaw-password     Password for role owlclaw (default: random)")
        print("  --hatchet-password     Password for role hatchet (default: random)")
        print("  --skip-hatchet         Do not create hatchet database/role")
        print("  --dry-run              Show what would be done without executing")
        print("  --help                 Show this message and exit")
        sys.exit(0)
    if argv == ["db", "migrate"]:
        print("Usage: owlclaw db migrate [OPTIONS] [TARGET]")
        print("\n  Run Alembic migrations. OWLCLAW_DATABASE_URL required.\n")
        print("  --dry-run  Show pending migrations only")
        sys.exit(0)
    if argv == ["db", "status"]:
        print("Usage: owlclaw db status")
        print("\n  Show database connection and migration status.")
        sys.exit(0)
    if argv == ["skill"]:
        print("Usage: owlclaw skill [OPTIONS] COMMAND [ARGS]...")
        print("\n  Create, validate, and list Agent Skills (SKILL.md). Local only.\n")
        print("Commands:")
        print("  init      Scaffold a new SKILL.md from template")
        print("  validate  Validate SKILL.md in current dir")
        print("  list      List skills in a directory")
        print("  templates List templates from the template library")
        print("\n  owlclaw skill init --help | owlclaw skill templates --help")
        sys.exit(0)
    if argv == ["skill", "init"]:
        print("Usage: owlclaw skill init [OPTIONS]")
        print("\n  Scaffold a new SKILL.md in current directory.")
        sys.exit(0)
    if argv == ["skill", "validate"]:
        print("Usage: owlclaw skill validate [OPTIONS] [DIR]")
        print("\n  Validate SKILL.md (default: current dir).")
        sys.exit(0)
    if argv == ["skill", "list"]:
        print("Usage: owlclaw skill list [OPTIONS]")
        print("\n  List Agent Skills in directory.")
        sys.exit(0)
    if argv == ["skill", "templates"]:
        print("Usage: owlclaw skill templates [OPTIONS]")
        print("\n  List templates from the template library.")
        sys.exit(0)
    # Fallback
    print("Usage: owlclaw [OPTIONS] COMMAND [ARGS]...")
    print("  db     Database: init, migrate, status")
    print("  skill  Create, validate, list Agent Skills (SKILL.md)")
    sys.exit(0)


def main() -> None:
    """CLI entry point — dispatches to subcommands."""
    if "--help" in sys.argv or "-h" in sys.argv:
        argv = [a for a in sys.argv[1:] if a not in ("--help", "-h")]
        _print_help_and_exit(argv)
    try:
        app()
    except TypeError as e:
        if "make_metavar" in str(e):
            argv = sys.argv[1:]
            _print_help_and_exit(argv)
        raise


if __name__ == "__main__":
    main()
