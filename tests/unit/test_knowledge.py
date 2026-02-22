"""Unit tests for Knowledge Injector (Skills knowledge formatting for prompts)."""

import pytest

from owlclaw.capabilities.knowledge import KnowledgeInjector
from owlclaw.capabilities.skills import Skill, SkillsLoader


@pytest.fixture
def skills_loader_with_two(tmp_path):
    """SkillsLoader with two Skills for knowledge tests."""
    for name, desc, body in [
        ("skill-a", "Description A", "# Guide A\nContent A"),
        ("skill-b", "Description B", "# Guide B\nContent B"),
    ]:
        (tmp_path / name).mkdir()
        (tmp_path / name / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: {desc}\n---\n\n{body}",
            encoding="utf-8",
        )
    loader = SkillsLoader(tmp_path)
    loader.scan()
    return loader


@pytest.fixture
def injector(skills_loader_with_two):
    return KnowledgeInjector(skills_loader_with_two)


def test_get_skills_knowledge(injector):
    """get_skills_knowledge() returns Markdown with name, description, and full content."""
    result = injector.get_skills_knowledge(["skill-a", "skill-b"])
    assert "# Available Skills" in result
    assert "Skill: skill-a" in result
    assert "**Description:** Description A" in result
    assert "Content A" in result
    assert "Skill: skill-b" in result
    assert "Content B" in result
    assert "---" in result


def test_get_skills_knowledge_context_filter(injector):
    """get_skills_knowledge() respects context_filter to exclude Skills."""
    def only_a(skill: Skill) -> bool:
        return skill.name == "skill-a"

    result = injector.get_skills_knowledge(["skill-a", "skill-b"], context_filter=only_a)
    assert "skill-a" in result
    assert "Content A" in result
    assert "skill-b" not in result
    assert "Content B" not in result


def test_get_skills_knowledge_empty_skills_list(injector):
    """get_skills_knowledge() with empty skill_names returns empty string."""
    result = injector.get_skills_knowledge([])
    assert result == ""


def test_get_skills_knowledge_unknown_skill_skipped(injector):
    """get_skills_knowledge() skips unknown skill names."""
    result = injector.get_skills_knowledge(["skill-a", "nonexistent", "skill-b"])
    assert "skill-a" in result
    assert "skill-b" in result
    assert "nonexistent" not in result


def test_get_skills_knowledge_deduplicates_skill_names(injector):
    result = injector.get_skills_knowledge(["skill-a", "skill-a", "skill-b"])
    assert result.count("## Skill: skill-a") == 1
    assert result.count("## Skill: skill-b") == 1


def test_get_all_skills_summary(injector):
    """get_all_skills_summary() returns summary with name and description only."""
    result = injector.get_all_skills_summary()
    assert "# Available Skills Summary" in result
    assert "**skill-a**: Description A" in result
    assert "**skill-b**: Description B" in result
    assert "Content A" not in result
    assert "Content B" not in result


def test_get_all_skills_summary_empty(tmp_path):
    """get_all_skills_summary() with no Skills returns 'No Skills available.'"""
    loader = SkillsLoader(tmp_path)
    loader.scan()
    injector = KnowledgeInjector(loader)
    result = injector.get_all_skills_summary()
    assert result == "No Skills available."


def test_get_all_skills_summary_sorted_by_name():
    """Summary ordering should be deterministic by skill name."""

    class _Loader:
        def list_skills(self):  # type: ignore[no-untyped-def]
            return [
                Skill("z-skill", "Z", file_path="z/SKILL.md", metadata={}),
                Skill("a-skill", "A", file_path="a/SKILL.md", metadata={}),
            ]

    injector = KnowledgeInjector(_Loader())  # type: ignore[arg-type]
    result = injector.get_all_skills_summary()
    assert result.index("**a-skill**") < result.index("**z-skill**")
