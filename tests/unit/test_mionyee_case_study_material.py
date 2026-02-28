"""Checks for content-launch case study material structure."""

from __future__ import annotations

from pathlib import Path


def test_mionyee_case_study_has_required_sections() -> None:
    payload = Path("docs/content/mionyee-case-study.md").read_text(encoding="utf-8")
    required_sections = [
        "## Background",
        "## Solution",
        "## Implementation",
        "## Results",
        "## Reuse Validation",
        "## Data Authenticity Statement",
    ]
    for section in required_sections:
        assert section in payload


def test_mionyee_case_study_references_real_data_outputs() -> None:
    payload = Path("docs/content/mionyee-case-study.md").read_text(encoding="utf-8")
    assert "docs/content/mionyee-case-data.md" in payload
    assert "docs/content/mionyee-case-data.json" in payload
    assert "No synthetic values are used" in payload
