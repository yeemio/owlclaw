"""Validate OwlHub example skills metadata."""

from __future__ import annotations

from pathlib import Path

from owlclaw.owlhub.validator import Validator


def test_example_skills_have_valid_manifest_frontmatter() -> None:
    repo = Path(__file__).resolve().parents[2]
    root = repo / "examples" / "owlhub_skills"
    validator = Validator()
    skill_files = sorted(root.rglob("SKILL.md"))
    assert len(skill_files) >= 3
    for skill_file in skill_files:
        parsed = validator.parse_skill_markdown(skill_file.read_text(encoding="utf-8"))
        assert parsed.name
        assert parsed.publisher
        assert parsed.version
        assert parsed.description
        result = validator.validate_manifest(
            {
                "name": parsed.name,
                "publisher": parsed.publisher,
                "version": parsed.version,
                "description": parsed.description,
                "license": parsed.license or "MIT",
                "tags": parsed.tags,
                "dependencies": parsed.dependencies,
            }
        )
        assert result.is_valid, f"{skill_file}: {result.errors}"
