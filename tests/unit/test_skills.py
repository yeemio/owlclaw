"""Unit tests for Skills Loader (SKILL.md discovery and parsing)."""


from pathlib import Path

import pytest

from owlclaw.capabilities.skills import SkillsLoader, SkillsWatcher


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


def test_skills_loader_clear_all_full_content_cache(tmp_path):
    """clear_all_full_content_cache() clears cached content for all loaded skills."""
    for name in ("alpha", "beta"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: Skill {name}\n---\n\n# Body {name}",
            encoding="utf-8",
        )

    loader = SkillsLoader(tmp_path)
    loader.scan()
    for skill in loader.list_skills():
        assert skill.load_full_content()

    cleared = loader.clear_all_full_content_cache()
    assert cleared == 2

    for skill in loader.list_skills():
        # After clearing cache, content should still be retrievable via reload.
        assert f"# Body {skill.name}" in skill.load_full_content()


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
    assert d["parse_mode"] == "natural_language"
    assert isinstance(d["trigger_config"], dict)
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
    assert skill.parse_mode == "structured"


def test_skills_loader_parses_top_level_industry_and_tags(tmp_path):
    skill_dir = tmp_path / "inventory-monitor"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: inventory-monitor
description: Monitor inventory threshold
industry: retail
tags: [inventory, alert]
---
# Body
""",
        encoding="utf-8",
    )
    loader = SkillsLoader(tmp_path)
    loader.scan()
    skill = loader.get_skill("inventory-monitor")
    assert skill is not None
    assert skill.metadata.get("industry") == "retail"
    assert skill.metadata.get("tags") == ["inventory", "alert"]


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
        file_path=Path("SKILL.md"),
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


def test_scan_duplicate_skill_names_workspace_overrides_bundled(tmp_path):
    bundled_dir = tmp_path / "bundled" / "skill"
    workspace_dir = tmp_path / "workspace" / "skill"
    bundled_dir.mkdir(parents=True)
    workspace_dir.mkdir(parents=True)
    (bundled_dir / "SKILL.md").write_text(
        "---\nname: same\ndescription: bundled\n---\n",
        encoding="utf-8",
    )
    (workspace_dir / "SKILL.md").write_text(
        "---\nname: same\ndescription: workspace\n---\n",
        encoding="utf-8",
    )
    loader = SkillsLoader(tmp_path)
    loader.scan()
    skill = loader.get_skill("same")
    assert skill is not None
    assert skill.description == "workspace"


def test_scan_duplicate_skill_names_managed_overrides_bundled(tmp_path):
    bundled_dir = tmp_path / "bundled" / "skill"
    managed_dir = tmp_path / "managed" / "skill"
    bundled_dir.mkdir(parents=True)
    managed_dir.mkdir(parents=True)
    (bundled_dir / "SKILL.md").write_text(
        "---\nname: same\ndescription: bundled\n---\n",
        encoding="utf-8",
    )
    (managed_dir / "SKILL.md").write_text(
        "---\nname: same\ndescription: managed\n---\n",
        encoding="utf-8",
    )
    loader = SkillsLoader(tmp_path)
    loader.scan()
    skill = loader.get_skill("same")
    assert skill is not None
    assert skill.description == "managed"


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


def test_skills_loader_normalizes_top_level_tools_simplified_parameters(tmp_path):
    skill_dir = tmp_path / "tools-simple"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: tools-simple
description: tools simplified syntax
tools:
  fetch-order:
    description: fetch order by id
    order_id: string
    include_items:
      type: boolean
      description: include line items
---
# Body
""",
        encoding="utf-8",
    )
    loader = SkillsLoader(tmp_path)
    loader.scan()
    skill = loader.get_skill("tools-simple")
    assert skill is not None
    tools_schema = skill.metadata.get("tools_schema", {})
    assert "fetch-order" in tools_schema
    params = tools_schema["fetch-order"]["parameters"]
    assert params["type"] == "object"
    assert params["properties"]["order_id"]["type"] == "string"
    assert params["properties"]["include_items"]["type"] == "boolean"
    assert set(params["required"]) == {"order_id", "include_items"}


