"""Unit/property tests for runtime config load/validation/reload (task 12)."""

from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import settings
from hypothesis import strategies as st

from owlclaw.agent.runtime.config import (
    DEFAULT_RUNTIME_CONFIG,
    load_runtime_config,
    validate_runtime_config,
)
from owlclaw.agent.runtime.runtime import AgentRuntime


def _make_app_dir(tmp_path: Path) -> str:
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "SOUL.md").write_text("You are a helpful assistant.", encoding="utf-8")
    (tmp_path / "IDENTITY.md").write_text("## My Capabilities\n- market_scan\n", encoding="utf-8")
    return str(tmp_path)


def test_load_runtime_config_from_file(tmp_path: Path) -> None:
    config_path = tmp_path / "owlclaw.yaml"
    config_path.write_text(
        "runtime:\n  model: gpt-4o\n  llm_timeout_seconds: 12\n  heartbeat:\n    enabled: false\n",
        encoding="utf-8",
    )
    cfg = load_runtime_config(config_path)
    assert cfg["model"] == "gpt-4o"
    assert cfg["llm_timeout_seconds"] == 12.0
    assert cfg["heartbeat"]["enabled"] is False


def test_validate_runtime_config_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="max_function_calls"):
        validate_runtime_config({"max_function_calls": 0})
    with pytest.raises(ValueError, match="llm_timeout_seconds"):
        validate_runtime_config({"llm_timeout_seconds": -1})
    with pytest.raises(ValueError, match="heartbeat.enabled"):
        validate_runtime_config({"heartbeat": {"enabled": "yes"}})


def test_runtime_load_and_reload_config(tmp_path: Path) -> None:
    app_dir = _make_app_dir(tmp_path / "app")
    cfg_path = tmp_path / "runtime.yaml"
    cfg_path.write_text("runtime:\n  model: gpt-4o-mini\n  max_function_calls: 2\n", encoding="utf-8")
    rt = AgentRuntime(agent_id="bot", app_dir=app_dir)
    loaded = rt.load_config_file(str(cfg_path))
    assert loaded["max_function_calls"] == 2
    cfg_path.write_text("runtime:\n  model: gpt-4o\n  max_function_calls: 3\n", encoding="utf-8")
    reloaded = rt.reload_config()
    assert reloaded["model"] == "gpt-4o"
    assert reloaded["max_function_calls"] == 3


def test_runtime_reload_without_path_raises(tmp_path: Path) -> None:
    rt = AgentRuntime(agent_id="bot", app_dir=_make_app_dir(tmp_path))
    with pytest.raises(RuntimeError, match="config path is not set"):
        rt.reload_config()


@given(
    max_calls=st.integers(min_value=1, max_value=200),
    llm_timeout=st.floats(min_value=0.1, max_value=600, allow_infinity=False, allow_nan=False),
    run_timeout=st.floats(min_value=0.1, max_value=3600, allow_infinity=False, allow_nan=False),
)
@settings(deadline=None)
def test_property_config_validation_accepts_positive_numbers(
    max_calls: int, llm_timeout: float, run_timeout: float
) -> None:
    cfg = validate_runtime_config(
        {
            "max_function_calls": max_calls,
            "llm_timeout_seconds": llm_timeout,
            "run_timeout_seconds": run_timeout,
        }
    )
    assert cfg["max_function_calls"] == max_calls
    assert cfg["llm_timeout_seconds"] > 0
    assert cfg["run_timeout_seconds"] > 0


def test_default_runtime_config_shape() -> None:
    assert DEFAULT_RUNTIME_CONFIG["model"]
    assert DEFAULT_RUNTIME_CONFIG["max_function_calls"] >= 1
