"""Static checks for governance-hardening migration."""

from pathlib import Path

MIGRATION_PATH = Path("migrations/versions/009_governance_hardening_indexes_and_webhook_idempotency_pk.py")
QUALITY_INDEX_MIGRATION_PATH = Path("migrations/versions/010_quality_store_tenant_prefixed_indexes.py")
MERGE_MIGRATION_PATH = Path("migrations/versions/011_merge_phase12_migration_heads.py")
ALEMBIC_ENV_PATH = Path("migrations/env.py")


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


def test_quality_store_migration_exists_with_expected_metadata() -> None:
    content = QUALITY_INDEX_MIGRATION_PATH.read_text(encoding="utf-8")
    assert 'revision: str = "010_quality_tenant_indexes"' in content
    assert 'down_revision: str | None = "009_governance_hardening"' in content


def test_quality_store_migration_drops_non_tenant_indexes() -> None:
    content = QUALITY_INDEX_MIGRATION_PATH.read_text(encoding="utf-8")
    required_snippets = [
        'op.drop_index(op.f("ix_skill_quality_snapshots_skill_name"), table_name="skill_quality_snapshots")',
        'op.drop_index(op.f("ix_skill_quality_snapshots_computed_at"), table_name="skill_quality_snapshots")',
        '"idx_quality_tenant_skill_name"',
        '"idx_quality_tenant_computed"',
    ]
    for snippet in required_snippets:
        assert snippet in content


def test_alembic_env_imports_owlhub_models() -> None:
    content = ALEMBIC_ENV_PATH.read_text(encoding="utf-8")
    assert "from owlclaw.owlhub.models import ReviewRecord, Skill, SkillStatistics, SkillVersion" in content


def test_phase12_migration_heads_are_merged() -> None:
    content = MERGE_MIGRATION_PATH.read_text(encoding="utf-8")
    assert 'revision: str = "011_merge_phase12_heads"' in content
    assert 'down_revision: tuple[str, str] = ("009_webhook_auth_token_hash", "010_quality_tenant_indexes")' in content
