"""Knowledge injection for Agent prompts.

This module implements the Knowledge Injector component, which formats
Skills knowledge and injects it into Agent system prompts.
"""

from collections.abc import Callable

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

        for skill_name in skill_names:
            if not isinstance(skill_name, str):
                continue
            normalized_name = skill_name.strip()
            if not normalized_name or normalized_name in seen:
                continue
            seen.add(normalized_name)
            skill = self.skills_loader.get_skill(normalized_name)
            if not skill:
                continue

            # Apply context filter if provided
            if context_filter and not context_filter(skill):
                continue

            # Load full content (lazy loading)
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
