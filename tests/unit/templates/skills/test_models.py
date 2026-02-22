"""Unit tests for owlclaw.templates.skills.models (skill-templates Task 1)."""

from pathlib import Path

from owlclaw.templates.skills.models import (
    SearchResult,
    TemplateCategory,
    TemplateMetadata,
    TemplateParameter,
    ValidationError,
)


class TestTemplateCategory:
    def test_enum_values(self) -> None:
        assert TemplateCategory.MONITORING.value == "monitoring"
        assert TemplateCategory.ANALYSIS.value == "analysis"
        assert TemplateCategory.WORKFLOW.value == "workflow"
        assert TemplateCategory.INTEGRATION.value == "integration"
        assert TemplateCategory.REPORT.value == "report"

    def test_from_string(self) -> None:
        assert TemplateCategory("monitoring") == TemplateCategory.MONITORING
        assert TemplateCategory("report") == TemplateCategory.REPORT


class TestTemplateParameter:
    def test_required_param(self) -> None:
        p = TemplateParameter(
            name="skill_name",
            type="str",
            description="Skill display name",
            required=True,
        )
        assert p.name == "skill_name"
        assert p.type == "str"
        assert p.required is True
        assert p.default is None
        assert p.choices is None

    def test_optional_param_with_default(self) -> None:
        p = TemplateParameter(
            name="check_interval",
            type="int",
            description="Interval in seconds",
            required=False,
            default=60,
        )
        assert p.default == 60

    def test_param_with_choices(self) -> None:
        p = TemplateParameter(
            name="format",
            type="str",
            description="Output format",
            required=True,
            choices=["json", "yaml"],
        )
        assert p.choices == ["json", "yaml"]


class TestTemplateMetadata:
    def test_metadata_fields(self) -> None:
        p = TemplateParameter("x", "str", "desc")
        m = TemplateMetadata(
            id="monitoring/health-check",
            name="Health Check",
            category=TemplateCategory.MONITORING,
            description="Monitor system health",
            tags=["monitoring", "health"],
            parameters=[p],
            examples=["Example 1"],
            file_path=Path("/tmp/templates/monitoring/health-check.md.j2"),
        )
        assert m.id == "monitoring/health-check"
        assert m.category == TemplateCategory.MONITORING
        assert len(m.parameters) == 1
        assert m.parameters[0].name == "x"


class TestValidationError:
    def test_validation_error(self) -> None:
        v = ValidationError(field="name", message="Must be kebab-case", severity="error")
        assert v.field == "name"
        assert v.severity == "error"


class TestSearchResult:
    def test_search_result(self) -> None:
        p = TemplateParameter("x", "str", "desc")
        m = TemplateMetadata(
            id="analysis/trend",
            name="Trend Detector",
            category=TemplateCategory.ANALYSIS,
            description="Detect trends",
            tags=[],
            parameters=[p],
            examples=[],
            file_path=Path("/x"),
        )
        r = SearchResult(template=m, score=0.8, match_reason="name match")
        assert r.score == 0.8
        assert r.template.name == "Trend Detector"
