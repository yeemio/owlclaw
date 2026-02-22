"""CLI tools — owlclaw db, owlclaw skill, owlclaw scan, owlclaw migrate."""

import argparse
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


def _dispatch_skill_command(argv: list[str]) -> bool:
    """Dispatch `owlclaw skill ...` using argparse for Typer option-parse compatibility."""
    if not argv or argv[0] != "skill":
        return False

    if len(argv) < 2:
        return False

    sub = argv[1]
    sub_argv = argv[2:]

    if sub == "init":
        from owlclaw.cli.skill_init import init_command

        parser = argparse.ArgumentParser(add_help=False, prog="owlclaw skill init")
        parser.add_argument("--name", default="")
        parser.add_argument("--output", "--path", "-o", "-p", dest="path", default=".")
        parser.add_argument("--template", default="")
        parser.add_argument("--category", "-c", default="")
        parser.add_argument("--params-file", dest="params_file", default="")
        parser.add_argument("--param", default="")
        parser.add_argument("--force", "-f", action="store_true", default=False)
        ns = parser.parse_args(sub_argv)
        init_command(
            name=ns.name,
            path=ns.path,
            template=ns.template,
            category=ns.category,
            params_file=ns.params_file,
            param=ns.param,
            force=ns.force,
        )
        return True

    if sub == "validate":
        from owlclaw.cli.skill_validate import validate_command

        parser = argparse.ArgumentParser(add_help=False, prog="owlclaw skill validate")
        parser.add_argument("paths", nargs="*", default=["."])
        parser.add_argument("--verbose", "-v", action="store_true", default=False)
        parser.add_argument("--strict", "-s", action="store_true", default=False)
        ns = parser.parse_args(sub_argv)
        validate_command(paths=ns.paths, verbose=ns.verbose, strict=ns.strict)
        return True

    if sub == "list":
        from owlclaw.cli.skill_list import list_command

        parser = argparse.ArgumentParser(add_help=False, prog="owlclaw skill list")
        parser.add_argument("--path", "-p", default=".")
        ns = parser.parse_args(sub_argv)
        list_command(path=ns.path)
        return True

    if sub == "templates":
        from owlclaw.cli.skill_list import templates_command

        parser = argparse.ArgumentParser(add_help=False, prog="owlclaw skill templates")
        parser.add_argument("--category", "-c", default="")
        parser.add_argument("--tags", default="")
        parser.add_argument("--search", "-s", default="")
        parser.add_argument("--show", default="")
        parser.add_argument("--verbose", "-v", action="store_true", default=False)
        parser.add_argument("--json", dest="json_output", action="store_true", default=False)
        ns = parser.parse_args(sub_argv)
        templates_command(
            category=ns.category,
            tags=ns.tags,
            search=ns.search,
            show=ns.show,
            verbose=ns.verbose,
            json_output=ns.json_output,
        )
        return True

    return False


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
    if _dispatch_skill_command(sys.argv[1:]):
        return
    try:
        app()
    except TypeError as e:
        if "make_metavar" in str(e):
            argv = sys.argv[1:]
            _print_help_and_exit(argv)
        raise


if __name__ == "__main__":
    main()
