"""Unit tests for Skills Loader (SKILL.md discovery and parsing)."""


import pytest

from owlclaw.capabilities.skills import SkillsLoader


def test_skills_loader_scan_discovers_skill_md(tmp_path):
    """scan() discovers SKILL.md files and parses valid frontmatter."""
    skill_dir = tmp_path / "entry-monitor"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: entry-monitor
description: Check entry opportunities for held positions
metadata:
  author: team
owlclaw:
  task_type: trading_decision
  constraints:
    trading_hours_only: true
---
# Usage guide
""",
        encoding="utf-8",
    )
    loader = SkillsLoader(tmp_path)
    skills = loader.scan()
    assert len(skills) == 1
    assert skills[0].name == "entry-monitor"
    assert skills[0].description == "Check entry opportunities for held positions"
    assert skills[0].task_type == "trading_decision"
    assert skills[0].constraints.get("trading_hours_only") is True


def test_skills_loader_scan_on_missing_base_path_returns_empty(tmp_path):
    missing = tmp_path / "does-not-exist"
    loader = SkillsLoader(missing)
    assert loader.scan() == []


def test_skills_loader_rejects_invalid_base_path():
    with pytest.raises(ValueError, match="base_path must be a non-empty path"):
        SkillsLoader("   ")
    with pytest.raises(ValueError, match="base_path must be a non-empty path"):
        SkillsLoader(None)  # type: ignore[arg-type]


def test_skills_loader_get_skill(tmp_path):
    """get_skill() returns Skill by name after scan()."""
    skill_dir = tmp_path / "morning-decision"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: morning-decision\ndescription: Morning decision\n---\n",
        encoding="utf-8",
    )
    loader = SkillsLoader(tmp_path)
    loader.scan()
    skill = loader.get_skill("morning-decision")
    assert skill is not None
    assert skill.name == "morning-decision"
    assert loader.get_skill("  morning-decision  ") is not None
    assert loader.get_skill("   ") is None
    assert loader.get_skill(None) is None  # type: ignore[arg-type]
    assert loader.get_skill("nonexistent") is None


def test_skills_loader_list_skills(tmp_path):
    """list_skills() returns all loaded Skills."""
    for name in ("a", "b"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: Skill {name}\n---\n",
            encoding="utf-8",
        )
    loader = SkillsLoader(tmp_path)
    loader.scan()
    skills = loader.list_skills()
    assert len(skills) == 2
    names = {s.name for s in skills}
    assert names == {"a", "b"}


def test_skill_load_full_content_lazy(tmp_path):
    """Skill.load_full_content() loads content after frontmatter (lazy)."""
    skill_dir = tmp_path / "lazy"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: lazy\ndescription: Lazy\n---\n\n# Body content here",
        encoding="utf-8",
    )
    loader = SkillsLoader(tmp_path)
    loader.scan()
    skill = loader.get_skill("lazy")
    assert skill is not None
    content = skill.load_full_content()
    assert "Body content here" in content
    assert "name: lazy" not in content


def test_skill_to_dict(tmp_path):
    """Skill.to_dict() serializes metadata without full content."""
    skill_dir = tmp_path / "dict"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: dict\ndescription: For to_dict\n---\n",
        encoding="utf-8",
    )
    loader = SkillsLoader(tmp_path)
    loader.scan()
    skill = loader.get_skill("dict")
    assert skill is not None
    d = skill.to_dict()
    assert d["name"] == "dict"
    assert d["description"] == "For to_dict"
    assert "file_path" in d
    assert "metadata" in d
    assert "full_content" not in d


def test_skills_loader_parses_focus_and_risk_extensions(tmp_path):
    """owlclaw focus/risk fields should be parsed and exposed by Skill."""
    skill_dir = tmp_path / "risky-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: risky-skill
description: Risky operation
owlclaw:
  focus: [inventory_monitor, trading_decision]
  risk_level: high
---
# Body
""",
        encoding="utf-8",
    )
    loader = SkillsLoader(tmp_path)
    loader.scan()
    skill = loader.get_skill("risky-skill")
    assert skill is not None
    assert skill.focus == ["inventory_monitor", "trading_decision"]
    assert skill.risk_level == "high"
    assert skill.requires_confirmation is True


def test_skills_loader_focus_ignores_non_string_items(tmp_path):
    """focus should only keep non-empty string items."""
    skill_dir = tmp_path / "focus-mixed"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: focus-mixed
description: Focus mixed
owlclaw:
  focus: [valid_tag, 123, null, "  ", another]
---
# Body
""",
        encoding="utf-8",
    )
    loader = SkillsLoader(tmp_path)
    loader.scan()
    skill = loader.get_skill("focus-mixed")
    assert skill is not None
    assert skill.focus == ["valid_tag", "another"]


def test_skill_focus_supports_tuple_and_dedupes():
    from owlclaw.capabilities.skills import Skill

    skill = Skill(
        name="x",
        description="d",
        file_path="SKILL.md",
        metadata={},
        owlclaw_config={"focus": ("a", " a ", "b", "", "b")},
    )
    assert skill.focus == ["a", "b"]


def test_skills_loader_requires_confirmation_accepts_int_literals(tmp_path):
    skill_dir = tmp_path / "confirm-int"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: confirm-int
description: confirm by int
owlclaw:
  risk_level: low
  requires_confirmation: 1
---
# Body
""",
        encoding="utf-8",
    )
    loader = SkillsLoader(tmp_path)
    loader.scan()
    skill = loader.get_skill("confirm-int")
    assert skill is not None
    assert skill.requires_confirmation is True


