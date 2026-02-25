"""Unit tests for owlclaw.templates.skills.validator (skill-templates Task 5)."""

from pathlib import Path
from tempfile import TemporaryDirectory

from hypothesis import given, settings
from hypothesis import strategies as st

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

    def test_validate_template_invalid_metadata_yaml(self, tmp_path: Path) -> None:
        tpl = tmp_path / "x.md.j2"
        tpl.write_text(
            "{#\nname: X\ndescription: [invalid\n#}\n---\nname: x\n---\n# Title\n",
            encoding="utf-8",
        )
        v = TemplateValidator()
        errs = v.validate_template(tpl)
        assert any(e.field == "metadata" and "Invalid metadata YAML" in e.message for e in errs)

    def test_validate_template_metadata_unrendered_placeholder(self, tmp_path: Path) -> None:
        tpl = tmp_path / "x.md.j2"
        tpl.write_text(
            "{#\nname: \"{{ name }}\"\ndescription: Y\nparameters: []\n#}\n---\nname: x\n---\n# Title\n",
            encoding="utf-8",
        )
        v = TemplateValidator()
        errs = v.validate_template(tpl)
        assert any(e.field == "metadata" and "unrendered Jinja2" in e.message for e in errs)

    def test_validate_template_metadata_missing_required_field(self, tmp_path: Path) -> None:
        tpl = tmp_path / "x.md.j2"
        tpl.write_text(
            "{#\nname: X\ndescription: Y\ntags: []\n#}\n---\nname: x\n---\n# Title\n",
            encoding="utf-8",
        )
        v = TemplateValidator()
        errs = v.validate_template(tpl)
        assert any(e.field == "metadata" and "missing required field: parameters" in e.message for e in errs)

    def test_validate_template_metadata_parameters_must_be_list(self, tmp_path: Path) -> None:
        tpl = tmp_path / "x.md.j2"
        tpl.write_text(
            "{#\nname: X\ndescription: Y\ntags: []\nparameters: bad\n#}\n---\nname: x\n---\n# Title\n",
            encoding="utf-8",
        )
        v = TemplateValidator()
        errs = v.validate_template(tpl)
        assert any(e.field == "metadata.parameters" and "must be a list" in e.message for e in errs)

    def test_validate_template_parameter_item_must_be_mapping(self, tmp_path: Path) -> None:
        tpl = tmp_path / "x.md.j2"
        tpl.write_text(
            "{#\nname: X\ndescription: Y\ntags: []\nparameters: [bad]\n#}\n---\nname: x\n---\n# Title\n",
            encoding="utf-8",
        )
        v = TemplateValidator()
        errs = v.validate_template(tpl)
        assert any(e.field == "metadata.parameters[0]" and "mapping/object" in e.message for e in errs)

    def test_validate_template_parameter_type_must_be_supported(self, tmp_path: Path) -> None:
        tpl = tmp_path / "x.md.j2"
        tpl.write_text(
            "{#\nname: X\ndescription: Y\ntags: []\nparameters:\n  - name: p\n    type: object\n#}\n---\nname: x\n---\n# Title\n",
            encoding="utf-8",
        )
        v = TemplateValidator()
        errs = v.validate_template(tpl)
        assert any(e.field == "metadata.parameters[0].type" and "must be one of" in e.message for e in errs)

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

    def test_validate_skill_file_empty_description(self, tmp_path: Path) -> None:
        skill = tmp_path / "SKILL.md"
        skill.write_text(
            "---\nname: my-skill\ndescription: \"\"\n---\n# Title\n",
            encoding="utf-8",
        )
        v = TemplateValidator()
        errs = v.validate_skill_file(skill)
        assert any(e.field == "description" and "non-empty" in e.message for e in errs)

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
        assert any(e.field == "frontmatter" and "Invalid frontmatter" in e.message for e in errs)

    def test_validate_skill_file_frontmatter_must_be_mapping(self, tmp_path: Path) -> None:
        skill = tmp_path / "SKILL.md"
        skill.write_text(
            "---\n- not\n- mapping\n---\n# Title\n",
            encoding="utf-8",
        )
        v = TemplateValidator()
        errs = v.validate_skill_file(skill)
        assert any(e.field == "frontmatter" and "mapping/object" in e.message for e in errs)

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

    def test_validate_skill_file_with_utf8_bom(self, tmp_path: Path) -> None:
        skill = tmp_path / "SKILL.md"
        skill.write_text(
            "\ufeff---\nname: my-skill\ndescription: A skill\n---\n# Title\n",
            encoding="utf-8",
        )
        v = TemplateValidator()
        errs = v.validate_skill_file(skill)
        assert errs == []

    def test_validate_trigger_syntax(self) -> None:
        v = TemplateValidator()
        assert v._validate_trigger_syntax('cron("*/5 * * * *")') is True
        assert v._validate_trigger_syntax('cron("invalid")') is False
        assert v._validate_trigger_syntax('webhook("/api/event")') is True
        assert v._validate_trigger_syntax('webhook("api/event")') is False
        assert v._validate_trigger_syntax('webhook("/api /event")') is False
        assert v._validate_trigger_syntax('queue("my-queue")') is True
        assert v._validate_trigger_syntax('queue("my queue")') is False
        assert v._validate_trigger_syntax('queue("my/queue")') is False
        assert v._validate_trigger_syntax('queue("")') is False
        assert v._validate_trigger_syntax("invalid") is False

    def test_validate_skill_file_trigger_must_be_string(self, tmp_path: Path) -> None:
        skill = tmp_path / "SKILL.md"
        skill.write_text(
            "---\nname: my-skill\ndescription: ok\nowlclaw:\n  trigger:\n    bad: true\n---\n# Title\n",
            encoding="utf-8",
        )
        v = TemplateValidator()
        errs = v.validate_skill_file(skill)
        assert any(e.field == "owlclaw.trigger" and "must be a string" in e.message for e in errs)

    def test_validate_skill_file_risk_level_invalid(self, tmp_path: Path) -> None:
        skill = tmp_path / "SKILL.md"
        skill.write_text(
            "---\nname: my-skill\ndescription: ok\nowlclaw:\n  risk_level: extreme\n---\n# Title\n",
            encoding="utf-8",
        )
        v = TemplateValidator()
        errs = v.validate_skill_file(skill)
        assert any(e.field == "owlclaw.risk_level" and "must be one of" in e.message for e in errs)

    def test_validate_skill_file_requires_confirmation_bool(self, tmp_path: Path) -> None:
        skill = tmp_path / "SKILL.md"
        skill.write_text(
            "---\nname: my-skill\ndescription: ok\nowlclaw:\n  requires_confirmation: \"yes\"\n---\n# Title\n",
            encoding="utf-8",
        )
        v = TemplateValidator()
        errs = v.validate_skill_file(skill)
        assert any(e.field == "owlclaw.requires_confirmation" and "boolean" in e.message for e in errs)

    def test_validate_skill_file_focus_list_items_non_empty(self, tmp_path: Path) -> None:
        skill = tmp_path / "SKILL.md"
        skill.write_text(
            "---\nname: my-skill\ndescription: ok\nowlclaw:\n  focus: [inventory, \"\"]\n---\n# Title\n",
            encoding="utf-8",
        )
        v = TemplateValidator()
        errs = v.validate_skill_file(skill)
        assert any(e.field == "owlclaw.focus" and "non-empty strings" in e.message for e in errs)

    def test_validate_skill_file_owlclaw_must_be_mapping(self, tmp_path: Path) -> None:
        skill = tmp_path / "SKILL.md"
        skill.write_text(
            "---\nname: my-skill\ndescription: ok\nowlclaw: bad-shape\n---\n# Title\n",
            encoding="utf-8",
        )
        v = TemplateValidator()
        errs = v.validate_skill_file(skill)
        assert any(e.field == "owlclaw" and "mapping/object" in e.message for e in errs)

    def test_validate_skill_file_high_risk_without_confirmation_warns(self, tmp_path: Path) -> None:
        skill = tmp_path / "SKILL.md"
        skill.write_text(
            "---\nname: my-skill\ndescription: ok\nowlclaw:\n  risk_level: high\n  requires_confirmation: false\n---\n# Title\n",
            encoding="utf-8",
        )
        v = TemplateValidator()
        errs = v.validate_skill_file(skill)
        assert any(
            e.field == "owlclaw.requires_confirmation"
            and e.severity == "warning"
            and "should generally require confirmation" in e.message
            for e in errs
        )

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
        assert len(templates) == 16, f"Expected 16 templates, got {len(templates)}"
        v = TemplateValidator()
        for p in templates:
            errs = v.validate_template(p)
            assert errs == [], f"{p.relative_to(base)}: {[e.message for e in errs]}"

    @settings(max_examples=100, deadline=None)
    @given(var_name=st.from_regex(r"[a-z_][a-z0-9_]{0,12}", fullmatch=True))
    def test_property_template_jinja2_syntax_valid(self, var_name: str) -> None:
        with TemporaryDirectory() as tmp_dir:
            tpl = Path(tmp_dir) / "x.md.j2"
            tpl.write_text(
                f"{{#\nname: X\ndescription: Y\ntags: []\nparameters: []\n#}}\n---\nname: x\n---\n# {{{{ {var_name} }}}}\n",
                encoding="utf-8",
            )
            errs = TemplateValidator().validate_template(tpl)
            assert not any(e.field == "syntax" for e in errs)

    @settings(max_examples=100, deadline=None)
    @given(body=st.text(min_size=0, max_size=120))
    def test_property_template_requires_metadata_comment_block(self, body: str) -> None:
        with TemporaryDirectory() as tmp_dir:
            tpl = Path(tmp_dir) / "x.md.j2"
            tpl.write_text(f"---\nname: x\n---\n{body}\n", encoding="utf-8")
            errs = TemplateValidator().validate_template(tpl)
            assert any(e.field == "metadata" and "comment block" in e.message for e in errs)

    @settings(max_examples=100, deadline=None)
    @given(
        name=st.from_regex(r"[a-z0-9]+(?:-[a-z0-9]+)*", fullmatch=True),
        description=st.text(min_size=1, max_size=80).filter(lambda x: bool(x.strip())),
    )
    def test_property_frontmatter_validity(self, name: str, description: str) -> None:
        with TemporaryDirectory() as tmp_dir:
            skill = Path(tmp_dir) / "SKILL.md"
            skill.write_text(
                f"---\nname: {name}\ndescription: {description!r}\n---\n# Title\n\nBody\n",
                encoding="utf-8",
            )
            errs = TemplateValidator().validate_skill_file(skill)
            assert not any(e.field == "frontmatter" for e in errs)

    @settings(max_examples=100, deadline=None)
    @given(valid_name=st.from_regex(r"[a-z0-9]+(?:-[a-z0-9]+)*", fullmatch=True))
    def test_property_name_format_valid_kebab_case(self, valid_name: str) -> None:
        with TemporaryDirectory() as tmp_dir:
            skill = Path(tmp_dir) / "SKILL.md"
            skill.write_text(
                f"---\nname: {valid_name!r}\ndescription: ok\n---\n# Title\n",
                encoding="utf-8",
            )
            errs = TemplateValidator().validate_skill_file(skill)
            assert not any(e.field == "name" and "kebab-case" in e.message for e in errs)

    @settings(max_examples=100, deadline=None)
    @given(invalid_name=st.from_regex(r"[A-Z][A-Za-z0-9 _-]{0,20}", fullmatch=True))
    def test_property_name_format_invalid_non_kebab_case(self, invalid_name: str) -> None:
        with TemporaryDirectory() as tmp_dir:
            skill = Path(tmp_dir) / "SKILL.md"
            skill.write_text(
                f"---\nname: {invalid_name!r}\ndescription: ok\n---\n# Title\n",
                encoding="utf-8",
            )
            errs = TemplateValidator().validate_skill_file(skill)
            assert any(e.field == "name" and "kebab-case" in e.message for e in errs)

    @settings(max_examples=100, deadline=None)
    @given(
        trigger=st.one_of(
            st.sampled_from(
                [
                    'cron("*/5 * * * *")',
                    'cron("0 * * * *")',
                    'cron("0 0 * * *")',
                ]
            ),
            st.from_regex(r'webhook\("/[A-Za-z0-9/_-]{1,40}"\)', fullmatch=True),
            st.from_regex(r'queue\("[A-Za-z0-9][A-Za-z0-9_-]{0,20}"\)', fullmatch=True),
        )
    )
    def test_property_trigger_syntax_valid(self, trigger: str) -> None:
        with TemporaryDirectory() as tmp_dir:
            skill = Path(tmp_dir) / "SKILL.md"
            skill.write_text(
                f"---\nname: my-skill\ndescription: ok\nowlclaw:\n  trigger: {trigger!r}\n---\n# Title\n",
                encoding="utf-8",
            )
            errs = TemplateValidator().validate_skill_file(skill)
            assert not any(e.field == "owlclaw.trigger" and "Invalid trigger syntax" in e.message for e in errs)

    @settings(max_examples=100, deadline=None)
    @given(body=st.text(min_size=1, max_size=120))
    def test_property_body_non_empty_with_heading(self, body: str) -> None:
        with TemporaryDirectory() as tmp_dir:
            skill = Path(tmp_dir) / "SKILL.md"
            skill.write_text(
                f"---\nname: my-skill\ndescription: ok\n---\n# Heading\n\n{body}\n",
                encoding="utf-8",
            )
            errs = TemplateValidator().validate_skill_file(skill)
            assert not any(e.field == "body" and "Body is empty" in e.message for e in errs)

    @settings(max_examples=100, deadline=None)
    @given(name=st.text(min_size=1, max_size=40))
    def test_property_validation_error_messages_are_non_empty(self, name: str) -> None:
        with TemporaryDirectory() as tmp_dir:
            skill = Path(tmp_dir) / "SKILL.md"
            skill.write_text(
                f"---\nname: {name!r}\n---\n\n",
                encoding="utf-8",
            )
            errs = TemplateValidator().validate_skill_file(skill)
            assert errs
            assert all(e.field.strip() for e in errs)
            assert all(e.message.strip() for e in errs)
