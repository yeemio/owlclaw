"""Acceptance tests for capabilities-skills (Task 8: e2e, performance, error scenarios)."""

import time

import pytest

from owlclaw import OwlClaw
from owlclaw.capabilities.registry import CapabilityRegistry
from owlclaw.capabilities.skills import SkillsLoader

# --- Task 8.1: E2E ---


def test_e2e_mount_skills_scan(tmp_path):
    """8.1.2: mount_skills() scans and discovers SKILL.md files."""
    (tmp_path / "cap" / "sub").mkdir(parents=True)
    (tmp_path / "cap" / "sub" / "SKILL.md").write_text(
        "---\nname: sub\ndescription: Sub skill\n---\n",
        encoding="utf-8",
    )
    app = OwlClaw("e2e")
    app.mount_skills(str(tmp_path))
    skills = app.skills_loader.list_skills()
    assert len(skills) == 1
    assert skills[0].name == "sub"


@pytest.mark.asyncio
async def test_e2e_handler_register_and_invoke(tmp_path):
    """8.1.3: Handler registration and invocation."""
    (tmp_path / "h").mkdir()
    (tmp_path / "h" / "SKILL.md").write_text(
        "---\nname: h\ndescription: H\n---\n",
        encoding="utf-8",
    )
    app = OwlClaw("e2e")
    app.mount_skills(str(tmp_path))

    @app.handler("h")
    async def my_handler(session):
        return {"invoked": True}

    result = await app.registry.invoke_handler("h", session={})
    assert result == {"invoked": True}


@pytest.mark.asyncio
async def test_e2e_state_register_and_query(tmp_path):
    """8.1.4: State registration and get_state."""
    (tmp_path / "s").mkdir()
    (tmp_path / "s" / "SKILL.md").write_text(
        "---\nname: s\ndescription: S\n---\n",
        encoding="utf-8",
    )
    app = OwlClaw("e2e")
    app.mount_skills(str(tmp_path))

    @app.state("my_state")
    def provide():
        return {"value": 42}

    result = await app.registry.get_state("my_state")
    assert result == {"value": 42}


def test_e2e_knowledge_injection(tmp_path):
    """8.1.5: Knowledge injector formats Skills for prompt."""
    (tmp_path / "k").mkdir()
    (tmp_path / "k" / "SKILL.md").write_text(
        "---\nname: k\ndescription: Knowledge\n---\n\n# Instructions\nUse this.",
        encoding="utf-8",
    )
    app = OwlClaw("e2e")
    app.mount_skills(str(tmp_path))
    knowledge = app.knowledge_injector.get_skills_knowledge(["k"])
    assert "Skill: k" in knowledge
    assert "Knowledge" in knowledge
    assert "Use this." in knowledge


# --- Task 8.2: Performance ---


def test_perf_100_skills_load_time(tmp_path):
    """8.2.1: Load time for 100 Skills (target: reasonable, no hard threshold here)."""
    for i in range(100):
        (tmp_path / f"skill-{i}").mkdir()
        (tmp_path / f"skill-{i}" / "SKILL.md").write_text(
            f"---\nname: skill-{i}\ndescription: Skill {i}\n---\n",
            encoding="utf-8",
        )
    loader = SkillsLoader(tmp_path)
    start = time.perf_counter()
    skills = loader.scan()
    elapsed = time.perf_counter() - start
    assert len(skills) == 100
    assert elapsed < 8.0, "100 Skills should load in under 8 seconds"


def test_perf_metadata_query(tmp_path):
    """8.2.3: list_capabilities / get_capability_metadata performance."""
    for i in range(50):
        (tmp_path / f"s{i}").mkdir()
        (tmp_path / f"s{i}" / "SKILL.md").write_text(
            f"---\nname: s{i}\ndescription: D\n---\n",
            encoding="utf-8",
        )
    loader = SkillsLoader(tmp_path)
    loader.scan()
    registry = CapabilityRegistry(loader)
    for i in range(50):
        registry.register_handler(f"s{i}", lambda: None)
    start = time.perf_counter()
    for _ in range(100):
        registry.list_capabilities()
        registry.get_capability_metadata("s0")
    elapsed = time.perf_counter() - start
    assert elapsed < 2.0, "Metadata queries should be fast"


# --- Task 8.3: Error scenarios ---


def test_error_invalid_yaml_handled(tmp_path):
    """8.3.1: Invalid YAML in SKILL.md is skipped, scan continues."""
    (tmp_path / "good").mkdir()
    (tmp_path / "good" / "SKILL.md").write_text(
        "---\nname: good\ndescription: Good\n---\n",
        encoding="utf-8",
    )
    (tmp_path / "bad").mkdir()
    (tmp_path / "bad" / "SKILL.md").write_text(
        "---\nname: [broken\ndescription: x\n---\n",
        encoding="utf-8",
    )
    loader = SkillsLoader(tmp_path)
    skills = loader.scan()
    assert len(skills) == 1
    assert skills[0].name == "good"


def test_error_missing_required_fields_handled(tmp_path):
    """8.3.2: Missing name/description is skipped."""
    (tmp_path / "valid").mkdir()
    (tmp_path / "valid" / "SKILL.md").write_text(
        "---\nname: valid\ndescription: Valid\n---\n",
        encoding="utf-8",
    )
    (tmp_path / "invalid").mkdir()
    (tmp_path / "invalid" / "SKILL.md").write_text(
        "---\nmetadata: {}\n---\n",
        encoding="utf-8",
    )
    loader = SkillsLoader(tmp_path)
    skills = loader.scan()
    assert len(skills) == 1
    assert skills[0].name == "valid"


def test_error_duplicate_registration_raises(tmp_path):
    """8.3.3: Duplicate handler registration raises ValueError."""
    (tmp_path / "d").mkdir()
    (tmp_path / "d" / "SKILL.md").write_text(
        "---\nname: d\ndescription: D\n---\n",
        encoding="utf-8",
    )
    app = OwlClaw("e2e")
    app.mount_skills(str(tmp_path))

    @app.handler("d")
    def first():
        pass

    with pytest.raises(ValueError, match="already registered"):
        @app.handler("d")
        def second():
            pass
