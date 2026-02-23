"""Property tests for KnowledgeInjector and Skills format validation."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import yaml  # type: ignore[import-untyped]
from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.capabilities.knowledge import KnowledgeInjector
from owlclaw.capabilities.skills import SkillsLoader


@given(
    name=st.from_regex(r"[a-z0-9]+(-[a-z0-9]+){0,2}", fullmatch=True),
    description=st.text(min_size=1, max_size=40).filter(lambda s: s.strip() != "" and "\n" not in s),
)
@settings(deadline=None)
def test_property_skills_format_validation_accepts_valid_frontmatter(name: str, description: str) -> None:
    """Property 9: valid SKILL frontmatter is accepted by loader."""
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        skill_dir = root / name
        skill_dir.mkdir(parents=True)
        frontmatter = yaml.safe_dump(
            {"name": name, "description": description},
            sort_keys=False,
            allow_unicode=False,
        ).strip()
        (skill_dir / "SKILL.md").write_text(
            f"---\n{frontmatter}\n---\n\n# Body\n",
            encoding="utf-8",
        )
        loader = SkillsLoader(root)
        skills = loader.scan()
        assert len(skills) == 1
        assert skills[0].name == name


@given(
    bad_name=st.text(min_size=1, max_size=20).filter(
        lambda s: ("\n" not in s) and (not all(ch.islower() or ch.isdigit() or ch == "-" for ch in s) or " " in s)
    )
)
@settings(deadline=None)
def test_property_skills_format_validation_rejects_invalid_name(bad_name: str) -> None:
    """Property 9: invalid skill names are rejected."""
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        skill_dir = root / "bad"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {bad_name}\ndescription: desc\n---\n",
            encoding="utf-8",
        )
        loader = SkillsLoader(root)
        skills = loader.scan()
        assert len(skills) == 0


@given(
    token_limit=st.integers(min_value=5, max_value=50),
    body_a=st.text(min_size=20, max_size=80).filter(lambda s: s.strip() != "" and "\n" not in s),
    body_b=st.text(min_size=20, max_size=80).filter(lambda s: s.strip() != "" and "\n" not in s),
)
@settings(deadline=None)
def test_property_skills_token_limit_selection(token_limit: int, body_a: str, body_b: str) -> None:
    """Property 10: select_skills enforces token budget with progressive selection."""
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        for idx, body in enumerate((body_a, body_b), start=1):
            name = f"skill-{idx}"
            skill_dir = root / name
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: desc {idx}\n---\n\n{body}\n",
                encoding="utf-8",
            )
        loader = SkillsLoader(root)
        loader.scan()
        injector = KnowledgeInjector(loader, token_limit=token_limit)
        selected = injector.select_skills(["skill-1", "skill-2"])
        assert selected
        total_tokens = 0
        for name in selected:
            skill = loader.get_skill(name)
            assert skill is not None
            total_tokens += injector._estimate_tokens(skill.load_full_content())
        assert len(selected) == 1 or total_tokens <= token_limit