def test_skills_loader_tools_schema_full_schema_precedence(tmp_path):
    skill_dir = tmp_path / "tools-precedence"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: tools-precedence
description: full schema should win
tools:
  check-stock:
    parameters:
      type: object
      properties:
        sku:
          type: string
      required: [sku]
    warehouse_id: string
---
# Body
""",
        encoding="utf-8",
    )
    loader = SkillsLoader(tmp_path)
    loader.scan()
    skill = loader.get_skill("tools-precedence")
    assert skill is not None
    params = skill.metadata["tools_schema"]["check-stock"]["parameters"]
    assert params["properties"] == {"sku": {"type": "string"}}
    assert params["required"] == ["sku"]


def test_skills_watcher_poll_once_reload_and_callback(tmp_path):
    skill_a = tmp_path / "a"
    skill_a.mkdir()
    (skill_a / "SKILL.md").write_text(
        "---\nname: a\ndescription: A\n---\n# Body\n",
        encoding="utf-8",
    )
    loader = SkillsLoader(tmp_path)
    loader.scan()
    watcher = SkillsWatcher(loader, debounce_seconds=0.0)
    observed: list[list[str]] = []
    watcher.watch(lambda skills: observed.append(sorted(skill.name for skill in skills)))

    # Initial baseline poll should not trigger reload.
    assert watcher.poll_once() is False

    skill_b = tmp_path / "b"
    skill_b.mkdir()
    (skill_b / "SKILL.md").write_text(
        "---\nname: b\ndescription: B\n---\n# Body\n",
        encoding="utf-8",
    )
    assert watcher.poll_once() is True
    assert observed
    assert observed[-1] == ["a", "b"]


def test_skills_loader_prerequisites_env_missing_skips_skill(tmp_path, monkeypatch):
    monkeypatch.delenv("OWLCLAW_PREREQ_TOKEN", raising=False)
    skill_dir = tmp_path / "prereq-env-missing"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: prereq-env-missing
description: should be skipped
owlclaw:
  prerequisites:
    env: [OWLCLAW_PREREQ_TOKEN]
---
# Body
""",
        encoding="utf-8",
    )
    loader = SkillsLoader(tmp_path)
    assert loader.scan() == []


def test_skills_loader_prerequisites_env_present_loads_skill(tmp_path, monkeypatch):
    monkeypatch.setenv("OWLCLAW_PREREQ_TOKEN", "ok")
    skill_dir = tmp_path / "prereq-env-ok"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: prereq-env-ok
description: should load
owlclaw:
  prerequisites:
    env: [OWLCLAW_PREREQ_TOKEN]
---
# Body
""",
        encoding="utf-8",
    )
    loader = SkillsLoader(tmp_path)
    skills = loader.scan()
    assert len(skills) == 1
    assert skills[0].name == "prereq-env-ok"


def test_skills_loader_prerequisites_bin_missing_skips_skill(tmp_path):
    skill_dir = tmp_path / "prereq-bin-missing"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: prereq-bin-missing
description: should be skipped
owlclaw:
  prerequisites:
    bins: [__definitely_missing_binary__]
---
# Body
""",
        encoding="utf-8",
    )
    loader = SkillsLoader(tmp_path)
    assert loader.scan() == []


def test_skills_loader_prerequisites_python_package_missing_skips_skill(tmp_path):
    skill_dir = tmp_path / "prereq-pkg-missing"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: prereq-pkg-missing
description: should be skipped
owlclaw:
  prerequisites:
    python_packages: [__missing_python_package__]
---
# Body
""",
        encoding="utf-8",
    )
    loader = SkillsLoader(tmp_path)
    assert loader.scan() == []


def test_skills_loader_prerequisites_os_mismatch_skips_skill(tmp_path):
    skill_dir = tmp_path / "prereq-os-missing"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: prereq-os-missing
description: should be skipped
owlclaw:
  prerequisites:
    os: [nonexistent-os]
---
# Body
""",
        encoding="utf-8",
    )
    loader = SkillsLoader(tmp_path)
    assert loader.scan() == []


