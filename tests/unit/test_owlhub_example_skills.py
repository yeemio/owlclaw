"""Validate OwlHub example skills metadata."""

from __future__ import annotations

from pathlib import Path

from owlclaw.owlhub.indexer.crawler import SkillRepositoryCrawler
from owlclaw.owlhub.validator import Validator


def test_example_skills_have_valid_manifest_frontmatter() -> None:
    repo = Path(__file__).resolve().parents[2]
    root = repo / "examples" / "owlhub_skills"
    validator = Validator()
    manifests = SkillRepositoryCrawler().crawl_repository(str(root))
    assert len(manifests) >= 3
    for manifest in manifests:
        result = validator.validate_manifest(manifest)
        assert result.is_valid, f"{manifest.name}: {result.errors}"