def test_parse_invalid_yaml_skipped(tmp_path):
    """Invalid YAML in frontmatter is logged and skill is skipped."""
    skill_dir = tmp_path / "bad"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: [unclosed\ndescription: bad\n---\n",
        encoding="utf-8",
    )
    loader = SkillsLoader(tmp_path)
    skills = loader.scan()
    assert len(skills) == 0


def test_parse_missing_required_fields_skipped(tmp_path):
    """Missing name or description is logged and skill is skipped."""
    skill_dir = tmp_path / "nofields"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\nmetadata: {}\n---\n", encoding="utf-8")
    loader = SkillsLoader(tmp_path)
    skills = loader.scan()
    assert len(skills) == 0


def test_parse_non_mapping_frontmatter_skipped(tmp_path):
    """Non-dict YAML frontmatter should be skipped safely."""
    skill_dir = tmp_path / "bad-shape"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\n- bad\n- list\n---\n",
        encoding="utf-8",
    )
    loader = SkillsLoader(tmp_path)
    skills = loader.scan()
    assert len(skills) == 0


def test_parse_name_description_must_be_non_empty_strings(tmp_path):
    """name/description must be non-empty strings."""
    skill_dir = tmp_path / "bad-fields"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: 123\ndescription: \"\"\n---\n",
        encoding="utf-8",
    )
    loader = SkillsLoader(tmp_path)
    skills = loader.scan()
    assert len(skills) == 0


def test_parse_name_must_be_kebab_case(tmp_path):
    """Skill name should follow kebab-case pattern."""
    skill_dir = tmp_path / "bad-name"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: Invalid Name\ndescription: ok\n---\n",
        encoding="utf-8",
    )
    loader = SkillsLoader(tmp_path)
    skills = loader.scan()
    assert len(skills) == 0


def test_parse_skill_with_utf8_bom(tmp_path):
    """UTF-8 BOM at file start should not break frontmatter parsing."""
    skill_dir = tmp_path / "bom"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "\ufeff---\nname: bom-skill\ndescription: has bom\n---\n# Body\n",
        encoding="utf-8",
    )
    loader = SkillsLoader(tmp_path)
    skills = loader.scan()
    assert len(skills) == 1
    assert skills[0].name == "bom-skill"


def test_scan_duplicate_skill_names_keeps_first_sorted_path(tmp_path):
    """Duplicate skill names should not silently overwrite earlier entries."""
    a_dir = tmp_path / "a-skill"
    b_dir = tmp_path / "b-skill"
    a_dir.mkdir()
    b_dir.mkdir()
    (a_dir / "SKILL.md").write_text(
        "---\nname: same\ndescription: first\n---\n",
        encoding="utf-8",
    )
    (b_dir / "SKILL.md").write_text(
        "---\nname: same\ndescription: second\n---\n",
        encoding="utf-8",
    )
    loader = SkillsLoader(tmp_path)
    skills = loader.scan()
    assert len(skills) == 1
    skill = loader.get_skill("same")
    assert skill is not None
    assert skill.description == "first"


def test_skill_exposes_optional_assets_references_and_scripts_dirs(tmp_path):
    skill_dir = tmp_path / "with-dirs"
    skill_dir.mkdir()
    (skill_dir / "references").mkdir()
    (skill_dir / "scripts").mkdir()
    (skill_dir / "assets").mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: with-dirs\ndescription: has optional dirs\n---\n# Body\n",
        encoding="utf-8",
    )
    loader = SkillsLoader(tmp_path)
    loader.scan()
    skill = loader.get_skill("with-dirs")
    assert skill is not None
    assert skill.references_dir == skill_dir / "references"
    assert skill.scripts_dir == skill_dir / "scripts"
    assert skill.assets_dir == skill_dir / "assets"


def test_skills_loader_parses_frontmatter_with_dashes_in_field_values(tmp_path):
    """Frontmatter parser should not break when YAML values contain '---'."""
    skill_dir = tmp_path / "dash-desc"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: dash-desc
description: "strategy --- monitor"
---
# Body
Use this skill.
""",
        encoding="utf-8",
    )
    loader = SkillsLoader(tmp_path)
    skills = loader.scan()
    assert len(skills) == 1
    assert skills[0].description == "strategy --- monitor"


def test_skill_load_full_content_handles_dashes_in_frontmatter_values(tmp_path):
    skill_dir = tmp_path / "dash-body"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: dash-body
description: "a --- b"
---
# Body Heading
Body text
""",
        encoding="utf-8",
    )
    loader = SkillsLoader(tmp_path)
    loader.scan()
    skill = loader.get_skill("dash-body")
    assert skill is not None
    body = skill.load_full_content()
    assert "# Body Heading" in body
    assert "description:" not in body
