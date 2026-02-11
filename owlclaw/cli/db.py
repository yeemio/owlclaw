"""owlclaw db — init, migrate, status (database CLI)."""

import typer

from owlclaw.cli.db_init import init_command
from owlclaw.cli.db_migrate import migrate_command
from owlclaw.cli.db_status import status_command

db_app = typer.Typer(
    name="db",
    help="Database operations: init, migrate, status.",
)

db_app.command("init")(init_command)
db_app.command("migrate")(migrate_command)
db_app.command("status")(status_command)
