"""Static checks for governance-hardening migration."""

from pathlib import Path

MIGRATION_PATH = Path("migrations/versions/009_governance_hardening_indexes_and_webhook_idempotency_pk.py")


def test_governance_hardening_migration_exists_with_expected_metadata() -> None:
    content = MIGRATION_PATH.read_text(encoding="utf-8")
    assert 'revision: str = "009_governance_hardening"' in content
    assert 'down_revision: str | None = "008_ledger_runtime_metadata"' in content


def test_governance_hardening_migration_covers_ledger_index_fixes() -> None:
    content = MIGRATION_PATH.read_text(encoding="utf-8")
    required_snippets = [
        'op.drop_index(op.f("ix_ledger_records_agent_id"), table_name="ledger_records")',
        'op.drop_index(op.f("ix_ledger_records_execution_mode"), table_name="ledger_records")',
        'op.create_index("idx_ledger_tenant_run", "ledger_records", ["tenant_id", "run_id"])',
        'op.create_index("idx_ledger_tenant_execution_mode", "ledger_records", ["tenant_id", "execution_mode"])',
    ]
    for snippet in required_snippets:
        assert snippet in content


def test_governance_hardening_migration_switches_webhook_idempotency_pk() -> None:
    content = MIGRATION_PATH.read_text(encoding="utf-8")
    required_snippets = [
        '"webhook_idempotency_keys"',
        '"pk_webhook_idempotency_keys"',
        '"uq_webhook_idempotency_keys_key"',
        '"idx_webhook_idempotency_tenant_key"',
    ]
    for snippet in required_snippets:
        assert snippet in content
