"""Initial schema (placeholder). No OwlClaw tables yet; Ledger/Memory add later.

Revision ID: 001_initial
Revises:
Create Date: 2026-02-11

"""
from typing import Sequence, Union

from alembic import op


revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No tables in this revision; alembic_version is created by Alembic."""
    pass


def downgrade() -> None:
    """Nothing to drop."""
    pass
