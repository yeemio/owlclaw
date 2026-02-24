from __future__ import annotations

from typing import Any

import pytest

from owlclaw.capabilities.bindings import BindingExecutor, BindingExecutorRegistry
from owlclaw.capabilities.bindings.schema import BindingConfig


class _DummyExecutor(BindingExecutor):
    async def execute(self, config: BindingConfig, parameters: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok", "parameters": parameters, "type": config.type}

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        return []

    @property
    def supported_modes(self) -> list[str]:
        return ["active", "shadow"]


def test_registry_register_get_list() -> None:
    registry = BindingExecutorRegistry()
    executor = _DummyExecutor()
    registry.register("http", executor)
    assert registry.get("http") is executor
    assert registry.list_types() == ["http"]


def test_registry_unknown_type_raises_value_error() -> None:
    registry = BindingExecutorRegistry()
    registry.register("http", _DummyExecutor())
    with pytest.raises(ValueError, match="Unknown binding type 'queue'"):
        registry.get("queue")