def test_skills_loader_prerequisites_config_list_and_map(tmp_path, monkeypatch):
    monkeypatch.setattr(
        SkillsLoader,
        "_load_runtime_config",
        lambda self: {"feature": {"enabled": True}, "agent": {"mode": "prod"}},
    )
    ok_dir = tmp_path / "prereq-config-ok"
    ok_dir.mkdir()
    (ok_dir / "SKILL.md").write_text(
        """---
name: prereq-config-ok
description: should load
owlclaw:
  prerequisites:
    config:
      feature.enabled: true
      agent.mode: prod
---
# Body
""",
        encoding="utf-8",
    )
    bad_dir = tmp_path / "prereq-config-bad"
    bad_dir.mkdir()
    (bad_dir / "SKILL.md").write_text(
        """---
name: prereq-config-bad
description: should skip
owlclaw:
  prerequisites:
    config:
      feature.enabled: false
---
# Body
""",
        encoding="utf-8",
    )
    list_dir = tmp_path / "prereq-config-list"
    list_dir.mkdir()
    (list_dir / "SKILL.md").write_text(
        """---
name: prereq-config-list
description: should load
owlclaw:
  prerequisites:
    config: [feature.enabled]
---
# Body
""",
        encoding="utf-8",
    )

    loader = SkillsLoader(tmp_path)
    skills = loader.scan()
    names = sorted(skill.name for skill in skills)
    assert names == ["prereq-config-list", "prereq-config-ok"]


def test_skills_loader_respects_owlclaw_yaml_skill_enablement(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "owlclaw.yaml").write_text(
        """skills:
  entries:
    disabled-skill:
      enabled: false
""",
        encoding="utf-8",
    )
    enabled_dir = tmp_path / "enabled"
    enabled_dir.mkdir()
    (enabled_dir / "SKILL.md").write_text(
        "---\nname: enabled-skill\ndescription: enabled\n---\n# Body\n",
        encoding="utf-8",
    )
    disabled_dir = tmp_path / "disabled"
    disabled_dir.mkdir()
    (disabled_dir / "SKILL.md").write_text(
        "---\nname: disabled-skill\ndescription: disabled\n---\n# Body\n",
        encoding="utf-8",
    )
    loader = SkillsLoader(tmp_path)
    skills = loader.scan()
    names = sorted(skill.name for skill in skills)
    assert names == ["enabled-skill"]


def test_skills_loader_allows_explicit_enable_in_owlclaw_yaml(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "owlclaw.yaml").write_text(
        """skills:
  entries:
    enabled-skill:
      enabled: true
""",
        encoding="utf-8",
    )
    skill_dir = tmp_path / "enabled"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: enabled-skill\ndescription: enabled\n---\n# Body\n",
        encoding="utf-8",
    )
    loader = SkillsLoader(tmp_path)
    skills = loader.scan()
    assert len(skills) == 1
    assert skills[0].name == "enabled-skill"


def test_skills_loader_natural_language_mode_sets_trigger_config(tmp_path):
    skill_dir = tmp_path / "nl-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: nl-skill
description: 每天早上 9 点检查库存
---
# 库存预警
当库存不足时通知我
""",
        encoding="utf-8",
    )
    loader = SkillsLoader(tmp_path)
    skills = loader.scan()
    assert len(skills) == 1
    skill = skills[0]
    assert skill.parse_mode == "natural_language"
    assert skill.trigger_config.get("type") == "cron"
    assert skill.trigger_config.get("expression") == "0 9 * * *"
    assert skill.trigger == 'cron("0 9 * * *")'


def test_skills_loader_hybrid_mode_uses_nl_trigger_when_owlclaw_has_no_trigger(tmp_path):
    skill_dir = tmp_path / "hybrid-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: hybrid-skill
description: 订单通知
owlclaw:
  task_type: order_monitor
---
# 订单通知
每周一生成订单汇总
""",
        encoding="utf-8",
    )
    loader = SkillsLoader(tmp_path)
    skills = loader.scan()
    assert len(skills) == 1
    skill = skills[0]
    assert skill.parse_mode == "hybrid"
    assert skill.trigger_config.get("type") == "cron"
    assert skill.trigger == 'cron("0 0 * * 1")'
