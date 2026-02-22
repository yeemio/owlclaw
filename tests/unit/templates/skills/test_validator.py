"""Unit tests for owlclaw.templates.skills.validator (skill-templates Task 5)."""

from pathlib import Path

from owlclaw.templates.skills import TemplateValidator


class TestTemplateValidator:
    def test_validate_template_valid(self, tmp_path: Path) -> None:
        tpl = tmp_path / "monitoring" / "x.md.j2"
        tpl.parent.mkdir()
        tpl.write_text(
            "{#\nname: X\ndescription: Y\ntags: []\nparameters: []\n#}\n---\nname: x\n---\n# Title\n",
            encoding="utf-8",
        )
        v = TemplateValidator()
        errs = v.validate_template(tpl)
        assert errs == []

    def test_validate_template_missing_metadata(self, tmp_path: Path) -> None:
        tpl = tmp_path / "x.md.j2"
        tpl.write_text("---\nname: x\n---\n# Title\n", encoding="utf-8")
        v = TemplateValidator()
        errs = v.validate_template(tpl)
        assert len(errs) >= 1
        assert any(e.field == "metadata" for e in errs)

    def test_validate_template_invalid_jinja2(self, tmp_path: Path) -> None:
        tpl = tmp_path / "x.md.j2"
        tpl.write_text("{# x #}\n{{ invalid }}\n{% endif %}\n", encoding="utf-8")
        v = TemplateValidator()
        errs = v.validate_template(tpl)
        assert len(errs) >= 1
        assert any(e.field == "syntax" for e in errs)

    def test_validate_skill_file_valid(self, tmp_path: Path) -> None:
        skill = tmp_path / "SKILL.md"
        skill.write_text(
            "---\nname: my-skill\ndescription: A skill\n---\n# Title\n\nContent\n",
            encoding="utf-8",
        )
        v = TemplateValidator()
        errs = v.validate_skill_file(skill)
        assert errs == []

    def test_validate_skill_file_missing_name(self, tmp_path: Path) -> None:
        skill = tmp_path / "SKILL.md"
        skill.write_text(
            "---\ndescription: Only description\n---\n# Title\n",
            encoding="utf-8",
        )
        v = TemplateValidator()
        errs = v.validate_skill_file(skill)
        assert any(e.field == "name" and "Missing" in e.message for e in errs)

    def test_validate_skill_file_bad_name_format(self, tmp_path: Path) -> None:
        skill = tmp_path / "SKILL.md"
        skill.write_text(
            "---\nname: Invalid Name\ndescription: X\n---\n# Title\n",
            encoding="utf-8",
        )
        v = TemplateValidator()
        errs = v.validate_skill_file(skill)
        assert any(e.field == "name" and "kebab-case" in e.message for e in errs)

    def test_validate_skill_file_empty_body(self, tmp_path: Path) -> None:
        skill = tmp_path / "SKILL.md"
        skill.write_text("---\nname: x\ndescription: y\n---\n\n", encoding="utf-8")
        v = TemplateValidator()
        errs = v.validate_skill_file(skill)
        assert any(e.field == "body" for e in errs)

    def test_validate_skill_file_invalid_frontmatter_yaml(self, tmp_path: Path) -> None:
        skill = tmp_path / "SKILL.md"
        skill.write_text(
            "---\nname: [invalid\ndescription: y\n---\n# Title\n",
            encoding="utf-8",
        )
        v = TemplateValidator()
        errs = v.validate_skill_file(skill)
        assert any(e.field == "frontmatter" and "Invalid YAML" in e.message for e in errs)

    def test_validate_skill_file_unrendered_jinja2_placeholder(self, tmp_path: Path) -> None:
        skill = tmp_path / "SKILL.md"
        skill.write_text(
            "---\nname: x\ndescription: y\n---\n# Title\n\nUse {{ skill_name }}\n",
            encoding="utf-8",
        )
        v = TemplateValidator()
        errs = v.validate_skill_file(skill)
        assert any("unrendered Jinja2 placeholders" in e.message for e in errs)

    def test_validate_skill_file_unrendered_jinja2_in_frontmatter(self, tmp_path: Path) -> None:
        skill = tmp_path / "SKILL.md"
        skill.write_text(
            "---\nname: my-skill\ndescription: \"{{ skill_description }}\"\n---\n# Title\n",
            encoding="utf-8",
        )
        v = TemplateValidator()
        errs = v.validate_skill_file(skill)
        assert any(e.field == "frontmatter" and "unrendered Jinja2" in e.message for e in errs)

    def test_parse_frontmatter_without_trailing_newline_after_delimiter(self, tmp_path: Path) -> None:
        skill = tmp_path / "SKILL.md"
        skill.write_text(
            "---\nname: my-skill\ndescription: A skill\n---",
            encoding="utf-8",
        )
        v = TemplateValidator()
        errs = v.validate_skill_file(skill)
        assert any(e.field == "body" and "Body is empty" in e.message for e in errs)
        assert not any(e.field == "name" and "Missing required field" in e.message for e in errs)

    def test_validate_trigger_syntax(self) -> None:
        v = TemplateValidator()
        assert v._validate_trigger_syntax('cron("*/5 * * * *")') is True
        assert v._validate_trigger_syntax('webhook("/api/event")') is True
        assert v._validate_trigger_syntax('queue("my-queue")') is True
        assert v._validate_trigger_syntax("invalid") is False

    def test_validate_and_report(self, tmp_path: Path) -> None:
        skill = tmp_path / "SKILL.md"
        skill.write_text("---\n---\n", encoding="utf-8")
        v = TemplateValidator()
        report = v.validate_and_report(skill_path=skill)
        assert "Validation report:" in report
        assert "error" in report.lower()

    def test_all_shipped_templates_valid(self) -> None:
        """Task 13 checkpoint: all 15 shipped templates must validate."""
        base = Path(__file__).resolve().parents[4] / "owlclaw" / "templates" / "skills" / "templates"
        templates = sorted(base.rglob("*.md.j2"))
        assert len(templates) == 15, f"Expected 15 templates, got {len(templates)}"
        v = TemplateValidator()
        for p in templates:
            errs = v.validate_template(p)
            assert errs == [], f"{p.relative_to(base)}: {[e.message for e in errs]}"
