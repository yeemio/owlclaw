"""Unit tests for owlclaw.templates.skills.registry (skill-templates Task 2)."""

from pathlib import Path

import pytest

from owlclaw.templates.skills import (
    TemplateCategory,
    TemplateRegistry,
)
from owlclaw.templates.skills.exceptions import TemplateNotFoundError
from owlclaw.templates.skills.models import TemplateMetadata


def _templates_dir() -> Path:
    """Resolve templates dir from repo root (tests/unit/templates/skills -> root)."""
    return Path(__file__).resolve().parents[4] / "owlclaw" / "templates" / "skills" / "templates"


class TestTemplateRegistry:
    def test_loads_template_from_directory(self, tmp_path: Path) -> None:
        """Registry loads template from a directory with category subdirs."""
        (tmp_path / "monitoring").mkdir()
        tpl = tmp_path / "monitoring" / "health-check.md.j2"
        tpl.write_text("""{#
name: Health Check Monitor
description: Monitor system health
tags: [monitoring, health]
parameters:
  - name: skill_name
    type: str
    description: Skill name
    required: true
  - name: check_interval
    type: int
    description: Interval in seconds
    default: 60
#}
---
name: test
---
# Test
""", encoding="utf-8")
        reg = TemplateRegistry(tmp_path)
        t = reg.get_template("monitoring/health-check")
        assert t is not None
        assert t.id == "monitoring/health-check"
        assert t.name == "Health Check Monitor"
        assert t.category == TemplateCategory.MONITORING
        assert "monitoring" in t.tags
        assert len(t.parameters) >= 2
        param_names = [p.name for p in t.parameters]
        assert "skill_name" in param_names
        assert "check_interval" in param_names

    def test_loads_bundled_templates(self) -> None:
        """Registry loads health-check from bundled templates (if present)."""
        templates_dir = _templates_dir()
        reg = TemplateRegistry(templates_dir)
        t = reg.get_template("monitoring/health-check")
        if t is None:
            pytest.skip("Bundled templates not found (path or package install)")
        assert t.id == "monitoring/health-check"
        assert t.name == "Health Check Monitor"

    def test_get_template_or_raise(self, tmp_path: Path) -> None:
        (tmp_path / "monitoring").mkdir()
        (tmp_path / "monitoring" / "health-check.md.j2").write_text(
            "{#\nname: X\ndescription: Y\ntags: []\nparameters: []\n#}\n---\n",
            encoding="utf-8",
        )
        reg = TemplateRegistry(tmp_path)
        t = reg.get_template_or_raise("monitoring/health-check")
        assert t.id == "monitoring/health-check"

        with pytest.raises(TemplateNotFoundError):
            reg.get_template_or_raise("nonexistent/template")

    def test_get_template_returns_none_for_missing(self, tmp_path: Path) -> None:
        reg = TemplateRegistry(tmp_path)
        assert reg.get_template("x/y") is None

    def test_list_templates_by_category(self, tmp_path: Path) -> None:
        (tmp_path / "monitoring").mkdir()
        (tmp_path / "monitoring" / "health-check.md.j2").write_text(
            "{#\nname: X\ndescription: Y\ntags: []\nparameters: []\n#}\n---\n",
            encoding="utf-8",
        )
        reg = TemplateRegistry(tmp_path)
        monitoring = reg.list_templates(category=TemplateCategory.MONITORING)
        assert len(monitoring) >= 1
        assert all(t.category == TemplateCategory.MONITORING for t in monitoring)

    def test_list_templates_by_tags(self, tmp_path: Path) -> None:
        (tmp_path / "monitoring").mkdir()
        (tmp_path / "monitoring" / "health-check.md.j2").write_text(
            "{#\nname: X\ndescription: Y\ntags: [health, alert]\nparameters: []\n#}\n---\n",
            encoding="utf-8",
        )
        reg = TemplateRegistry(tmp_path)
        results = reg.list_templates(tags=["health"])
        assert len(results) >= 1
        assert any("health" in t.tags for t in results)

    def test_list_templates_by_tags_is_case_insensitive(self, tmp_path: Path) -> None:
        (tmp_path / "monitoring").mkdir()
        (tmp_path / "monitoring" / "health-check.md.j2").write_text(
            "{#\nname: X\ndescription: Y\ntags: [Health, Alert]\nparameters: []\n#}\n---\n",
            encoding="utf-8",
        )
        reg = TemplateRegistry(tmp_path)
        results = reg.list_templates(tags=["  health  "])
        assert len(results) >= 1

    def test_parse_parameter_required_string_false(self, tmp_path: Path) -> None:
        (tmp_path / "monitoring").mkdir()
        (tmp_path / "monitoring" / "health-check.md.j2").write_text(
            "{#\nname: X\ndescription: Y\ntags: []\nparameters:\n  - name: opt\n    type: str\n    required: \"false\"\n#}\n---\n",
            encoding="utf-8",
        )
        reg = TemplateRegistry(tmp_path)
        tpl = reg.get_template("monitoring/health-check")
        assert tpl is not None
        assert len(tpl.parameters) == 1
        assert tpl.parameters[0].required is False

    def test_parse_parameter_choices_string(self, tmp_path: Path) -> None:
        (tmp_path / "monitoring").mkdir()
        (tmp_path / "monitoring" / "health-check.md.j2").write_text(
            "{#\nname: X\ndescription: Y\ntags: []\nparameters:\n  - name: fmt\n    type: str\n    choices: json, yaml\n#}\n---\n",
            encoding="utf-8",
        )
        reg = TemplateRegistry(tmp_path)
        tpl = reg.get_template("monitoring/health-check")
        assert tpl is not None
        assert len(tpl.parameters) == 1
        assert tpl.parameters[0].choices == ["json", "yaml"]

    def test_skip_empty_and_duplicate_parameter_names(self, tmp_path: Path) -> None:
        (tmp_path / "monitoring").mkdir()
        (tmp_path / "monitoring" / "health-check.md.j2").write_text(
            "{#\nname: X\ndescription: Y\ntags: []\nparameters:\n  - name: \"\"\n    type: str\n  - name: item\n    type: str\n  - name: item\n    type: int\n#}\n---\n",
            encoding="utf-8",
        )
        reg = TemplateRegistry(tmp_path)
        tpl = reg.get_template("monitoring/health-check")
        assert tpl is not None
        assert [p.name for p in tpl.parameters] == ["item"]
        assert tpl.parameters[0].type == "str"

    def test_search_templates(self, tmp_path: Path) -> None:
        (tmp_path / "monitoring").mkdir()
        (tmp_path / "monitoring" / "health-check.md.j2").write_text(
            "{#\nname: Health Monitor\ndescription: Monitor health\ntags: [health]\nparameters: []\n#}\n---\n",
            encoding="utf-8",
        )
        reg = TemplateRegistry(tmp_path)
        results = reg.search_templates("health")
        assert len(results) >= 1

    def test_search_templates_empty_query_returns_empty(self, tmp_path: Path) -> None:
        (tmp_path / "monitoring").mkdir()
        (tmp_path / "monitoring" / "health-check.md.j2").write_text(
            "{#\nname: Health Monitor\ndescription: Monitor health\ntags: [health]\nparameters: []\n#}\n---\n",
            encoding="utf-8",
        )
        reg = TemplateRegistry(tmp_path)
        assert reg.search_templates("") == []
        assert reg.search_templates("   ") == []

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Registry with empty dir has no templates."""
        reg = TemplateRegistry(tmp_path)
        assert reg.get_template("any/id") is None
        assert reg.list_templates() == []
        assert reg.search_templates("x") == []

    def test_duplicate_template_id_keeps_first_loaded(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        (tmp_path / "monitoring").mkdir()
        (tmp_path / "analysis").mkdir()
        first = tmp_path / "monitoring" / "health-check.md.j2"
        second = tmp_path / "analysis" / "trend-detector.md.j2"
        first.write_text("{#\nname: First\ndescription: first\ntags: []\nparameters: []\n#}\n", encoding="utf-8")
        second.write_text("{#\nname: Second\ndescription: second\ntags: []\nparameters: []\n#}\n", encoding="utf-8")

        def _fake_parse(self: TemplateRegistry, template_file: Path, category: TemplateCategory) -> TemplateMetadata:
            if "health-check" in template_file.name:
                return TemplateMetadata(
                    id="monitoring/duplicate",
                    name="First",
                    category=TemplateCategory.MONITORING,
                    description="first",
                    tags=[],
                    parameters=[],
                    examples=[],
                    file_path=template_file,
                )
            return TemplateMetadata(
                id="monitoring/duplicate",
                name="Second",
                category=TemplateCategory.MONITORING,
                description="second",
                tags=[],
                parameters=[],
                examples=[],
                file_path=template_file,
            )

        monkeypatch.setattr(TemplateRegistry, "_parse_template_metadata", _fake_parse)
        reg = TemplateRegistry(tmp_path)
        loaded = reg.get_template("monitoring/duplicate")
        assert loaded is not None
        assert loaded.name == "Second"
