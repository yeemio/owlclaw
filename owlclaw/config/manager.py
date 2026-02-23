"""Configuration manager for OwlClaw."""

from __future__ import annotations

import os
from threading import Lock
from typing import Any, Callable, ClassVar

import yaml

from owlclaw.config.loader import YAMLConfigLoader
from owlclaw.config.models import OwlClawConfig

ConfigListener = Callable[[OwlClawConfig, OwlClawConfig], None]


def _deep_merge(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = dict(base)
    for key, value in updates.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, dict)
        ):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _build_nested_dict(path: list[str], value: Any) -> dict[str, Any]:
    current: dict[str, Any] = value
    for key in reversed(path):
        current = {key: current}
    return current


def _collect_env_overrides(prefix: str = "OWLCLAW_") -> dict[str, Any]:
    """Collect OWLCLAW_ env vars into nested dict overrides."""
    merged: dict[str, Any] = {}
    for key, raw_value in os.environ.items():
        if not key.startswith(prefix):
            continue
        suffix = key[len(prefix) :]
        if not suffix:
            continue
        path = [segment.strip().lower() for segment in suffix.split("__") if segment.strip()]
        if not path:
            continue
        try:
            parsed_value = yaml.safe_load(raw_value)
        except yaml.YAMLError:
            parsed_value = raw_value
        merged = _deep_merge(merged, _build_nested_dict(path, parsed_value))
    return merged


class ConfigManager:
    """Thread-safe singleton for typed configuration access."""

    _instance: ClassVar[ConfigManager | None] = None
    _class_lock: ClassVar[Lock] = Lock()

    def __init__(self) -> None:
        self._lock = Lock()
        self._config = OwlClawConfig()
        self._listeners: list[ConfigListener] = []

    @classmethod
    def instance(cls) -> ConfigManager:
        """Get singleton instance."""
        if cls._instance is not None:
            return cls._instance
        with cls._class_lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    @classmethod
    def load(
        cls,
        config_path: str | None = None,
        overrides: dict[str, Any] | None = None,
    ) -> ConfigManager:
        """Load config by precedence: defaults < YAML < env vars < runtime overrides."""
        manager = cls.instance()
        defaults = OwlClawConfig.model_construct().model_dump(mode="python")
        yaml_data = YAMLConfigLoader.load_dict(config_path)
        env_data = _collect_env_overrides()
        merged = _deep_merge(defaults, yaml_data)
        merged = _deep_merge(merged, env_data)
        merged = _deep_merge(merged, overrides or {})
        new_config = OwlClawConfig.model_validate(merged)
        with manager._lock:
            old = manager._config
            manager._config = new_config
            listeners = list(manager._listeners)
        for callback in listeners:
            callback(old, new_config)
        return manager

    def get(self) -> OwlClawConfig:
        """Return current config snapshot."""
        with self._lock:
            return self._config

    def on_change(self, callback: ConfigListener) -> None:
        """Register change listener."""
        with self._lock:
            self._listeners.append(callback)

