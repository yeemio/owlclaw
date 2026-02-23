"""Knowledge injection for Agent prompts.

This module implements the Knowledge Injector component, which formats
Skills knowledge and injects it into Agent system prompts.
"""

from collections.abc import Callable
from typing import Any

from owlclaw.capabilities.skills import Skill, SkillsLoader


class KnowledgeInjector:
    """Formats and injects Skills knowledge into Agent prompts.

    The KnowledgeInjector retrieves Skills knowledge documents and formats
    them as Markdown for inclusion in Agent system prompts. It supports
    context-based filtering to include only relevant Skills.

    Attributes:
        skills_loader: SkillsLoader instance for accessing Skills
    """

    def __init__(self, skills_loader: SkillsLoader, *, token_limit: int = 4000):
        """Initialize the KnowledgeInjector.

        Args:
            skills_loader: SkillsLoader instance for accessing Skills
        """
        if not isinstance(token_limit, int) or token_limit < 1:
            raise ValueError("token_limit must be a positive integer")
        self.skills_loader = skills_loader
        self.token_limit = token_limit

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        if not text or not text.strip():
            return 0
        return len(text.split())

    @staticmethod
    def _matches_focus(skill: Skill, focus: str | None) -> bool:
        if not focus:
            return True
        target = focus.strip().lower()
        if not target:
            return True
        declared_focus = {item.strip().lower() for item in skill.focus if item.strip()}
        if declared_focus:
            return target in declared_focus
        tags = skill.metadata.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]
        if isinstance(tags, list):
            normalized_tags = {str(tag).strip().lower() for tag in tags if str(tag).strip()}
            return target in normalized_tags
        return False

    def load_skills_metadata(self) -> list[dict[str, Any]]:
        """Load metadata summary for all scanned Skills."""
        return [skill.to_dict() for skill in sorted(self.skills_loader.list_skills(), key=lambda s: s.name)]

    def select_skills(
        self,
        skill_names: list[str],
        *,
        focus: str | None = None,
        token_limit: int | None = None,
    ) -> list[str]:
        """Select relevant Skills by focus and token budget."""
        budget = self.token_limit if token_limit is None else max(1, int(token_limit))
        selected: list[str] = []
        seen: set[str] = set()
        used_tokens = 0
        for raw_name in skill_names:
            if not isinstance(raw_name, str):
                continue
            name = raw_name.strip().lower()
            if not name or name in seen:
                continue
            seen.add(name)
            skill = self.skills_loader.get_skill(name)
            if not skill:
                continue
            if not self._matches_focus(skill, focus):
                continue
            content = skill.load_full_content()
            content_tokens = self._estimate_tokens(content)
            if selected and used_tokens + content_tokens > budget:
                continue
            if not selected and content_tokens > budget:
                selected.append(skill.name)
                break
            selected.append(skill.name)
            used_tokens += content_tokens
        return selected

    def reload_skills(self) -> list[Skill]:
        """Reload skills from disk and return refreshed list."""
        return self.skills_loader.scan()

    def get_skills_knowledge(
        self,
        skill_names: list[str],
        context_filter: Callable[[Skill], bool] | None = None
    ) -> str:
        """Retrieve and format Skills knowledge for specified Skills.

        This method loads the full content of specified Skills and formats
        them as Markdown sections. An optional context filter can exclude
        Skills based on runtime context (e.g., trading hours).

        Args:
            skill_names: List of Skill names to include
            context_filter: Optional filter function to exclude Skills
                           based on context (e.g., trading hours)

        Returns:
            Formatted Markdown string with Skills knowledge
        """
        knowledge_parts = []
        seen: set[str] = set()

        selected_names = self.select_skills(skill_names, token_limit=self.token_limit)
        for skill_name in selected_names:
            normalized_name = skill_name.strip().lower()
            if not normalized_name or normalized_name in seen:
                continue
            seen.add(normalized_name)
            skill = self.skills_loader.get_skill(normalized_name)
            if not skill:
                continue
            if context_filter and not context_filter(skill):
                continue
            full_content = skill.load_full_content()
            knowledge_parts.append(
                f"## Skill: {skill.name}\n\n"
                f"**Description:** {skill.description}\n\n"
                f"{full_content}\n"
            )

        if not knowledge_parts:
            return ""

        return (
            "# Available Skills\n\n"
            "The following Skills describe your capabilities and "
            "when to use them:\n\n"
            + "\n---\n\n".join(knowledge_parts)
        )

    def get_all_skills_summary(self) -> str:
        """Get a summary of all Skills (metadata only, no full content).

        This method provides a lightweight overview of available Skills
        without loading their full content. Useful for Agent startup.

        Returns:
            Formatted Markdown summary of all Skills
        """
        skills = self.skills_loader.list_skills()

        if not skills:
            return "No Skills available."

        summary_parts = [
            "# Available Skills Summary\n\n"
            "You have access to the following capabilities:\n"
        ]

        for skill in sorted(skills, key=lambda s: s.name):
            summary_parts.append(
                f"- **{skill.name}**: {skill.description}"
            )

        return "\n".join(summary_parts)
