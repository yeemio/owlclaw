from __future__ import annotations

from typing import Any

import pytest

from owlclaw.capabilities.bindings import (
    BindingExecutor,
    BindingExecutorRegistry,
    BindingTool,
    HTTPBindingConfig,
    SQLBindingConfig,
)
from owlclaw.capabilities.bindings.schema import BindingConfig
from owlclaw.security import InputSanitizer, SanitizationRule


class _EchoExecutor(BindingExecutor):
    async def execute(self, config: BindingConfig, parameters: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok", "parameters": parameters, "token": "secret-value"}

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        return []

    @property
    def supported_modes(self) -> list[str]:
        return ["active", "shadow"]


@pytest.mark.asyncio
async def test_binding_tool_sanitizes_input_parameters() -> None:
    registry = BindingExecutorRegistry()
    registry.register("http", _EchoExecutor())
    sanitizer = InputSanitizer(
        rules=[SanitizationRule(pattern=r"secret", action="replace", replacement="[MASKED]", description="mask secret")]
    )
    tool = BindingTool(
        name="safe-call",
        description="safe call",
        parameters_schema={"type": "object"},
        binding_config=HTTPBindingConfig(method="GET", url="https://svc.local/x"),
        executor_registry=registry,
        sanitizer=sanitizer,
    )

    result = await tool(payload="contains secret text")
    assert result["parameters"]["payload"] == "contains [MASKED] text"


@pytest.mark.asyncio
async def test_binding_tool_masks_sensitive_output() -> None:
    registry = BindingExecutorRegistry()
    registry.register("http", _EchoExecutor())
    tool = BindingTool(
        name="mask-output",
        description="mask output",
        parameters_schema={"type": "object"},
        binding_config=HTTPBindingConfig(method="GET", url="https://svc.local/y"),
        executor_registry=registry,
    )

    result = await tool()
    assert result["token"] == "[REDACTED]"


@pytest.mark.asyncio
async def test_binding_tool_sql_write_requires_high_risk_level() -> None:
    registry = BindingExecutorRegistry()
    registry.register("sql", _EchoExecutor())
    tool = BindingTool(
        name="sql-write",
        description="write",
        parameters_schema={"type": "object"},
        binding_config=SQLBindingConfig(
            connection="sqlite+aiosqlite:///:memory:",
            query="UPDATE users SET active=:active WHERE id=:id",
            read_only=False,
        ),
        executor_registry=registry,
        risk_level="low",
    )

    with pytest.raises(PermissionError, match="risk_level high or critical"):
        await tool(id=1, active=True)
