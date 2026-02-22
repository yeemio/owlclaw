"""Skills loading and management for OwlClaw.

This module implements the Skills Loader component, which discovers and loads
SKILL.md files from application directories following the Agent Skills specification.
"""

import logging
import re
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)
_SKILL_NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class Skill:
    """Represents a loaded Skill with metadata and optional full content.

    A Skill is a knowledge document (SKILL.md) that describes a capability's
    purpose, usage guidelines, and relationships with other capabilities.
    Skills follow the Agent Skills open specification (Anthropic, Dec 2025).

    Attributes:
        name: Unique identifier for the Skill
        description: Brief description of what the Skill does
        file_path: Path to the SKILL.md file
        metadata: Agent Skills standard metadata (author, version, tags)
        owlclaw_config: OwlClaw-specific extension fields
    """

    def __init__(
        self,
        name: str,
        description: str,
        file_path: Path,
        metadata: dict,
        owlclaw_config: dict | None = None,
        full_content: str | None = None,
    ):
        self.name = name
        self.description = description
        self.file_path = Path(file_path)
        self.metadata = metadata
        self.owlclaw_config = owlclaw_config or {}
        self._full_content = full_content
        self._is_loaded = full_content is not None

    @property
    def task_type(self) -> str | None:
        """Get the task_type for AI routing (OwlClaw extension)."""
        return self.owlclaw_config.get("task_type")

    @property
    def constraints(self) -> dict:
        """Get the constraints for governance filtering (OwlClaw extension)."""
        return self.owlclaw_config.get("constraints", {})

    @property
    def trigger(self) -> str | None:
        """Get the trigger configuration (OwlClaw extension)."""
        return self.owlclaw_config.get("trigger")

    @property
    def focus(self) -> list[str]:
        """Get focus tags used for runtime skill selection (OwlClaw extension)."""
        raw = self.owlclaw_config.get("focus", [])
        if isinstance(raw, str):
            normalized = raw.strip()
            return [normalized] if normalized else []
        if isinstance(raw, list):
            return [item.strip() for item in raw if isinstance(item, str) and item.strip()]
        return []

    @property
    def risk_level(self) -> str:
        """Get declared risk level (low/medium/high/critical), defaulting to low."""
        raw = self.owlclaw_config.get("risk_level", "low")
        if isinstance(raw, str):
            normalized = raw.strip().lower()
            if normalized in {"low", "medium", "high", "critical"}:
                return normalized
        return "low"

    @property
    def requires_confirmation(self) -> bool:
        """Whether this skill requires human confirmation before execution.

        For compatibility with architecture v4.1:
        - explicit owlclaw.requires_confirmation takes precedence;
        - high/critical risk defaults to True when not explicitly set.
        """
        raw = self.owlclaw_config.get("requires_confirmation")
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, int) and raw in {0, 1}:
            return bool(raw)
        if isinstance(raw, str):
            normalized = raw.strip().lower()
            if normalized in {"1", "true", "yes", "on"}:
                return True
            if normalized in {"0", "false", "no", "off"}:
                return False
        return self.risk_level in {"high", "critical"}

    def load_full_content(self) -> str:
        """Load full instruction text from SKILL.md (lazy loading).

        The full content is loaded only when needed and cached for subsequent
        access. This minimizes memory usage during startup.

        Returns:
            The instruction text (content after frontmatter)
        """
        if not self._is_loaded:
            content = self.file_path.read_text(encoding="utf-8")
            # Extract content after frontmatter (between second and third ---)
            parts = content.split("---", 2)
            if len(parts) >= 3:
                self._full_content = parts[2].strip()
            else:
                self._full_content = ""
            self._is_loaded = True
        return self._full_content

    @property
    def references_dir(self) -> Path | None:
        """Path to references/ directory if it exists.

        The references/ directory contains supporting documentation
        referenced by the Skill (e.g., trading-rules.md).
        """
        ref_dir = self.file_path.parent / "references"
        return ref_dir if ref_dir.exists() else None

    @property
    def scripts_dir(self) -> Path | None:
        """Path to scripts/ directory if it exists.

        The scripts/ directory contains helper scripts used by the Skill
        (e.g., check_signals.py).
        """
        scripts_dir = self.file_path.parent / "scripts"
        return scripts_dir if scripts_dir.exists() else None

    @property
    def assets_dir(self) -> Path | None:
        """Path to assets/ directory if it exists."""
        assets_dir = self.file_path.parent / "assets"
        return assets_dir if assets_dir.exists() else None

    def to_dict(self) -> dict:
        """Serialize metadata to dict (excludes full content).

        Returns:
            Dictionary with Skill metadata suitable for JSON serialization
        """
        return {
            "name": self.name,
            "description": self.description,
            "file_path": str(self.file_path),
            "metadata": self.metadata,
            "task_type": self.task_type,
            "constraints": self.constraints,
            "trigger": self.trigger,
            "focus": self.focus,
            "risk_level": self.risk_level,
            "requires_confirmation": self.requires_confirmation,
        }


