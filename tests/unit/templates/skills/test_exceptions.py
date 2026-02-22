"""Unit tests for owlclaw.templates.skills.exceptions (skill-templates Task 1)."""

from owlclaw.templates.skills.exceptions import (
    MissingParameterError,
    ParameterTypeError,
    ParameterValueError,
    TemplateError,
    TemplateNotFoundError,
    TemplateRenderError,
)


class TestTemplateExceptions:
    def test_template_not_found_error(self) -> None:
        err = TemplateNotFoundError("monitoring/nonexistent")
        assert "monitoring/nonexistent" in str(err)
        assert isinstance(err, TemplateError)

    def test_missing_parameter_error(self) -> None:
        err = MissingParameterError("skill_name")
        assert "skill_name" in str(err)
        assert isinstance(err, TemplateError)

    def test_parameter_type_error(self) -> None:
        err = ParameterTypeError(
            "check_interval: expected int, got str",
            param_name="check_interval",
            expected="int",
            got="str",
        )
        assert "check_interval" in str(err)
        assert err.expected == "int"
        assert isinstance(err, TemplateError)

    def test_parameter_value_error(self) -> None:
        err = ParameterValueError(
            "format must be one of: json, yaml",
            param_name="format",
            value="invalid",
            choices=["json", "yaml"],
        )
        assert "format" in str(err)
        assert err.choices == ["json", "yaml"]
        assert isinstance(err, TemplateError)

    def test_template_render_error(self) -> None:
        err = TemplateRenderError("Jinja2 syntax error at line 5")
        assert "line 5" in str(err)
        assert isinstance(err, TemplateError)
