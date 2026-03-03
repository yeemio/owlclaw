"""Integration tests for Lite Mode end-to-end flow."""

from __future__ import annotations

import pytest

from owlclaw import OwlClaw


@pytest.mark.asyncio
async def test_lite_mode_heartbeat_trigger_runs_without_api_key(tmp_path) -> None:
    skill_dir = tmp_path / "inventory-check"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: inventory-check\ndescription: Check inventory\n---\n",
        encoding="utf-8",
    )
    (tmp_path / "SOUL.md").write_text("# Soul\nLite mode test agent.", encoding="utf-8")
    (tmp_path / "IDENTITY.md").write_text("# Identity\nLite mode test identity.", encoding="utf-8")

    app = OwlClaw.lite(
        "lite-e2e",
        skills_path=str(tmp_path),
        mock_responses={"default": {"content": "No action required", "function_calls": []}},
        heartbeat_interval_minutes=1,
    )

    runtime = await app.start(app_dir=str(tmp_path))
    try:
        result = await runtime.trigger_event("heartbeat", payload={"source": "heartbeat"})
        assert result["status"] == "completed"
        assert "Invalid API key" not in str(result)
    finally:
        await app.stop()
