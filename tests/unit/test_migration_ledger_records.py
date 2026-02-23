"""Static verification for governance ledger migration script."""

from pathlib import Path

MIGRATION_PATH = Path("migrations/versions/002_add_ledger_records.py")


def test_ledger_migration_file_exists_with_expected_revision_metadata() -> None:
    content = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'revision: str = "002_ledger"' in content
    assert 'down_revision: str | None = "001_initial"' in content
    assert '"""Add ledger_records table for governance execution logging.' in content


def test_ledger_migration_declares_required_columns() -> None:
    content = MIGRATION_PATH.read_text(encoding="utf-8")
    required_columns = [
        'sa.Column("id", UUID(as_uuid=True), primary_key=True)',
        '"tenant_id",',
        'sa.Column("agent_id", sa.String(255), nullable=False)',
        'sa.Column("run_id", sa.String(255), nullable=False)',
        'sa.Column("capability_name", sa.String(255), nullable=False)',
        'sa.Column("task_type", sa.String(100), nullable=False)',
        'sa.Column("input_params", JSONB, nullable=False)',
        'sa.Column("execution_time_ms", sa.Integer(), nullable=False)',
        'sa.Column("estimated_cost", sa.DECIMAL(10, 4), nullable=False)',
        'sa.Column("status", sa.String(32), nullable=False)',
        '"created_at",',
    ]
    for snippet in required_columns:
        assert snippet in content


def test_ledger_migration_declares_tenant_and_lookup_indexes() -> None:
    content = MIGRATION_PATH.read_text(encoding="utf-8")
    required_indexes = [
        '"idx_ledger_tenant_agent"',
        '"idx_ledger_tenant_capability"',
        '"idx_ledger_tenant_created"',
        'op.f("ix_ledger_records_agent_id")',
        'op.f("ix_ledger_records_run_id")',
        'op.f("ix_ledger_records_status")',
        'op.f("ix_ledger_records_tenant_id")',
    ]
    for snippet in required_indexes:
        assert snippet in content
