"""Validation tests for the mionyee trading example package."""

from __future__ import annotations

import ast
from pathlib import Path

from owlclaw.capabilities.skills import SkillsLoader


def test_mionyee_example_structure_is_complete() -> None:
    base = Path("examples/mionyee-trading")
    assert (base / "app.py").exists()
    assert (base / "README.md").exists()
    assert (base / "docs" / "SOUL.md").exists()
    assert (base / "docs" / "IDENTITY.md").exists()


def test_mionyee_example_skills_are_loadable() -> None:
    skills_root = Path("examples/mionyee-trading/skills")
    skills = SkillsLoader(skills_root).scan()
    names = {skill.name for skill in skills}
    assert names == {"entry-monitor", "morning-decision", "knowledge-feedback"}


def test_mionyee_app_script_is_valid_python() -> None:
    app_path = Path("examples/mionyee-trading/app.py")
    source = app_path.read_text(encoding="utf-8")
    ast.parse(source)
