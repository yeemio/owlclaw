"""CLI tools — owlclaw db, owlclaw skill, owlclaw scan, owlclaw migrate."""

import argparse
import sys

import typer
from click.exceptions import Exit as ClickExit

from owlclaw.cli.db import db_app
from owlclaw.cli.memory import memory_app
from owlclaw.cli.skill import skill_app

app = typer.Typer(
    name="owlclaw",
    help="OwlClaw — Agent base for business applications.",
)
app.add_typer(db_app, name="db")
app.add_typer(memory_app, name="memory")
app.add_typer(skill_app, name="skill")


def _dispatch_skill_command(argv: list[str]) -> bool:
    """Dispatch `owlclaw skill ...` using argparse for Typer option-parse compatibility."""
    if not argv or argv[0] != "skill":
        return False

    if len(argv) < 2:
        _print_help_and_exit(["skill"])

    sub = argv[1]
    sub_argv = argv[2:]
    if "--help" in sub_argv or "-h" in sub_argv:
        _print_help_and_exit(["skill", sub])

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

    print(f"Error: unknown skill subcommand: {sub}", file=sys.stderr)
    raise SystemExit(2)


def _dispatch_memory_command(argv: list[str]) -> bool:
    """Dispatch `owlclaw memory ...` using argparse for Typer option-parse compatibility."""
    if not argv or argv[0] != "memory":
        return False

    if len(argv) < 2:
        _print_help_and_exit(["memory"])

    sub = argv[1]
    sub_argv = argv[2:]
    if "--help" in sub_argv or "-h" in sub_argv:
        _print_help_and_exit(["memory", sub])

    if sub == "list":
        from owlclaw.cli.memory import list_command

        parser = argparse.ArgumentParser(add_help=False, prog="owlclaw memory list")
        parser.add_argument("--agent", required=True)
        parser.add_argument("--tenant", default="default")
        parser.add_argument("--tags", default="")
        parser.add_argument("--page", type=int, default=1)
        parser.add_argument("--page-size", type=int, default=20)
        parser.add_argument("--include-archived", action="store_true", default=False)
        parser.add_argument("--backend", default="pgvector")
        ns = parser.parse_args(sub_argv)
        list_command(
            agent=ns.agent,
            tenant=ns.tenant,
            tags=ns.tags,
            page=ns.page,
            page_size=ns.page_size,
            include_archived=ns.include_archived,
            backend=ns.backend,
        )
        return True

    if sub == "prune":
        from owlclaw.cli.memory import prune_command

        parser = argparse.ArgumentParser(add_help=False, prog="owlclaw memory prune")
        parser.add_argument("--agent", required=True)
        parser.add_argument("--tenant", default="default")
        parser.add_argument("--before", default="")
        parser.add_argument("--tags", default="")
        parser.add_argument("--backend", default="pgvector")
        ns = parser.parse_args(sub_argv)
        prune_command(
            agent=ns.agent,
            tenant=ns.tenant,
            before=ns.before,
            tags=ns.tags,
            backend=ns.backend,
        )
        return True

    if sub == "reset":
        from owlclaw.cli.memory import reset_command

        parser = argparse.ArgumentParser(add_help=False, prog="owlclaw memory reset")
        parser.add_argument("--agent", required=True)
        parser.add_argument("--tenant", default="default")
        parser.add_argument("--confirm", action="store_true", default=False)
        parser.add_argument("--backend", default="pgvector")
        ns = parser.parse_args(sub_argv)
        reset_command(
            agent=ns.agent,
            tenant=ns.tenant,
            confirm=ns.confirm,
            backend=ns.backend,
        )
        return True

    if sub == "stats":
        from owlclaw.cli.memory import stats_command

        parser = argparse.ArgumentParser(add_help=False, prog="owlclaw memory stats")
        parser.add_argument("--agent", required=True)
        parser.add_argument("--tenant", default="default")
        parser.add_argument("--backend", default="pgvector")
        ns = parser.parse_args(sub_argv)
        stats_command(
            agent=ns.agent,
            tenant=ns.tenant,
            backend=ns.backend,
        )
        return True

    if sub == "migrate-backend":
        from owlclaw.cli.memory import migrate_backend_command

        parser = argparse.ArgumentParser(add_help=False, prog="owlclaw memory migrate-backend")
        parser.add_argument("--agent", required=True)
        parser.add_argument("--tenant", default="default")
        parser.add_argument("--source-backend", required=True)
        parser.add_argument("--target-backend", required=True)
        parser.add_argument("--batch-size", type=int, default=200)
        parser.add_argument("--include-archived", dest="include_archived", action="store_true", default=True)
        parser.add_argument("--exclude-archived", dest="include_archived", action="store_false")
        ns = parser.parse_args(sub_argv)
        migrate_backend_command(
            agent=ns.agent,
            tenant=ns.tenant,
            source_backend=ns.source_backend,
            target_backend=ns.target_backend,
            batch_size=ns.batch_size,
            include_archived=ns.include_archived,
        )
        return True

    print(f"Error: unknown memory subcommand: {sub}", file=sys.stderr)
    raise SystemExit(2)


