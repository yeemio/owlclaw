"""Template validator — validates .md.j2 templates and generated SKILL.md files."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)
from jinja2 import Environment

from owlclaw.templates.skills.models import ValidationError

# Pattern for metadata comment block
_METADATA_BLOCK = re.compile(r"\{#.*?#\}", re.DOTALL)

# Supported trigger patterns: cron("..."), webhook("..."), queue("...")
_TRIGGER_PATTERNS = [
    re.compile(r'^cron\(".*?"\)$'),
    re.compile(r'^webhook\(".*?"\)$'),
    re.compile(r'^queue\(".*?"\)$'),
]


class TemplateValidator:
    """Validates .md.j2 template files and generated SKILL.md files."""

    def validate_template(self, template_path: Path) -> list[ValidationError]:
        """Validate a template file.

        Args:
            template_path: Path to the .md.j2 template file.

        Returns:
            List of validation errors (empty if valid).
        """
        errors: list[ValidationError] = []
        try:
            content = template_path.read_text(encoding="utf-8")
        except OSError as e:
            logger.warning("Cannot read template file: path=%s, error=%s", template_path, e)
            errors.append(
                ValidationError(
                    field="file",
                    message=f"Cannot read file: {e}",
                    severity="error",
                )
            )
            return errors

        if not _METADATA_BLOCK.search(content):
            errors.append(
                ValidationError(
                    field="metadata",
                    message="Template missing metadata comment block {# ... #}",
                    severity="error",
                )
            )

        try:
            env = Environment()
            env.parse(content)
        except Exception as e:
            logger.debug("Invalid Jinja2 syntax in %s: %s", template_path, e)
            errors.append(
                ValidationError(
                    field="syntax",
                    message=f"Invalid Jinja2 syntax: {e}",
                    severity="error",
                )
            )

        return errors

    def validate_skill_file(self, skill_path: Path) -> list[ValidationError]:
        """Validate a generated SKILL.md file.

        Args:
            skill_path: Path to the SKILL.md file.

        Returns:
            List of validation errors (empty if valid).
        """
        errors: list[ValidationError] = []
        try:
            content = skill_path.read_text(encoding="utf-8")
        except OSError as e:
            logger.warning("Cannot read skill file: path=%s, error=%s", skill_path, e)
            errors.append(
                ValidationError(
                    field="file",
                    message=f"Cannot read file: {e}",
                    severity="error",
                )
            )
            return errors

        frontmatter, body = self._parse_skill_file(content)
        errors.extend(self._validate_frontmatter(frontmatter))
        errors.extend(self._validate_body(body))
        return errors

    def _parse_skill_file(self, content: str) -> tuple[dict[str, Any], str]:
        """Parse SKILL.md content into frontmatter dict and body string."""
        match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n(.*)$", content, re.DOTALL)
        if not match:
            return {}, content

        frontmatter_str, body = match.groups()
        frontmatter: dict[str, Any] = {}
        if frontmatter_str.strip():
            loaded = yaml.safe_load(frontmatter_str)
            if isinstance(loaded, dict):
                frontmatter = loaded
        return frontmatter, body

    def _validate_frontmatter(self, frontmatter: dict[str, Any]) -> list[ValidationError]:
        """Validate frontmatter fields."""
        errors: list[ValidationError] = []
        required_fields = ["name", "description"]
        for field in required_fields:
            if field not in frontmatter:
                errors.append(
                    ValidationError(
                        field=field,
                        message=f"Missing required field: {field}",
                        severity="error",
                    )
                )

        if "name" in frontmatter:
            name = frontmatter["name"]
            if not isinstance(name, str) or not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name):
                errors.append(
                    ValidationError(
                        field="name",
                        message=f"Name must be in kebab-case format: {name!r}",
                        severity="error",
                    )
                )

        if "owlclaw" in frontmatter:
            owlclaw = frontmatter["owlclaw"]
            if isinstance(owlclaw, dict):
                if "spec_version" not in owlclaw:
                    errors.append(
                        ValidationError(
                            field="owlclaw.spec_version",
                            message="Missing owlclaw.spec_version",
                            severity="warning",
                        )
                    )
                if "trigger" in owlclaw:
                    trigger = owlclaw["trigger"]
                    if isinstance(trigger, str) and not self._validate_trigger_syntax(trigger):
                        errors.append(
                            ValidationError(
                                field="owlclaw.trigger",
                                message=f"Invalid trigger syntax: {trigger!r}",
                                severity="error",
                            )
                        )

        return errors

    def _validate_body(self, body: str) -> list[ValidationError]:
        """Validate Markdown body."""
        errors: list[ValidationError] = []
        if not body.strip():
            errors.append(
                ValidationError(
                    field="body",
                    message="Body is empty",
                    severity="error",
                )
            )
        elif not re.search(r"^#+\s+", body, re.MULTILINE):
            errors.append(
                ValidationError(
                    field="body",
                    message="Body should contain at least one heading",
                    severity="warning",
                )
            )
        return errors

    def _validate_trigger_syntax(self, trigger: str) -> bool:
        """Check if trigger matches supported syntax (cron/webhook/queue)."""
        return any(p.match(trigger) for p in _TRIGGER_PATTERNS)

    def validate_and_report(
        self,
        template_path: Path | None = None,
        skill_path: Path | None = None,
    ) -> str:
        """Validate and return a human-readable error report.

        Args:
            template_path: Optional path to .md.j2 template.
            skill_path: Optional path to SKILL.md file.

        Returns:
            Report string (empty if no errors).
        """
        errors: list[ValidationError] = []
        if template_path:
            errors.extend(self.validate_template(template_path))
        if skill_path:
            errors.extend(self.validate_skill_file(skill_path))

        if not errors:
            return ""

        lines = ["Validation report:"]
        for e in errors:
            lines.append(f"  [{e.severity}] {e.field}: {e.message}")
        return "\n".join(lines)
