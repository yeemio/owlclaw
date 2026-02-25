"""Static verification for OwlHub core migration script."""

from pathlib import Path

MIGRATION_PATH = Path("migrations/versions/006_owlhub_core_tables.py")


def test_owlhub_migration_metadata_is_correct() -> None:
    content = MIGRATION_PATH.read_text(encoding="utf-8")
    assert 'revision: str = "006_owlhub_core"' in content
    assert 'down_revision: str | None = "005_signal_state"' in content
    assert "Add OwlHub core service tables." in content


def test_owlhub_migration_creates_required_tables() -> None:
    content = MIGRATION_PATH.read_text(encoding="utf-8")
    required_tables = [
        'op.create_table(\n        "skills",',
        'op.create_table(\n        "skill_versions",',
        'op.create_table(\n        "skill_statistics",',
        'op.create_table(\n        "review_records",',
    ]
    for snippet in required_tables:
        assert snippet in content


def test_owlhub_migration_declares_required_indexes() -> None:
    content = MIGRATION_PATH.read_text(encoding="utf-8")
    required_indexes = [
        '"idx_skills_tenant_name"',
        '"idx_skills_tenant_publisher"',
        '"idx_skills_tags_gin"',
        '"idx_skill_versions_tenant_skill"',
        '"idx_skill_statistics_tenant_skill"',
        '"idx_review_records_tenant_publisher"',
    ]
    for snippet in required_indexes:
        assert snippet in content
