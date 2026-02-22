"""Unit tests for owlclaw skill CLI (init, validate, list)."""

import json

import pytest
from click.exceptions import Exit
from typer.testing import CliRunner

from owlclaw.cli.skill import skill_app
from owlclaw.templates.skills.models import ValidationError

runner = CliRunner()


def test_skill_list_empty(tmp_path, monkeypatch):
    """list in empty directory prints no skills."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(skill_app, ["list"])
    assert result.exit_code == 0
    assert "No skills found" in result.output


def test_skill_init_creates_skill_dir_and_file(tmp_path, monkeypatch):
    """init creates directory and SKILL.md with frontmatter (default template)."""
    monkeypatch.chdir(tmp_path)
    from owlclaw.cli.skill_init import init_command

    init_command(name="my-skill", path=".", template="default")
    skill_dir = tmp_path / "my-skill"
    skill_file = skill_dir / "SKILL.md"
    assert skill_dir.is_dir()
    assert skill_file.is_file()
    content = skill_file.read_text(encoding="utf-8")
    assert "name: my-skill" in content
    assert "description:" in content
    assert "---" in content


def test_skill_validate_passes_for_valid_skill(tmp_path):
    """validate exits 0 for SKILL.md with name and description."""
    (tmp_path / "valid-skill").mkdir()
    (tmp_path / "valid-skill" / "SKILL.md").write_text(
        "---\nname: valid-skill\ndescription: A valid skill.\n---\n# Body\n",
        encoding="utf-8",
    )
    result = runner.invoke(skill_app, ["validate", str(tmp_path / "valid-skill")])
    assert result.exit_code == 0
    assert "OK:" in result.output


def test_skill_validate_fails_for_missing_description(tmp_path):
    """validate exits non-zero when description is missing."""
    (tmp_path / "bad-skill").mkdir()
    (tmp_path / "bad-skill" / "SKILL.md").write_text(
        "---\nname: bad-skill\n---\n# Body\n",
        encoding="utf-8",
    )
    result = runner.invoke(skill_app, ["validate", str(tmp_path / "bad-skill")])
    assert result.exit_code != 0
    assert "FAIL:" in result.output


def test_skill_validate_nonexistent_path_exits_with_error(tmp_path):
    """validate should report missing paths explicitly."""
    missing = tmp_path / "does-not-exist"
    result = runner.invoke(skill_app, ["validate", str(missing)])
    assert result.exit_code == 2
    assert "path not found" in result.output.lower()


def test_skill_validate_non_skill_file_exits_with_error(tmp_path):
    """validate should fail when a provided file is not named SKILL.md."""
    not_skill = tmp_path / "README.md"
    not_skill.write_text("# not a skill file\n", encoding="utf-8")
    result = runner.invoke(skill_app, ["validate", str(not_skill)])
    assert result.exit_code == 2
    assert "file is not skill.md" in result.output.lower()


def test_skill_validate_deduplicates_overlapping_paths(tmp_path):
    """validate should not process the same SKILL.md twice for overlapping inputs."""
    skill_dir = tmp_path / "dup-skill"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        "---\nname: dup-skill\ndescription: Duplicate path test.\n---\n# Body\n",
        encoding="utf-8",
    )
    result = runner.invoke(skill_app, ["validate", str(tmp_path), str(skill_file)])
    assert result.exit_code == 0
    assert "Validated 1 file(s): 1 passed, 0 failed." in result.output


def test_skill_init_from_template_creates_valid_skill_md(tmp_path):
    """Template library produces valid SKILL.md from monitoring/health-check."""
    from owlclaw.templates.skills import (
        TemplateRegistry,
        TemplateRenderer,
        get_default_templates_dir,
    )

    registry = TemplateRegistry(get_default_templates_dir())
    renderer = TemplateRenderer(registry)
    params = {
        "skill_name": "TestMonitor",
        "skill_description": "Test",
        "endpoints": "/health,/ready",
    }
    content = renderer.render("monitoring/health-check", params)
    skill_dir = tmp_path / "test-monitor"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    assert "name: test" in text and "monitor" in text.lower()
    assert "/health,/ready" in text


def test_skill_templates_list(tmp_path):
    """templates subcommand lists templates from library."""
    result = runner.invoke(skill_app, ["templates"])
    assert result.exit_code == 0
    assert "monitoring/health-check" in result.output
    assert "Health Check" in result.output or "health-check" in result.output


def test_skill_templates_category_filter_case_insensitive():
    """Template listing logic should accept mixed-case category names."""
    from owlclaw.cli.skill_list import _list_templates
    from owlclaw.templates.skills import TemplateRegistry, TemplateSearcher, get_default_templates_dir

    registry = TemplateRegistry(get_default_templates_dir())
    searcher = TemplateSearcher(registry)
    _list_templates(
        registry=registry,
        searcher=searcher,
        category="MONITORING",
        tags="",
        search="",
        show="",
        verbose=False,
        json_output=False,
    )


def test_skill_init_interactive_wizard_without_template(tmp_path, monkeypatch):
    """init without --template enters interactive mode and creates SKILL.md."""
    monkeypatch.chdir(tmp_path)
    from owlclaw.cli.skill_init import init_command

    prompts = iter(["1", "wizard-skill", "Wizard description", "/health"])

    def _fake_prompt(*args, **kwargs):  # type: ignore[no-untyped-def]
        return next(prompts, "1")

    monkeypatch.setattr("typer.prompt", _fake_prompt)
    init_command(
        name="",
        path=".",
        template="",
        category="",
        params_file="",
        param="",
        force=False,
    )

    skill_file = tmp_path / "wizard-skill" / "SKILL.md"
    assert skill_file.is_file()
    content = skill_file.read_text(encoding="utf-8")
    assert "name: wizard-skill" in content


def test_skill_init_params_file_not_found_exits(tmp_path):
    """Missing --params-file should fail with clear error."""
    from owlclaw.cli.skill_init import init_command

    with pytest.raises(Exit) as exc_info:
        init_command(
            name="",
            path=str(tmp_path),
            template="monitoring/health-check",
            category="",
            params_file=str(tmp_path / "missing.json"),
            param="",
            force=False,
        )
    assert exc_info.value.exit_code == 2


def test_skill_init_params_file_json_object_required(tmp_path):
    """--params-file must contain object mapping, not list/scalar."""
    from owlclaw.cli.skill_init import init_command

    params_file = tmp_path / "params.json"
    params_file.write_text(json.dumps(["bad", "shape"]), encoding="utf-8")
    with pytest.raises(Exit) as exc_info:
        init_command(
            name="",
            path=str(tmp_path),
            template="monitoring/health-check",
            category="",
            params_file=str(params_file),
            param="",
            force=False,
        )
    assert exc_info.value.exit_code == 2


def test_skill_init_non_interactive_missing_required_params_exits(tmp_path):
    """Non-interactive init should fail fast when required params are missing."""
    from owlclaw.cli.skill_init import init_command

    params_file = tmp_path / "params.json"
    params_file.write_text(json.dumps({"skill_name": "x"}), encoding="utf-8")
    with pytest.raises(Exit) as exc_info:
        init_command(
            name="",
            path=str(tmp_path),
            template="monitoring/health-check",
            category="",
            params_file=str(params_file),
            param="",
            force=False,
        )
    assert exc_info.value.exit_code == 2


def test_skill_init_invalid_param_entry_exits(tmp_path):
    """Invalid --param fragment without '=' should fail explicitly."""
    from owlclaw.cli.skill_init import init_command

    with pytest.raises(Exit) as exc_info:
        init_command(
            name="",
            path=str(tmp_path),
            template="monitoring/health-check",
            category="",
            params_file="",
            param="skill_name=test,broken_fragment",
            force=False,
        )
    assert exc_info.value.exit_code == 2


def test_skill_init_non_interactive_requires_template(tmp_path):
    """Non-interactive mode should require --template to avoid accidental prompts."""
    from owlclaw.cli.skill_init import init_command

    with pytest.raises(Exit) as exc_info:
        init_command(
            name="",
            path=str(tmp_path),
            template="",
            category="",
            params_file="",
            param="skill_name=test",
            force=False,
        )
    assert exc_info.value.exit_code == 2


def test_skill_init_exits_when_generated_skill_has_validation_error(tmp_path, monkeypatch):
    """init should return non-zero if generated SKILL.md has validation errors."""
    monkeypatch.chdir(tmp_path)
    from owlclaw.cli.skill_init import init_command

    def _fake_validate(_self, _path):  # type: ignore[no-untyped-def]
        return [ValidationError(field="name", message="bad name", severity="error")]

    monkeypatch.setattr("owlclaw.cli.skill_init.TemplateValidator.validate_skill_file", _fake_validate)
    with pytest.raises(Exit) as exc_info:
        init_command(
            name="my-skill",
            path=".",
            template="default",
            category="",
            params_file="",
            param="",
            force=False,
        )
    assert exc_info.value.exit_code == 1


def test_skill_list_shows_skills(tmp_path, monkeypatch):
    """list shows name and description of discovered skills."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a-skill").mkdir()
    (tmp_path / "a-skill" / "SKILL.md").write_text(
        "---\nname: a-skill\ndescription: First skill.\n---\n",
        encoding="utf-8",
    )
    (tmp_path / "b-skill").mkdir()
    (tmp_path / "b-skill" / "SKILL.md").write_text(
        "---\nname: b-skill\ndescription: Second skill.\n---\n",
        encoding="utf-8",
    )
    result = runner.invoke(skill_app, ["list"])
    assert result.exit_code == 0
    assert "a-skill" in result.output
    assert "b-skill" in result.output
    assert "First skill" in result.output
    assert "Second skill" in result.output


