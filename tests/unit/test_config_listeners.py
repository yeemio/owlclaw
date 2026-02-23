"""Unit tests for config change listeners."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from owlclaw.config import (
    ConfigManager,
    register_governance_reload_listener,
    register_runtime_reload_listener,
    register_security_reload_listener,
)
from owlclaw.governance.visibility import VisibilityFilter
from owlclaw.security.risk_gate import RiskGate


class _DummyApp:
    def __init__(self) -> None:
        self._governance_config: dict[str, Any] | None = {"router": {"default_model": "old"}}
        self._visibility_filter: object | None = object()
        self._router: object | None = object()
        self.ensure_called = 0

    def _ensure_governance(self) -> None:
        self.ensure_called += 1


def test_register_governance_reload_listener_updates_app(tmp_path) -> None:  # type: ignore[no-untyped-def]
    ConfigManager._reset_for_tests()
    cfg_path = tmp_path / "owlclaw.yaml"
    cfg_path.write_text("governance:\n  monthly_budget: 1000\n", encoding="utf-8")
    manager = ConfigManager.load(config_path=str(cfg_path))
    app = _DummyApp()
    register_governance_reload_listener(app, manager=manager)

    cfg_path.write_text("governance:\n  monthly_budget: 1200\n", encoding="utf-8")
    manager.reload()
    assert app._governance_config is not None
    assert app._governance_config["monthly_budget"] == 1200
    assert app.ensure_called >= 1


def test_register_security_reload_listener_updates_risk_gate(tmp_path) -> None:  # type: ignore[no-untyped-def]
    ConfigManager._reset_for_tests()
    cfg_path = tmp_path / "owlclaw.yaml"
    cfg_path.write_text("security:\n  risk_gate:\n    confirmation_timeout_seconds: 300\n", encoding="utf-8")
    manager = ConfigManager.load(config_path=str(cfg_path))
    vf = VisibilityFilter()
    original_gate = vf._risk_gate
    register_security_reload_listener(vf, manager=manager)

    cfg_path.write_text("security:\n  risk_gate:\n    confirmation_timeout_seconds: 120\n", encoding="utf-8")
    manager.reload()
    assert isinstance(vf._risk_gate, RiskGate)
    assert vf._risk_gate is not original_gate


def test_register_runtime_reload_listener_updates_heartbeat(tmp_path) -> None:  # type: ignore[no-untyped-def]
    ConfigManager._reset_for_tests()
    cfg_path = tmp_path / "owlclaw.yaml"
    cfg_path.write_text("agent:\n  heartbeat_interval_minutes: 30\n", encoding="utf-8")
    manager = ConfigManager.load(config_path=str(cfg_path))
    runtime = SimpleNamespace(agent_id="agent-1", config={"heartbeat": {"enabled": True}}, _heartbeat_checker=None)
    register_runtime_reload_listener(runtime, manager=manager)

    cfg_path.write_text("agent:\n  heartbeat_interval_minutes: 10\n", encoding="utf-8")
    manager.reload()
    assert runtime.config["heartbeat"]["interval_minutes"] == 10
    assert runtime._heartbeat_checker is not None

