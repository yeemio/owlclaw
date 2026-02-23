"""Unit tests for FocusManager (Task 6)."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from owlclaw.triggers.cron import FocusManager


@dataclass
class _Skill:
    name: str
    description: str
    focus: list[str]
    metadata: dict


class _SkillsManager:
    def __init__(self, skills: list[_Skill]) -> None:
        self._skills = skills

    def list_skills(self) -> list[_Skill]:
        return self._skills


@pytest.mark.asyncio
async def test_load_skills_for_focus_none_returns_all() -> None:
    skills = [
        _Skill("a", "A", ["inventory_monitor"], {}),
        _Skill("b", "B", ["reporting"], {}),
    ]
    manager = FocusManager(_SkillsManager(skills))
    loaded = await manager.load_skills_for_focus(None)
    assert [s.name for s in loaded] == ["a", "b"]


@pytest.mark.asyncio
async def test_load_skills_for_focus_filters_by_focus() -> None:
    skills = [
        _Skill("a", "A", ["inventory_monitor"], {}),
        _Skill("b", "B", ["reporting"], {}),
    ]
    manager = FocusManager(_SkillsManager(skills))
    loaded = await manager.load_skills_for_focus("inventory_monitor")
    assert [s.name for s in loaded] == ["a"]


def test_skill_matches_focus_uses_metadata_focus() -> None:
    skill = _Skill("a", "A", [], {"focus": ["trading_decision"]})
    manager = FocusManager(_SkillsManager([skill]))
    assert manager._skill_matches_focus(skill, "trading_decision") is True
    assert manager._skill_matches_focus(skill, "reporting") is False


def test_build_agent_prompt_with_and_without_focus() -> None:
    skills = [_Skill("a", "A desc", ["inventory_monitor"], {})]
    manager = FocusManager(_SkillsManager(skills))
    with_focus = manager.build_agent_prompt("inventory_monitor", skills)
    without_focus = manager.build_agent_prompt(None, skills)

    assert "Current focus: inventory_monitor" in with_focus
    assert "prioritize actions related to inventory_monitor" in with_focus
    assert "- a: A desc" in with_focus
    assert "Current focus: none" in without_focus