@pytest.mark.skip(reason="Typer/CliRunner optional positional path parsing differs; manual coverage")
def test_skill_init_refuse_overwrite_without_force(tmp_path):
    """init without --force refuses to overwrite existing SKILL.md."""
    (tmp_path / "existing").mkdir()
    (tmp_path / "existing" / "SKILL.md").write_text("existing", encoding="utf-8")
    path_arg = tmp_path.as_posix()
    result = runner.invoke(skill_app, ["init", "existing", path_arg])
    assert result.exit_code == 2
    assert "already exists" in result.output
    assert (tmp_path / "existing" / "SKILL.md").read_text() == "existing"


@pytest.mark.skip(reason="Typer/CliRunner optional positional path parsing differs; manual coverage")
def test_skill_init_force_overwrites(tmp_path):
    """init with --force overwrites existing SKILL.md."""
    (tmp_path / "overwrite").mkdir()
    (tmp_path / "overwrite" / "SKILL.md").write_text("old", encoding="utf-8")
    path_arg = tmp_path.as_posix()
    result = runner.invoke(
        skill_app, ["init", "overwrite", path_arg, "--force"]
    )
    assert result.exit_code == 0
    content = (tmp_path / "overwrite" / "SKILL.md").read_text(encoding="utf-8")
    assert "name: overwrite" in content
    assert "old" not in content
