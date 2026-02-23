"""Configuration manager for OwlClaw."""

from __future__ import annotations

from threading import Lock
from typing import Any, Callable, ClassVar

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
        """Load configuration from defaults + YAML + runtime overrides."""
        manager = cls.instance()
        yaml_data = YAMLConfigLoader.load_dict(config_path)
        merged = _deep_merge(yaml_data, overrides or {})
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

