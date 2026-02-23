"""Unit tests for OwlClaw.configure with unified config manager."""

from __future__ import annotations

from owlclaw.app import OwlClaw
from owlclaw.config import ConfigManager


def test_configure_shortcuts_apply_to_nested_config() -> None:
    ConfigManager._reset_for_tests()
    app = OwlClaw("test-app")
    app.configure(
        soul="docs/custom/SOUL.md",
        model="gpt-4o",
        heartbeat_interval_minutes=45,
    )
    cfg = ConfigManager.instance().get()
    assert cfg.agent.soul == "docs/custom/SOUL.md"
    assert cfg.integrations.llm.model == "gpt-4o"
    assert cfg.agent.heartbeat_interval_minutes == 45


def test_configure_governance_dict_remains_compatible() -> None:
    ConfigManager._reset_for_tests()
    app = OwlClaw("test-app")
    app.configure(governance={"router": {"default_model": "gpt-4o-mini"}})
    assert app._governance_config == {"router": {"default_model": "gpt-4o-mini"}}


def test_configure_nested_delimiter_path_supported() -> None:
    ConfigManager._reset_for_tests()
    app = OwlClaw("test-app")
    app.configure(integrations__llm__temperature=0.3)
    cfg = ConfigManager.instance().get()
    assert cfg.integrations.llm.temperature == 0.3

