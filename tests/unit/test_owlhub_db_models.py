"""Unit tests for OwlHub SQLAlchemy model definitions."""

from __future__ import annotations

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from owlclaw.owlhub.models import ReviewRecord, Skill, SkillStatistics, SkillVersion


def test_owlhub_model_tablenames_match_expected_contract() -> None:
    assert Skill.__tablename__ == "skills"
    assert SkillVersion.__tablename__ == "skill_versions"
    assert SkillStatistics.__tablename__ == "skill_statistics"
    assert ReviewRecord.__tablename__ == "review_records"


def test_skill_model_has_unique_constraint_for_publisher_name_per_tenant() -> None:
    constraints = {constraint.name for constraint in Skill.__table__.constraints}
    assert "uq_skills_tenant_publisher_name" in constraints


def test_skill_version_model_has_unique_constraint_for_version_per_skill_per_tenant() -> None:
    constraints = {constraint.name for constraint in SkillVersion.__table__.constraints}
    assert "uq_skill_versions_tenant_skill_version" in constraints


def test_postgresql_ddl_includes_tags_array_and_metadata_jsonb() -> None:
    skill_sql = str(CreateTable(Skill.__table__).compile(dialect=postgresql.dialect()))
    version_sql = str(CreateTable(SkillVersion.__table__).compile(dialect=postgresql.dialect()))
    assert "tags VARCHAR(64)[]" in skill_sql
    assert "metadata_json JSONB" in version_sql
