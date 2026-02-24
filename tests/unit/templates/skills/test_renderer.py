"""Unit tests for owlclaw.templates.skills.renderer (skill-templates Task 3)."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
import yaml
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from owlclaw.templates.skills import TemplateRegistry, TemplateRenderer
from owlclaw.templates.skills.exceptions import (
    MissingParameterError,
    ParameterTypeError,
    ParameterValueError,
    TemplateRenderError,
)


def _make_registry(tmp_path: Path, content: str) -> TemplateRegistry:
    (tmp_path / "monitoring").mkdir()
    (tmp_path / "monitoring" / "health-check.md.j2").write_text(content, encoding="utf-8")
    return TemplateRegistry(tmp_path)


def _build_renderer_template(
    *,
    parameters: list[dict[str, object]],
    body_lines: list[str],
) -> str:
    metadata = {
        "name": "Health Check",
        "description": "Monitor health",
        "tags": [],
        "parameters": parameters,
    }
    metadata_yaml = yaml.safe_dump(metadata, sort_keys=False, allow_unicode=False).strip()
    body = "\n".join(body_lines)
    return f"{{#\n{metadata_yaml}\n#}}\n---\nname: test\n---\n{body}\n"


class TestTemplateRenderer:
    def test_render_basic(self, tmp_path: Path) -> None:
        content = """{#
name: Health Check
description: Monitor health
tags: []
parameters:
  - name: skill_name
    type: str
    description: Name
    required: true
#}
---
name: {{ skill_name }}
---
# {{ skill_name }}
"""
        reg = _make_registry(tmp_path, content)
        rdr = TemplateRenderer(reg)
        out = rdr.render("monitoring/health-check", {"skill_name": "my-skill"})
        assert "name: my-skill" in out
        assert "# my-skill" in out

    def test_render_missing_required_param(self, tmp_path: Path) -> None:
        content = """{#
name: X
description: Y
tags: []
parameters:
  - name: skill_name
    type: str
    description: Required
    required: true
#}
---
name: {{ skill_name }}
---
"""
        reg = _make_registry(tmp_path, content)
        rdr = TemplateRenderer(reg)
        with pytest.raises(MissingParameterError):
            rdr.render("monitoring/health-check", {})

    def test_render_applies_default(self, tmp_path: Path) -> None:
        content = """{#
name: X
description: Y
tags: []
parameters:
  - name: skill_name
    type: str
    description: Name
    required: true
  - name: interval
    type: int
    description: Interval
    required: false
    default: 60
#}
---
name: {{ skill_name }}
interval: {{ interval }}
---
"""
        reg = _make_registry(tmp_path, content)
        rdr = TemplateRenderer(reg)
        out = rdr.render("monitoring/health-check", {"skill_name": "test"})
        assert "interval: 60" in out

    def test_render_validates_choices(self, tmp_path: Path) -> None:
        content = """{#
name: X
description: Y
tags: []
parameters:
  - name: format
    type: str
    description: Format
    required: true
    choices: [json, yaml]
#}
---
format: {{ format }}
---
"""
        reg = _make_registry(tmp_path, content)
        rdr = TemplateRenderer(reg)
        with pytest.raises(ParameterValueError):
            rdr.render("monitoring/health-check", {"format": "xml"})
        out = rdr.render("monitoring/health-check", {"format": "json"})
        assert "format: json" in out

    def test_render_validates_choices_case_insensitively_for_strings(self, tmp_path: Path) -> None:
        content = """{#
name: X
description: Y
tags: []
parameters:
  - name: format
    type: str
    description: Format
    required: true
    choices: [json, yaml]
#}
---
format: {{ format }}
---
"""
        reg = _make_registry(tmp_path, content)
        rdr = TemplateRenderer(reg)
        out = rdr.render("monitoring/health-check", {"format": "JSON"})
        assert "format: json" in out

    def test_kebab_case_filter(self, tmp_path: Path) -> None:
        content = """{#
name: X
description: Y
tags: []
parameters:
  - name: skill_name
    type: str
    description: Name
    required: true
#}
---
name: {{ skill_name | kebab_case }}
---
"""
        reg = _make_registry(tmp_path, content)
        rdr = TemplateRenderer(reg)
        out = rdr.render("monitoring/health-check", {"skill_name": "My Health Check"})
        assert "name: my-health-check" in out

    def test_snake_case_filter(self, tmp_path: Path) -> None:
        content = """{#
name: X
description: Y
tags: []
parameters:
  - name: var
    type: str
    description: Var
    required: true
#}
---
{{ var | snake_case }}
---
"""
        reg = _make_registry(tmp_path, content)
        rdr = TemplateRenderer(reg)
        out = rdr.render("monitoring/health-check", {"var": "Health Check"})
        assert "health_check" in out

    def test_render_converts_bool_literals(self, tmp_path: Path) -> None:
        content = """{#
name: X
description: Y
tags: []
parameters:
  - name: enabled
    type: bool
    description: Enabled flag
    required: true
#}
---
enabled: {{ enabled }}
---
"""
        reg = _make_registry(tmp_path, content)
        rdr = TemplateRenderer(reg)
        out_true = rdr.render("monitoring/health-check", {"enabled": "true"})
        out_false = rdr.render("monitoring/health-check", {"enabled": "off"})
        assert "enabled: True" in out_true
        assert "enabled: False" in out_false

    def test_render_converts_bool_int_literals(self, tmp_path: Path) -> None:
        content = """{#
name: X
description: Y
tags: []
parameters:
  - name: enabled
    type: bool
    description: Enabled flag
    required: true
#}
---
enabled: {{ enabled }}
---
"""
        reg = _make_registry(tmp_path, content)
        rdr = TemplateRenderer(reg)
        out_true = rdr.render("monitoring/health-check", {"enabled": 1})
        out_false = rdr.render("monitoring/health-check", {"enabled": 0})
        assert "enabled: True" in out_true
        assert "enabled: False" in out_false

    def test_render_rejects_invalid_bool_literal(self, tmp_path: Path) -> None:
        content = """{#
name: X
description: Y
tags: []
parameters:
  - name: enabled
    type: bool
    description: Enabled flag
    required: true
#}
---
enabled: {{ enabled }}
---
"""
        reg = _make_registry(tmp_path, content)
        rdr = TemplateRenderer(reg)
        with pytest.raises(ParameterTypeError):
            rdr.render("monitoring/health-check", {"enabled": "maybe"})

    def test_render_rejects_bool_for_int_parameter(self, tmp_path: Path) -> None:
        content = """{#
name: X
description: Y
tags: []
parameters:
  - name: interval
    type: int
    description: Interval
    required: true
#}
---
interval: {{ interval }}
---
"""
        reg = _make_registry(tmp_path, content)
        rdr = TemplateRenderer(reg)
        with pytest.raises(ParameterTypeError):
            rdr.render("monitoring/health-check", {"interval": True})

    def test_render_converts_csv_string_to_list(self, tmp_path: Path) -> None:
        content = """{#
name: X
description: Y
tags: []
parameters:
  - name: items
    type: list
    description: Items
    required: true
#}
---
items: {{ items|join(',') }}
---
"""
        reg = _make_registry(tmp_path, content)
        rdr = TemplateRenderer(reg)
        out = rdr.render("monitoring/health-check", {"items": "a, b, c"})
        assert "items: a,b,c" in out

    def test_render_keeps_list_parameter_as_list(self, tmp_path: Path) -> None:
        content = """{#
name: X
description: Y
tags: []
parameters:
  - name: items
    type: list
    description: Items
    required: true
#}
---
items: {{ items|join(',') }}
---
"""
        reg = _make_registry(tmp_path, content)
        rdr = TemplateRenderer(reg)
        out = rdr.render("monitoring/health-check", {"items": ["x", "y"]})
        assert "items: x,y" in out

    def test_render_parses_json_like_list_string(self, tmp_path: Path) -> None:
        content = """{#
name: X
description: Y
tags: []
parameters:
  - name: items
    type: list
    description: Items
    required: true
#}
---
items: {{ items|join(',') }}
---
"""
        reg = _make_registry(tmp_path, content)
        rdr = TemplateRenderer(reg)
        out = rdr.render("monitoring/health-check", {"items": "[a, b, c]"})
        assert "items: a,b,c" in out

    def test_render_rejects_unknown_parameters(self, tmp_path: Path) -> None:
        content = """{#
name: X
description: Y
tags: []
parameters:
  - name: skill_name
    type: str
    description: Name
    required: true
#}
---
name: {{ skill_name }}
---
"""
        reg = _make_registry(tmp_path, content)
        rdr = TemplateRenderer(reg)
        with pytest.raises(ParameterValueError, match="Unknown template parameters"):
            rdr.render("monitoring/health-check", {"skill_name": "ok", "unexpected": "x"})

    def test_render_fails_for_undeclared_template_variable(self, tmp_path: Path) -> None:
        content = """{#
name: X
description: Y
tags: []
parameters:
  - name: skill_name
    type: str
    description: Name
    required: true
#}
---
name: {{ skill_name }}
owner: {{ owner }}
---
"""
        reg = _make_registry(tmp_path, content)
        rdr = TemplateRenderer(reg)
        with pytest.raises(TemplateRenderError):
            rdr.render("monitoring/health-check", {"skill_name": "ok"})

    @settings(max_examples=100, deadline=None)
    @given(required_names=st.lists(st.from_regex(r"[a-z][a-z0-9_]{0,12}", fullmatch=True), min_size=1, max_size=6, unique=True))
    def test_property_required_parameters_validation(self, required_names: list[str]) -> None:
        parameters = [
            {"name": name, "type": "str", "description": "required", "required": True}
            for name in required_names
        ]
        body_lines = [f"{name}: {{{{ {name} }}}}" for name in required_names]

        with TemporaryDirectory() as tmp_dir:
            reg = _make_registry(
                Path(tmp_dir),
                _build_renderer_template(parameters=parameters, body_lines=body_lines),
            )
            rdr = TemplateRenderer(reg)
            with pytest.raises(MissingParameterError) as exc_info:
                rdr.render("monitoring/health-check", {})
            assert set(exc_info.value.missing) == set(required_names)

    @settings(max_examples=100, deadline=None)
    @given(default_value=st.integers(min_value=1, max_value=10_000))
    def test_property_default_parameter_application(self, default_value: int) -> None:
        parameters = [
            {"name": "skill_name", "type": "str", "description": "name", "required": True},
            {"name": "interval", "type": "int", "description": "interval", "required": False, "default": default_value},
        ]

        with TemporaryDirectory() as tmp_dir:
            reg = _make_registry(
                Path(tmp_dir),
                _build_renderer_template(
                    parameters=parameters,
                    body_lines=["name: {{ skill_name }}", "interval: {{ interval }}"],
                ),
            )
            rdr = TemplateRenderer(reg)
            out = rdr.render("monitoring/health-check", {"skill_name": "demo"})
            assert f"interval: {default_value}" in out

    @settings(max_examples=100, deadline=None)
    @given(
        param_type=st.sampled_from(["int", "bool"]),
        invalid_bool_literal=st.text(min_size=1, max_size=10).filter(
            lambda s: s.strip().lower() not in {"1", "0", "true", "false", "yes", "no", "on", "off"}
        ),
    )
    def test_property_parameter_type_validation(self, param_type: str, invalid_bool_literal: str) -> None:
        parameters = [{"name": "value", "type": param_type, "description": "value", "required": True}]
        invalid_value: object = True if param_type == "int" else invalid_bool_literal

        with TemporaryDirectory() as tmp_dir:
            reg = _make_registry(
                Path(tmp_dir),
                _build_renderer_template(parameters=parameters, body_lines=["value: {{ value }}"]),
            )
            rdr = TemplateRenderer(reg)
            with pytest.raises(ParameterTypeError) as exc_info:
                rdr.render("monitoring/health-check", {"value": invalid_value})
            assert exc_info.value.param_name == "value"
            assert exc_info.value.expected == param_type

    @settings(max_examples=100, deadline=None)
    @given(
        choices=st.lists(st.from_regex(r"[a-z][a-z0-9_-]{0,10}", fullmatch=True), min_size=1, max_size=8, unique=True),
        invalid_value=st.from_regex(r"[a-z][a-z0-9_-]{0,10}", fullmatch=True),
    )
    def test_property_parameter_choice_validation(self, choices: list[str], invalid_value: str) -> None:
        assume(invalid_value not in choices)

        parameters = [
            {"name": "format", "type": "str", "description": "format", "required": True, "choices": choices}
        ]

        with TemporaryDirectory() as tmp_dir:
            reg = _make_registry(
                Path(tmp_dir),
                _build_renderer_template(parameters=parameters, body_lines=["format: {{ format }}"]),
            )
            rdr = TemplateRenderer(reg)
            with pytest.raises(ParameterValueError) as exc_info:
                rdr.render("monitoring/health-check", {"format": invalid_value})
            assert exc_info.value.param_name == "format"
