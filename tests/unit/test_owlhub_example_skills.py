"""Validate OwlHub example skills metadata."""

from __future__ import annotations

from pathlib import Path

import yaml

from owlclaw.owlhub.validator import Validator


def _load_frontmatter(skill_text: str) -> dict[str, object]:
    if not skill_text.startswith("---"):
        return {}
    parts = skill_text.split("---", 2)
    if len(parts) < 3:
        return {}
    payload = yaml.safe_load(parts[1])
    return payload if isinstance(payload, dict) else {}


def test_example_skills_have_valid_manifest_frontmatter() -> None:
    repo = Path(__file__).resolve().parents[2]
    root = repo / "examples" / "owlhub_skills"
    validator = Validator()
    skill_files = sorted(root.rglob("SKILL.md"))
    assert len(skill_files) >= 3
    for skill_file in skill_files:
        manifest = _load_frontmatter(skill_file.read_text(encoding="utf-8"))
        metadata = manifest.get("metadata") if isinstance(manifest.get("metadata"), dict) else {}
        result = validator.validate_manifest(
            {
                "name": manifest.get("name", ""),
                "publisher": manifest.get("publisher", ""),
                "version": metadata.get("version", ""),
                "description": manifest.get("description", ""),
                "license": manifest.get("license", "MIT"),
                "tags": manifest.get("tags", []),
                "dependencies": manifest.get("dependencies", {}),
            }
        )
        assert result.is_valid, f"{skill_file}: {result.errors}"