def _print_help_and_exit(argv: list[str]) -> None:
    """Print plain help when Typer/Rich make_metavar bug triggers (--help)."""
    argv = [a for a in argv if a not in ("--help", "-h")]
    if not argv:
        print("Usage: owlclaw [OPTIONS] COMMAND [ARGS]...")
        print("\n  OwlClaw — Agent base for business applications.\n")
        print("Commands:")
        print("  db     Database: init, migrate, status")
        print("  memory Agent memory: list, prune, reset, stats")
        print("  skill  Create, validate, list Agent Skills (SKILL.md)")
        print("\n  owlclaw db --help   owlclaw skill --help")
        sys.exit(0)
    if argv == ["db"]:
        print("Usage: owlclaw db [OPTIONS] COMMAND [ARGS]...")
        print("\n  Database operations: init, migrate, status, revision.\n")
        print("Commands:")
        print("  init     Create owlclaw (and optionally hatchet) database, role, pgvector")
        print("  migrate  Run Alembic migrations (owlclaw schema)")
        print("  status   Show connection and migration status")
        print("  revision Create new migration script (--empty or autogenerate)")
        print("\n  owlclaw db init --help | owlclaw db migrate --help | owlclaw db revision --help")
        sys.exit(0)
    if argv == ["db", "revision"]:
        print("Usage: owlclaw db revision [OPTIONS]")
        print("\n  Create a new migration script (autogenerate or empty template).\n")
        print("Options:")
        print("  -m, --message TEXT    Revision message (required for autogenerate)")
        print("  --empty               Create empty migration template")
        print("  --database-url TEXT   Database URL (default: OWLCLAW_DATABASE_URL)")
        print("  --help                Show this message and exit")
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
    if argv == ["memory"]:
        print("Usage: owlclaw memory [OPTIONS] COMMAND [ARGS]...")
        print("\n  Agent memory operations (list, prune, reset, stats).\n")
        print("Commands:")
        print("  list    List memory entries with pagination and tag filter")
        print("  prune   Delete memory entries by time/tag filter")
        print("  reset   Delete all memory entries for an agent")
        print("  stats   Show memory statistics")
        print("  migrate-backend  Migrate memory data between backends")
        print("\n  owlclaw memory list --help | owlclaw memory prune --help")
        sys.exit(0)
    if argv == ["memory", "list"]:
        print("Usage: owlclaw memory list --agent <name> [OPTIONS]")
        print("\n  List memory entries with pagination and tag filter.")
        sys.exit(0)
    if argv == ["memory", "prune"]:
        print("Usage: owlclaw memory prune --agent <name> [OPTIONS]")
        print("\n  Delete memory entries by time/tag filter.")
        sys.exit(0)
    if argv == ["memory", "reset"]:
        print("Usage: owlclaw memory reset --agent <name> --confirm [OPTIONS]")
        print("\n  Delete all memory entries for an agent.")
        sys.exit(0)
    if argv == ["memory", "stats"]:
        print("Usage: owlclaw memory stats --agent <name> [OPTIONS]")
        print("\n  Show memory statistics.")
        sys.exit(0)
    if argv == ["memory", "migrate-backend"]:
        print("Usage: owlclaw memory migrate-backend --agent <name> --source-backend <x> --target-backend <y> [OPTIONS]")
        print("\n  Migrate memory entries between storage backends.")
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
    print("  memory Agent memory: list, prune, reset, stats, migrate-backend")
    print("  skill  Create, validate, list Agent Skills (SKILL.md)")
    sys.exit(0)


def _dispatch_db_revision(argv: list[str]) -> bool:
    """Dispatch `owlclaw db revision` via argparse (avoids Typer Option secondary-flag issue)."""
    if len(argv) < 2 or argv[0] != "db" or argv[1] != "revision":
        return False
    if "--help" in argv or "-h" in argv:
        _print_help_and_exit(["db", "revision"])
    import argparse
    from owlclaw.cli.db_revision import revision_command
    parser = argparse.ArgumentParser(prog="owlclaw db revision")
    parser.add_argument("-m", "--message", default="", help="Revision message")
    parser.add_argument("--empty", action="store_true", help="Empty migration template")
    parser.add_argument("--database-url", dest="database_url", default="", help="Database URL")
    ns = parser.parse_args(argv[2:])
    revision_command(message=ns.message, empty_template=ns.empty, database_url=ns.database_url or "")
    return True


def main() -> None:
    """CLI entry point — dispatches to subcommands."""
    if "--help" in sys.argv or "-h" in sys.argv:
        argv = [a for a in sys.argv[1:] if a not in ("--help", "-h")]
        _print_help_and_exit(argv)
    try:
        if _dispatch_db_revision(sys.argv[1:]):
            return
    except SystemExit:
        raise
    except Exception:
        raise
    try:
        if _dispatch_memory_command(sys.argv[1:]):
            return
    except ClickExit as e:
        raise SystemExit(e.exit_code) from None
    try:
        if _dispatch_skill_command(sys.argv[1:]):
            return
    except ClickExit as e:
        raise SystemExit(e.exit_code) from None
    try:
        app()
    except TypeError as e:
        if "make_metavar" in str(e):
            argv = sys.argv[1:]
            _print_help_and_exit(argv)
        raise


if __name__ == "__main__":
    main()
