"""Unit tests for IdentityLoader (agent-runtime Task 2)."""

from __future__ import annotations

import pytest

from owlclaw.agent.runtime.identity import IdentityLoader


@pytest.fixture
def app_dir(tmp_path):
    """Create a temp app dir with SOUL.md and IDENTITY.md."""
    soul = tmp_path / "SOUL.md"
    soul.write_text("You are a diligent trading assistant.", encoding="utf-8")

    identity = tmp_path / "IDENTITY.md"
    identity.write_text(
        "# Agent Identity\n\n"
        "## My Capabilities\n"
        "- Monitor market data\n"
        "- Generate reports\n\n"
        "## Constraints\n"
        "- Only trade within configured risk limits\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def soul_only_dir(tmp_path):
    """App dir with SOUL.md only (no IDENTITY.md)."""
    (tmp_path / "SOUL.md").write_text("Minimal soul.", encoding="utf-8")
    return tmp_path


class TestIdentityLoader:
    async def test_load_success(self, app_dir) -> None:
        loader = IdentityLoader(str(app_dir))
        await loader.load()
        identity = loader.get_identity()
        assert "diligent trading assistant" in identity["soul"]
        assert "Monitor market data" in identity["capabilities_summary"]

    async def test_capabilities_summary_extracted(self, app_dir) -> None:
        loader = IdentityLoader(str(app_dir))
        await loader.load()
        summary = loader.get_identity()["capabilities_summary"]
        assert "Monitor market data" in summary
        assert "Generate reports" in summary
        # Should NOT include content from ## Constraints
        assert "risk limits" not in summary

    async def test_missing_soul_raises(self, tmp_path) -> None:
        loader = IdentityLoader(str(tmp_path))
        with pytest.raises(FileNotFoundError, match="SOUL.md"):
            await loader.load()

    async def test_empty_soul_raises(self, tmp_path) -> None:
        (tmp_path / "SOUL.md").write_text("   ", encoding="utf-8")
        (tmp_path / "IDENTITY.md").write_text("## My Capabilities\n- A\n", encoding="utf-8")
        loader = IdentityLoader(str(tmp_path))
        with pytest.raises(ValueError, match="SOUL.md must not be empty"):
            await loader.load()

    async def test_missing_identity_md_raises(self, soul_only_dir) -> None:
        loader = IdentityLoader(str(soul_only_dir))
        with pytest.raises(FileNotFoundError, match="IDENTITY.md"):
            await loader.load()

    async def test_empty_identity_raises(self, tmp_path) -> None:
        (tmp_path / "SOUL.md").write_text("assistant", encoding="utf-8")
        (tmp_path / "IDENTITY.md").write_text(" \n", encoding="utf-8")
        loader = IdentityLoader(str(tmp_path))
        with pytest.raises(ValueError, match="IDENTITY.md must not be empty"):
            await loader.load()

    async def test_get_identity_before_load_raises(self, app_dir) -> None:
        loader = IdentityLoader(str(app_dir))
        with pytest.raises(RuntimeError, match="load\\(\\)"):
            loader.get_identity()

    async def test_hot_reload(self, app_dir) -> None:
        loader = IdentityLoader(str(app_dir))
        await loader.load()

        # Modify SOUL.md
        (app_dir / "SOUL.md").write_text("Updated soul content.", encoding="utf-8")
        await loader.reload()

        identity = loader.get_identity()
        assert "Updated soul content" in identity["soul"]

    async def test_chinese_heading(self, tmp_path) -> None:
        (tmp_path / "SOUL.md").write_text("我是助手。", encoding="utf-8")
        (tmp_path / "IDENTITY.md").write_text(
            "## 我的能力\n- 监控市场\n## 约束\n- 限额\n",
            encoding="utf-8",
        )
        loader = IdentityLoader(str(tmp_path))
        await loader.load()
        summary = loader.get_identity()["capabilities_summary"]
        assert "监控市场" in summary
        assert "限额" not in summary

    async def test_capabilities_heading_case_and_trailing_spaces(self, tmp_path) -> None:
        (tmp_path / "SOUL.md").write_text("You are assistant.", encoding="utf-8")
        (tmp_path / "IDENTITY.md").write_text(
            "# Identity\n\n## MY CAPABILITIES   \n- A\n## Other\n- B\n",
            encoding="utf-8",
        )
        loader = IdentityLoader(str(tmp_path))
        await loader.load()
        summary = loader.get_identity()["capabilities_summary"]
        assert summary == "- A"
