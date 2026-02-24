"""CLI tools — owlclaw db, owlclaw skill, owlclaw scan, owlclaw migrate."""

import argparse
import sys

import typer
from click.exceptions import Exit as ClickExit

from owlclaw.cli.db import db_app
from owlclaw.cli.init_config import init_config_command
from owlclaw.cli.memory import memory_app
from owlclaw.cli.reload_config import reload_config_command
from owlclaw.cli.skill import skill_app

app = typer.Typer(
    name="owlclaw",
    help="OwlClaw — Agent base for business applications.",
)
app.add_typer(db_app, name="db")
app.add_typer(memory_app, name="memory")
app.add_typer(skill_app, name="skill")


@app.command("init")
def init_command(
    path: str = typer.Option(".", "--path", help="Output directory"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing owlclaw.yaml"),
) -> None:
    """Generate default owlclaw.yaml in target directory."""
    init_config_command(path=path, force=force)


@app.command("reload")
def reload_command(
    config: str = typer.Option("", "--config", help="Optional config file path"),
) -> None:
    """Reload configuration and print applied/skipped changes."""
    reload_config_command(config=config or None)


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

    if sub == "search":
        from owlclaw.cli.skill_hub import search_command

        parser = argparse.ArgumentParser(add_help=False, prog="owlclaw skill search")
        parser.add_argument("--query", "-q", default="")
        parser.add_argument("--mode", default="auto")
        parser.add_argument("--api-base-url", default="")
        parser.add_argument("--api-token", default="")
        parser.add_argument("--index-url", default="./index.json")
        parser.add_argument("--tags", default="")
        parser.add_argument("--tag-mode", default="and")
        parser.add_argument("--include-draft", action="store_true", default=False)
        parser.add_argument("--install-dir", default="./.owlhub/skills")
        parser.add_argument("--lock-file", default="./skill-lock.json")
        ns = parser.parse_args(sub_argv)
        search_command(
            query=ns.query,
            mode=ns.mode,
            api_base_url=ns.api_base_url,
            api_token=ns.api_token,
            index_url=ns.index_url,
            tags=ns.tags,
            tag_mode=ns.tag_mode,
            include_draft=ns.include_draft,
            install_dir=ns.install_dir,
            lock_file=ns.lock_file,
        )
        return True

    if sub == "install":
        from owlclaw.cli.skill_hub import install_command

        parser = argparse.ArgumentParser(add_help=False, prog="owlclaw skill install")
        parser.add_argument("name")
        parser.add_argument("--version", default="")
        parser.add_argument("--no-deps", action="store_true", default=False)
        parser.add_argument("--force", action="store_true", default=False)
        parser.add_argument("--mode", default="auto")
        parser.add_argument("--api-base-url", default="")
        parser.add_argument("--api-token", default="")
        parser.add_argument("--index-url", default="./index.json")
        parser.add_argument("--install-dir", default="./.owlhub/skills")
        parser.add_argument("--lock-file", default="./skill-lock.json")
        ns = parser.parse_args(sub_argv)
        install_command(
            name=ns.name,
            version=ns.version,
            no_deps=ns.no_deps,
            force=ns.force,
            mode=ns.mode,
            api_base_url=ns.api_base_url,
            api_token=ns.api_token,
            index_url=ns.index_url,
            install_dir=ns.install_dir,
            lock_file=ns.lock_file,
        )
        return True

    if sub == "installed":
        from owlclaw.cli.skill_hub import installed_command

        parser = argparse.ArgumentParser(add_help=False, prog="owlclaw skill installed")
        parser.add_argument("--mode", default="auto")
        parser.add_argument("--api-base-url", default="")
        parser.add_argument("--api-token", default="")
        parser.add_argument("--index-url", default="./index.json")
        parser.add_argument("--install-dir", default="./.owlhub/skills")
        parser.add_argument("--lock-file", default="./skill-lock.json")
        ns = parser.parse_args(sub_argv)
        installed_command(
            mode=ns.mode,
            api_base_url=ns.api_base_url,
            api_token=ns.api_token,
            index_url=ns.index_url,
            install_dir=ns.install_dir,
            lock_file=ns.lock_file,
        )
        return True

    if sub == "update":
        from owlclaw.cli.skill_hub import update_command

        parser = argparse.ArgumentParser(add_help=False, prog="owlclaw skill update")
        parser.add_argument("name", nargs="?", default="")
        parser.add_argument("--mode", default="auto")
        parser.add_argument("--api-base-url", default="")
        parser.add_argument("--api-token", default="")
        parser.add_argument("--index-url", default="./index.json")
        parser.add_argument("--install-dir", default="./.owlhub/skills")
        parser.add_argument("--lock-file", default="./skill-lock.json")
        ns = parser.parse_args(sub_argv)
        update_command(
            name=ns.name,
            mode=ns.mode,
            api_base_url=ns.api_base_url,
            api_token=ns.api_token,
            index_url=ns.index_url,
            install_dir=ns.install_dir,
            lock_file=ns.lock_file,
        )
        return True

    if sub == "publish":
        from owlclaw.cli.skill_hub import publish_command

        parser = argparse.ArgumentParser(add_help=False, prog="owlclaw skill publish")
        parser.add_argument("path", nargs="?", default=".")
        parser.add_argument("--mode", default="api")
        parser.add_argument("--api-base-url", default="")
        parser.add_argument("--api-token", default="")
        parser.add_argument("--index-url", default="./index.json")
        parser.add_argument("--install-dir", default="./.owlhub/skills")
        parser.add_argument("--lock-file", default="./skill-lock.json")
        ns = parser.parse_args(sub_argv)
        publish_command(
            path=ns.path,
            mode=ns.mode,
            api_base_url=ns.api_base_url,
            api_token=ns.api_token,
            index_url=ns.index_url,
            install_dir=ns.install_dir,
            lock_file=ns.lock_file,
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


def _dispatch_trigger_command(argv: list[str]) -> bool:
    """Dispatch `owlclaw trigger ...` using argparse for command-specific templates."""
    if not argv or argv[0] != "trigger":
        return False
    if len(argv) < 2:
        _print_help_and_exit(["trigger"])

    sub = argv[1]
    sub_argv = argv[2:]
    if "--help" in sub_argv or "-h" in sub_argv:
        if sub == "template" and sub_argv and sub_argv[0] == "db-change":
            _print_help_and_exit(["trigger", "template", "db-change"])
        _print_help_and_exit(["trigger", sub])

    if sub != "template":
        print(f"Error: unknown trigger subcommand: {sub}", file=sys.stderr)
        raise SystemExit(2)
    if len(sub_argv) < 1:
        _print_help_and_exit(["trigger", "template"])

    template_name = sub_argv[0]
    if template_name != "db-change":
        print(f"Error: unknown trigger template: {template_name}", file=sys.stderr)
        raise SystemExit(2)

    from owlclaw.cli.trigger_template import db_change_template_command

    parser = argparse.ArgumentParser(add_help=False, prog="owlclaw trigger template db-change")
    parser.add_argument("--output", "--path", "-o", "-p", dest="output_dir", default=".")
    parser.add_argument("--channel", default="position_changes")
    parser.add_argument("--table", dest="table_name", default="positions")
    parser.add_argument("--trigger-name", dest="trigger_name", default="position_changes_trigger")
    parser.add_argument("--function-name", dest="function_name", default="notify_position_changes")
    parser.add_argument("--force", "-f", action="store_true", default=False)
    ns = parser.parse_args(sub_argv[1:])
    target = db_change_template_command(
        output_dir=ns.output_dir,
        channel=ns.channel,
        table_name=ns.table_name,
        trigger_name=ns.trigger_name,
        function_name=ns.function_name,
        force=ns.force,
    )
    print(f"Generated: {target}")
    return True


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
        print("  trigger Trigger templates (db-change)")
        print("\n  owlclaw db --help   owlclaw skill --help")
        sys.exit(0)
    if argv == ["db"]:
        print("Usage: owlclaw db [OPTIONS] COMMAND [ARGS]...")
        print("\n  Database operations: init, migrate, status, revision, rollback, backup.\n")
        print("Commands:")
        print("  init     Create owlclaw (and optionally hatchet) database, role, pgvector")
        print("  migrate  Run Alembic migrations (owlclaw schema)")
        print("  status   Show connection and migration status")
        print("  revision Create new migration script (--empty or autogenerate)")
        print("  rollback Roll back migrations (--target, --steps, or one step)")
        print("  backup   Create database backup (pg_dump)")
        print("  restore  Restore database from backup (psql/pg_restore)")
        print("  check    Run database health checks")
        print("\n  owlclaw db init --help | owlclaw db backup --help | owlclaw db check --help")
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
    if argv == ["db", "rollback"]:
        print("Usage: owlclaw db rollback [OPTIONS]")
        print("\n  Roll back database migrations (Alembic downgrade).\n")
        print("Options:")
        print("  -t, --target TEXT     Revision to downgrade to (e.g. base or revision id)")
        print("  -s, --steps INTEGER  Number of revisions to downgrade (default: 1 if omitted)")
        print("  --database-url TEXT  Database URL (default: OWLCLAW_DATABASE_URL)")
        print("  --dry-run             Show what would be rolled back without executing")
        print("  -y, --yes             Skip confirmation prompt")
        print("  --help                Show this message and exit")
        sys.exit(0)
    if argv == ["db", "backup"]:
        print("Usage: owlclaw db backup [OPTIONS]")
        print("\n  Create database backup using pg_dump.\n")
        print("Options:")
        print("  -o, --output PATH     Output file path (required)")
        print("  -F, --format [plain|custom]  Backup format (default: plain)")
        print("  --schema-only         Dump schema only")
        print("  --data-only           Dump data only")
        print("  --database-url TEXT  Database URL (default: OWLCLAW_DATABASE_URL)")
        print("  --help                Show this message and exit")
        sys.exit(0)
    if argv == ["db", "restore"]:
        print("Usage: owlclaw db restore [OPTIONS]")
        print("\n  Restore database from backup file (SQL or pg_dump custom).\n")
        print("Options:")
        print("  -i, --input PATH      Input backup file (required)")
        print("  --clean               Drop existing objects before restore (pg_restore only)")
        print("  --database-url TEXT  Database URL (default: OWLCLAW_DATABASE_URL)")
        print("  -y, --yes             Skip confirmation prompt")
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
    if argv == ["db", "check"]:
        print("Usage: owlclaw db check [OPTIONS]")
        print("\n  Run database health checks (connection, migration, pgvector, pool, disk, slow queries).\n")
        print("Options:")
        print("  --database-url TEXT  Database URL (default: OWLCLAW_DATABASE_URL)")
        print("  -v, --verbose        Show detailed progress")
        print("  --help               Show this message and exit")
        sys.exit(0)
    if argv == ["skill"]:
        print("Usage: owlclaw skill [OPTIONS] COMMAND [ARGS]...")
        print("\n  Create, validate, and list Agent Skills (SKILL.md). Local only.\n")
        print("Commands:")
        print("  init      Scaffold a new SKILL.md from template")
        print("  validate  Validate SKILL.md in current dir")
        print("  list      List skills in a directory")
        print("  templates List templates from the template library")
        print("  publish   Publish a local skill to OwlHub API")
        print("\n  owlclaw skill init --help | owlclaw skill templates --help")
        sys.exit(0)
    if argv == ["init"]:
        print("Usage: owlclaw init [OPTIONS]")
        print("\n  Generate default owlclaw.yaml in target directory.")
        print("Options:")
        print("  --path TEXT   Output directory (default: current directory)")
        print("  --force       Overwrite existing owlclaw.yaml")
        print("  --help        Show this message and exit")
        sys.exit(0)
    if argv == ["reload"]:
        print("Usage: owlclaw reload [OPTIONS]")
        print("\n  Reload configuration and display applied/skipped changes.")
        print("Options:")
        print("  --config TEXT  Optional config file path")
        print("  --help         Show this message and exit")
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
    if argv == ["trigger"]:
        print("Usage: owlclaw trigger [OPTIONS] COMMAND [ARGS]...")
        print("\n  Trigger tooling commands.")
        print("Commands:")
        print("  template  Generate trigger templates")
        print("\n  owlclaw trigger template --help")
        sys.exit(0)
    if argv == ["trigger", "template"]:
        print("Usage: owlclaw trigger template [OPTIONS] TEMPLATE")
        print("\n  Generate trigger templates.")
        print("Templates:")
        print("  db-change  PostgreSQL NOTIFY trigger SQL")
        print("\n  owlclaw trigger template db-change --help")
        sys.exit(0)
    if argv == ["trigger", "db-change"] or argv == ["trigger", "template", "db-change"]:
        print("Usage: owlclaw trigger template db-change [OPTIONS]")
        print("\n  Generate PostgreSQL NOTIFY trigger SQL template.")
        print("Options:")
        print("  --output, --path TEXT      Output directory (default: .)")
        print("  --channel TEXT             NOTIFY channel (default: position_changes)")
        print("  --table TEXT               Source table (default: positions)")
        print("  --trigger-name TEXT        Trigger name (default: position_changes_trigger)")
        print("  --function-name TEXT       Function name (default: notify_position_changes)")
        print("  --force                    Overwrite existing target file")
        print("  --help                     Show this message and exit")
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
    print("  db     Database: init, migrate, status, revision, rollback")
    print("  memory Agent memory: list, prune, reset, stats, migrate-backend")
    print("  skill  Create, validate, list Agent Skills (SKILL.md)")
    print("  trigger Trigger templates (db-change)")
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


def _dispatch_db_rollback(argv: list[str]) -> bool:
    """Dispatch `owlclaw db rollback` via argparse (Typer optional-option compatibility)."""
    if len(argv) < 2 or argv[0] != "db" or argv[1] != "rollback":
        return False
    if "--help" in argv or "-h" in argv:
        _print_help_and_exit(["db", "rollback"])
    parser = argparse.ArgumentParser(prog="owlclaw db rollback")
    parser.add_argument("-t", "--target", default="", help="Revision to downgrade to")
    parser.add_argument("-s", "--steps", type=int, default=0, help="Number of revisions to downgrade")
    parser.add_argument("--database-url", dest="database_url", default="", help="Database URL")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be rolled back")
    parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")
    ns = parser.parse_args(argv[2:])
    from owlclaw.cli.db_rollback import rollback_command
    rollback_command(
        target=ns.target or "",
        steps=ns.steps or 0,
        database_url=ns.database_url or "",
        dry_run=ns.dry_run,
        yes=ns.yes,
    )
    return True


def _dispatch_db_backup(argv: list[str]) -> bool:
    """Dispatch `owlclaw db backup` via argparse."""
    if len(argv) < 2 or argv[0] != "db" or argv[1] != "backup":
        return False
    if "--help" in argv or "-h" in argv:
        _print_help_and_exit(["db", "backup"])
    parser = argparse.ArgumentParser(prog="owlclaw db backup")
    parser.add_argument("-o", "--output", required=True, help="Output file path")
    parser.add_argument("-F", "--format", dest="format_name", default="plain", help="plain or custom")
    parser.add_argument("--schema-only", action="store_true", help="Schema only")
    parser.add_argument("--data-only", action="store_true", help="Data only")
    parser.add_argument("--database-url", dest="database_url", default="", help="Database URL")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed progress")
    ns = parser.parse_args(argv[2:])
    from owlclaw.cli.db_backup import backup_command
    backup_command(
        output=ns.output,
        format_name=ns.format_name or "plain",
        schema_only=ns.schema_only,
        data_only=ns.data_only,
        database_url=ns.database_url or "",
        verbose=ns.verbose,
    )
    return True


def _dispatch_db_restore(argv: list[str]) -> bool:
    """Dispatch `owlclaw db restore` via argparse."""
    if len(argv) < 2 or argv[0] != "db" or argv[1] != "restore":
        return False
    if "--help" in argv or "-h" in argv:
        _print_help_and_exit(["db", "restore"])
    parser = argparse.ArgumentParser(prog="owlclaw db restore")
    parser.add_argument("-i", "--input", required=True, help="Input backup file path")
    parser.add_argument("--clean", action="store_true", help="Drop objects before restore (pg_restore)")
    parser.add_argument("--database-url", dest="database_url", default="", help="Database URL")
    parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed progress")
    ns = parser.parse_args(argv[2:])
    from owlclaw.cli.db_restore import restore_command
    restore_command(
        input_path=ns.input,
        clean=ns.clean,
        database_url=ns.database_url or "",
        yes=ns.yes,
        verbose=ns.verbose,
    )
    return True


def main() -> None:
    """CLI entry point — dispatches to subcommands."""
    if "--help" in sys.argv or "-h" in sys.argv:
        argv = [a for a in sys.argv[1:] if a not in ("--help", "-h")]
        _print_help_and_exit(argv)
    try:
        _main_impl()
    except KeyboardInterrupt:
        sys.exit(130)


def _main_impl() -> None:
    """Inner main; KeyboardInterrupt is handled in main()."""
    try:
        if _dispatch_db_revision(sys.argv[1:]):
            return
    except SystemExit:
        raise
    try:
        if _dispatch_db_rollback(sys.argv[1:]):
            return
    except SystemExit:
        raise
    except Exception:
        raise
    try:
        if _dispatch_db_backup(sys.argv[1:]):
            return
    except SystemExit:
        raise
    except Exception:
        raise
    try:
        if _dispatch_db_restore(sys.argv[1:]):
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
        if _dispatch_trigger_command(sys.argv[1:]):
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
