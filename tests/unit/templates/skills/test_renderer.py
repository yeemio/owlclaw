"""Unit tests for owlclaw.templates.skills.renderer (skill-templates Task 3)."""

from pathlib import Path

import pytest

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
