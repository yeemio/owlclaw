"""SKILL.md template library — templates, models, and exceptions."""

from pathlib import Path

from owlclaw.templates.skills.exceptions import (
    MissingParameterError,
    ParameterTypeError,
    ParameterValueError,
    TemplateNotFoundError,
    TemplateRenderError,
)
from owlclaw.templates.skills.models import (
    SearchResult,
    TemplateCategory,
    TemplateMetadata,
    TemplateParameter,
    ValidationError,
)
from owlclaw.templates.skills.registry import TemplateRegistry

__all__ = [
    "MissingParameterError",
    "ParameterTypeError",
    "ParameterValueError",
    "SearchResult",
    "TemplateCategory",
    "TemplateMetadata",
    "TemplateNotFoundError",
    "TemplateParameter",
    "TemplateRenderError",
    "TemplateRegistry",
    "ValidationError",
]


def get_default_templates_dir() -> Path:
    """Return the path to the bundled templates directory."""
    return Path(__file__).parent / "templates"
