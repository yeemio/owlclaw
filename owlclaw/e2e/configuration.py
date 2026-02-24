"""Configuration loader for e2e validation CLI."""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class E2EConfig(BaseModel):
    """Runtime configuration for e2e validation CLI."""

    mode: str = "full"
    scenario_file: str | None = None
    task_id: str = "1"
    timeout_seconds: int = Field(default=300, ge=1)
    fail_fast: bool = False
    output_file: str | None = None


def load_e2e_config(
    *,
    config_path: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> E2EConfig:
    """Load config from JSON file and apply OWLCLAW_E2E_* environment overrides."""
    base: dict[str, Any] = {}
    if config_path:
        base = _load_json_config(config_path)

    env = dict(os.environ if environ is None else environ)
    overrides = _load_env_overrides(env)
    merged = {**base, **overrides}
    return E2EConfig.model_validate(merged)


def _load_json_config(config_path: str) -> dict[str, Any]:
    path = Path(config_path)
    raw = path.read_text(encoding="utf-8")
    loaded = json.loads(raw)
    if not isinstance(loaded, dict):
        raise ValueError("e2e config file must be a JSON object")
    return dict(loaded)


def _load_env_overrides(environ: Mapping[str, str]) -> dict[str, Any]:
    mapping: dict[str, tuple[str, Callable[[str], Any]]] = {
        "OWLCLAW_E2E_MODE": ("mode", str),
        "OWLCLAW_E2E_SCENARIO_FILE": ("scenario_file", str),
        "OWLCLAW_E2E_TASK_ID": ("task_id", str),
        "OWLCLAW_E2E_TIMEOUT_SECONDS": ("timeout_seconds", int),
        "OWLCLAW_E2E_FAIL_FAST": ("fail_fast", _to_bool),
        "OWLCLAW_E2E_OUTPUT_FILE": ("output_file", str),
    }
    overrides: dict[str, Any] = {}
    for env_name, (field_name, converter) in mapping.items():
        value = environ.get(env_name)
        if value is None or value == "":
            continue
        overrides[field_name] = converter(value)
    return overrides


def _to_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"invalid boolean value: {value}")