class SkillsLoader:
    """Discovers and loads SKILL.md files from application directories.

    At startup only frontmatter metadata is loaded; full instruction text
    is loaded on demand via Skill.load_full_content() (progressive loading).
    """

    def __init__(self, base_path: Path | str):
        self.base_path = Path(base_path)
        self.skills: dict[str, Skill] = {}

    def scan(self) -> list[Skill]:
        """Recursively scan for SKILL.md files and load metadata.

        Returns:
            List of loaded Skill objects. Invalid or missing files are
            logged and skipped.
        """
        self.skills.clear()
        skill_files = sorted(self.base_path.rglob("SKILL.md"))
        for skill_file in skill_files:
            skill = self._parse_skill_file(skill_file)
            if skill is not None:
                if skill.name in self.skills:
                    logger.warning(
                        "Duplicate Skill name '%s' in %s (already loaded from %s); skipping",
                        skill.name,
                        skill_file,
                        self.skills[skill.name].file_path,
                    )
                    continue
                self.skills[skill.name] = skill
        return list(self.skills.values())

    def _parse_skill_file(self, file_path: Path) -> Skill | None:
        """Parse SKILL.md file and extract frontmatter metadata.

        On YAML error, missing required fields, or read error, logs a
        warning and returns None.
        """
        try:
            content = file_path.read_text(encoding="utf-8")
        except OSError as e:
            logger.warning("Failed to read Skill file %s: %s", file_path, e)
            return None
        content = content.lstrip("\ufeff")

        if not content.startswith("---"):
            logger.warning("Skill file %s missing frontmatter", file_path)
            return None

        parts = content.split("---", 2)
        if len(parts) < 3:
            logger.warning("Skill file %s invalid frontmatter format", file_path)
            return None

        try:
            frontmatter = yaml.safe_load(parts[1])
        except yaml.YAMLError as e:
            logger.warning("Skill file %s YAML parse error: %s", file_path, e)
            return None

        if frontmatter is None:
            logger.warning("Skill file %s empty frontmatter", file_path)
            return None
        if not isinstance(frontmatter, dict):
            logger.warning("Skill file %s frontmatter must be a mapping", file_path)
            return None

        if "name" not in frontmatter or "description" not in frontmatter:
            logger.warning(
                "Skill file %s missing required fields (name, description)",
                file_path,
            )
            return None
        if not isinstance(frontmatter["name"], str) or not frontmatter["name"].strip():
            logger.warning("Skill file %s invalid name field", file_path)
            return None
        if not _SKILL_NAME_PATTERN.match(frontmatter["name"].strip()):
            logger.warning("Skill file %s name must be kebab-case", file_path)
            return None
        if not isinstance(frontmatter["description"], str) or not frontmatter["description"].strip():
            logger.warning("Skill file %s invalid description field", file_path)
            return None

        metadata = frontmatter.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
        owlclaw_config = frontmatter.get("owlclaw", {})
        if not isinstance(owlclaw_config, dict):
            owlclaw_config = {}

        return Skill(
            name=frontmatter["name"].strip(),
            description=frontmatter["description"].strip(),
            file_path=file_path,
            metadata=metadata,
            owlclaw_config=owlclaw_config,
            full_content=None,
        )

    def get_skill(self, name: str) -> Skill | None:
        """Retrieve a Skill by name."""
        normalized = name.strip()
        if not normalized:
            return None
        return self.skills.get(normalized)

    def list_skills(self) -> list[Skill]:
        """List all loaded Skills."""
        return list(self.skills.values())
