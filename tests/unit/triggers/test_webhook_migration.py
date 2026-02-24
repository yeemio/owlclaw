"""Static verification for webhook trigger migration script."""

from pathlib import Path

MIGRATION_PATH = Path("migrations/versions/004_webhook_trigger_core.py")


def test_webhook_migration_file_exists_with_expected_revision_metadata() -> None:
    content = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'revision: str = "004_webhook"' in content
    assert 'down_revision: str | None = "003_memory"' in content
    assert '"""Add webhook trigger persistence tables.' in content


def test_webhook_migration_declares_required_tables() -> None:
    content = MIGRATION_PATH.read_text(encoding="utf-8")
    for table_name in [
        '"webhook_endpoints"',
        '"webhook_events"',
        '"webhook_idempotency_keys"',
        '"webhook_transformation_rules"',
        '"webhook_executions"',
    ]:
        assert table_name in content


def test_webhook_migration_declares_tenant_indexes() -> None:
    content = MIGRATION_PATH.read_text(encoding="utf-8")
    required_indexes = [
        "idx_webhook_endpoints_tenant_target_agent",
        "idx_webhook_events_tenant_endpoint_timestamp",
        "idx_webhook_idempotency_tenant_expires",
        "idx_webhook_rules_tenant_name",
        "idx_webhook_executions_tenant_status",
    ]
    for snippet in required_indexes:
        assert snippet in content
