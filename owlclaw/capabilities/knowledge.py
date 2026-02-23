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

    def __init__(self, skills_loader: SkillsLoader):
        """Initialize the KnowledgeInjector.

        Args:
            skills_loader: SkillsLoader instance for accessing Skills
        """
        self.skills_loader = skills_loader
        self._default_max_tokens: int | None = None

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Estimate token usage with a lightweight word-count heuristic."""
        if not text:
            return 0
        return len(text.split())

    def load_skills_metadata(self) -> list[dict[str, Any]]:
        """Load and return normalized metadata for all scanned skills."""
        metadata: list[dict[str, Any]] = []
        for skill in sorted(self.skills_loader.list_skills(), key=lambda s: s.name):
            metadata.append(
                {
                    "name": skill.name,
                    "description": skill.description,
                    "task_type": skill.task_type,
                    "constraints": skill.constraints,
                    "trigger": skill.trigger,
                    "focus": skill.focus,
                    "risk_level": skill.risk_level,
                    "requires_confirmation": skill.requires_confirmation,
                }
            )
        return metadata

    def select_skills(
        self,
        skill_names: list[str],
        context_filter: Callable[[Skill], bool] | None = None,
        max_tokens: int | None = None,
    ) -> list[Skill]:
        """Select skills in order with optional filter and token budget."""
        selected: list[Skill] = []
        seen: set[str] = set()
        budget = max_tokens if isinstance(max_tokens, int) and max_tokens > 0 else self._default_max_tokens
        used_tokens = 0

        for skill_name in skill_names:
            if not isinstance(skill_name, str):
                continue
            normalized_name = skill_name.strip().lower()
            if not normalized_name or normalized_name in seen:
                continue
            seen.add(normalized_name)
            skill = self.skills_loader.get_skill(normalized_name)
            if skill is None:
                continue
            if context_filter is not None and not context_filter(skill):
                continue

            if budget is not None:
                estimated = self._estimate_tokens(skill.load_full_content())
                if used_tokens + estimated > budget:
                    continue
                used_tokens += estimated
            selected.append(skill)
        return selected

    def reload_skills(self) -> list[Skill]:
        """Reload skills from disk and clear prior cached full contents."""
        for skill in self.skills_loader.list_skills():
            skill.clear_full_content_cache()
        return self.skills_loader.scan()

    def get_skills_knowledge(
        self,
        skill_names: list[str],
        context_filter: Callable[[Skill], bool] | None = None,
        max_tokens: int | None = None,
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
        knowledge_parts: list[str] = []
        selected_skills = self.select_skills(
            skill_names,
            context_filter=context_filter,
            max_tokens=max_tokens,
        )

        for skill in selected_skills:
            full_content = skill.load_full_content()

            # Format as Markdown section
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
