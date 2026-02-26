"""Unit and property tests for OwlHub Validator."""

from __future__ import annotations

from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.owlhub.schema import SkillManifest
from owlclaw.owlhub.validator import Validator


def _valid_manifest() -> SkillManifest:
    return SkillManifest(
        name="entry-monitor",
        version="1.2.3",
        publisher="acme-labs",
        description="A valid skill manifest description.",
        license="MIT",
        dependencies={"market-data": "^1.0.0"},
    )


def test_validate_version_examples() -> None:
    validator = Validator()
    assert validator.validate_version("1.0.0")
    assert validator.validate_version("1.2.3-alpha.1")
    assert validator.validate_version("1.2.3+build.9")
    assert not validator.validate_version("1.0")
    assert not validator.validate_version("v1.0.0")


def test_validate_manifest_required_fields() -> None:
    validator = Validator()
    result = validator.validate_manifest({"name": "", "version": "1.0.0"})
    assert result.is_valid is False
    assert any(error.field == "publisher" for error in result.errors)
    assert any(error.field == "description" for error in result.errors)
    assert any(error.field == "license" for error in result.errors)


def test_validate_structure_and_dependencies(tmp_path: Path) -> None:
    validator = Validator()
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()
    no_skill_file = validator.validate_structure(skill_dir)
    assert no_skill_file.is_valid is False

    (skill_dir / "SKILL.md").write_text("---\nname: a\ndescription: b\n---\n", encoding="utf-8")
    with_skill_file = validator.validate_structure(skill_dir)
    assert with_skill_file.is_valid is True

    bad_deps = validator.validate_dependencies({"MarketData": ">=1.0"})
    assert bad_deps.is_valid is False


@settings(max_examples=10)
@given(
    major=st.integers(min_value=0, max_value=20),
    minor=st.integers(min_value=0, max_value=20),
    patch=st.integers(min_value=0, max_value=20),
)
def test_property_2_semver_validation(major: int, minor: int, patch: int) -> None:
    """Property 2: semver strings are accepted."""
    validator = Validator()
    assert validator.validate_version(f"{major}.{minor}.{patch}") is True


@settings(max_examples=10)
@given(
    missing_field=st.sampled_from(["name", "version", "publisher", "description", "license"]),
)
def test_property_5_required_field_validation(missing_field: str) -> None:
    """Property 5: missing required fields are rejected."""
    validator = Validator()
    manifest = {
        "name": "entry-monitor",
        "version": "1.2.3",
        "publisher": "acme-labs",
        "description": "A valid skill manifest description.",
        "license": "MIT",
    }
    manifest.pop(missing_field)
    result = validator.validate_manifest(manifest)
    assert result.is_valid is False
    assert any(error.field == missing_field for error in result.errors)


@settings(max_examples=10)
@given(
    bad_name=st.text(min_size=1, max_size=8).filter(lambda s: "-" not in s and not s.islower()),
    bad_version=st.text(min_size=1, max_size=8).filter(lambda s: s.count(".") < 2),
)
def test_property_13_validation_completeness(bad_name: str, bad_version: str) -> None:
    """Property 13: validator reports multiple manifest errors in one pass."""
    validator = Validator()
    payload = {
        "name": bad_name,
        "version": bad_version,
        "publisher": "bad Publisher",
        "description": "short",
        "license": "",
        "dependencies": {"BadDep": ">=1.0"},
    }
    result = validator.validate_manifest(payload)
    assert result.is_valid is False
    assert len(result.errors) >= 4


def test_validate_manifest_dataclass_path() -> None:
    validator = Validator()
    result = validator.validate_manifest(_valid_manifest())
    assert result.is_valid is True


