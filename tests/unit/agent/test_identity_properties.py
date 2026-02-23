"""Property tests for IdentityLoader (agent-runtime Task 2.3/2.4/2.6)."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from hypothesis import given
from hypothesis import settings
from hypothesis import strategies as st

from owlclaw.agent.runtime.identity import IdentityLoader

_SAFE_TEXT = st.text(
    alphabet=st.characters(blacklist_categories=["Cc", "Cs", "Zl", "Zp"]),
    min_size=1,
    max_size=120,
).filter(lambda s: s.strip() != "" and "\n" not in s and "\r" not in s and "\u00a0" not in s)


@pytest.mark.asyncio
@given(
    soul=_SAFE_TEXT,
    bullet_a=_SAFE_TEXT,
    bullet_b=_SAFE_TEXT,
)
@settings(deadline=None)
async def test_property_identity_load_completeness(soul: str, bullet_a: str, bullet_b: str) -> None:
    """Property 1: loader returns non-empty soul and capabilities summary from valid files."""
    with TemporaryDirectory() as tmp:
        app_dir = Path(tmp)
        (app_dir / "SOUL.md").write_text(soul, encoding="utf-8")
        (app_dir / "IDENTITY.md").write_text(
            f"## My Capabilities\n- {bullet_a}\n- {bullet_b}\n\n## Constraints\n- x\n",
            encoding="utf-8",
        )
        loader = IdentityLoader(str(app_dir))
        await loader.load()
        identity = loader.get_identity()
        assert identity["soul"].strip() == soul.strip()
        assert f"- {bullet_a}" in identity["capabilities_summary"]
        assert f"- {bullet_b}" in identity["capabilities_summary"]
        assert "Constraints" not in identity["capabilities_summary"]


@pytest.mark.asyncio
@given(
    missing=st.sampled_from(["SOUL.md", "IDENTITY.md", "BOTH"]),
)
@settings(deadline=None)
async def test_property_identity_missing_file_errors(missing: str) -> None:
    """Property 2: missing identity files consistently raise FileNotFoundError."""
    with TemporaryDirectory() as tmp:
        app_dir = Path(tmp)
        if missing in {"IDENTITY.md"}:
            (app_dir / "SOUL.md").write_text("assistant", encoding="utf-8")
        elif missing in {"SOUL.md"}:
            (app_dir / "IDENTITY.md").write_text("## My Capabilities\n- a\n", encoding="utf-8")
        loader = IdentityLoader(str(app_dir))
        with pytest.raises(FileNotFoundError):
            await loader.load()


@pytest.mark.asyncio
@given(
    original=_SAFE_TEXT,
    updated=_SAFE_TEXT,
)
@settings(deadline=None)
async def test_property_identity_reload_consistency(original: str, updated: str) -> None:
    """Property 3: reload() reflects file changes deterministically."""
    with TemporaryDirectory() as tmp:
        app_dir = Path(tmp)
        (app_dir / "SOUL.md").write_text(original, encoding="utf-8")
        (app_dir / "IDENTITY.md").write_text("## My Capabilities\n- a\n", encoding="utf-8")

        loader = IdentityLoader(str(app_dir))
        await loader.load()
        first = loader.get_identity()

        (app_dir / "SOUL.md").write_text(updated, encoding="utf-8")
        await loader.reload()
        second = loader.get_identity()

        assert first["soul"].strip() == original.strip()
        assert second["soul"].strip() == updated.strip()
