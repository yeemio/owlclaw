"""Validate OpenClaw tutorial constraints used by openclaw-skill-pack acceptance."""

from __future__ import annotations

import re
from pathlib import Path


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_openclaw_skill_readme_quick_start_has_three_steps() -> None:
    readme = _read(Path(__file__).resolve().parents[2] / "skills" / "owlclaw-for-openclaw" / "README.md")
    section = readme.split("## Quick start", 1)[1]
    numbered = re.findall(r"^\d+\.\s+", section, flags=re.MULTILINE)
    assert len(numbered) == 3, "Quick start must keep <= 3 installation/usage steps"


def test_openclaw_one_command_tutorial_estimated_time_within_ten_minutes() -> None:
    en_doc = _read(Path(__file__).resolve().parents[2] / "docs" / "content" / "openclaw-one-command-en.md")
    zh_doc = _read(Path(__file__).resolve().parents[2] / "docs" / "content" / "openclaw-one-command-zh.md")

    assert "Estimated time: 10 minutes." in en_doc
    assert "预计耗时：10 分钟内。" in zh_doc


def test_openclaw_one_command_tutorial_has_three_steps() -> None:
    en_doc = _read(Path(__file__).resolve().parents[2] / "docs" / "content" / "openclaw-one-command-en.md")
    zh_doc = _read(Path(__file__).resolve().parents[2] / "docs" / "content" / "openclaw-one-command-zh.md")

    en_steps = re.findall(r"^## Step \d+:", en_doc, flags=re.MULTILINE)
    zh_steps = re.findall(r"^## 第[一二三四五六七八九十]+步：", zh_doc, flags=re.MULTILINE)

    assert len(en_steps) == 3
    assert len(zh_steps) == 3
