"""Validate owlclaw-for-openclaw skill package assets."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

_FRONTMATTER_PATTERN = re.compile(r"^---\r?\n(.*?)\r?\n---", re.DOTALL)


def _load_frontmatter(skill_path: Path) -> dict[str, Any]:
    content = skill_path.read_text(encoding="utf-8")
    match = _FRONTMATTER_PATTERN.match(content)
    assert match is not None, "SKILL.md must contain frontmatter block"
    payload = yaml.safe_load(match.group(1))
    assert isinstance(payload, dict), "frontmatter must be a mapping"
    return payload


def test_openclaw_skill_package_structure() -> None:
    root = Path(__file__).resolve().parents[2] / "skills" / "owlclaw-for-openclaw"
    required_paths = [
        root / "SKILL.md",
        root / "README.md",
        root / "skills" / "governance.md",
        root / "skills" / "persistent-tasks.md",
        root / "skills" / "business-connect.md",
        root / "examples" / "budget-control.md",
        root / "examples" / "background-task.md",
        root / "examples" / "database-connect.md",
        root / "config" / "owlclaw.example.json",
    ]
    for target in required_paths:
        assert target.exists(), f"missing skill package asset: {target}"


def test_openclaw_skill_frontmatter_has_mcp_binding() -> None:
    skill_file = Path(__file__).resolve().parents[2] / "skills" / "owlclaw-for-openclaw" / "SKILL.md"
    frontmatter = _load_frontmatter(skill_file)

    assert frontmatter["name"] == "owlclaw-for-openclaw"
    assert isinstance(frontmatter.get("description"), str) and frontmatter["description"]

    owlclaw = frontmatter.get("owlclaw")
    assert isinstance(owlclaw, dict)
    binding = owlclaw.get("binding")
    assert isinstance(binding, dict)
    assert binding.get("type") == "mcp"
    assert binding.get("endpoint") == "${OWLCLAW_MCP_ENDPOINT}"
