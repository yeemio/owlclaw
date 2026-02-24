from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from owlclaw.capabilities.bindings import BindingExecutor, BindingExecutorRegistry, BindingTool, HTTPBindingConfig
from owlclaw.capabilities.bindings.schema import BindingConfig


class _SuccessExecutor(BindingExecutor):
    async def execute(self, config: BindingConfig, parameters: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok", "echo": parameters, "mode": config.mode}

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        return []

    @property
    def supported_modes(self) -> list[str]:
        return ["active", "shadow"]


class _FailExecutor(BindingExecutor):
    async def execute(self, config: BindingConfig, parameters: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("executor failure")

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        return []

    @property
    def supported_modes(self) -> list[str]:
        return ["active"]


@pytest.mark.asyncio
async def test_binding_tool_calls_executor_and_records_success() -> None:
    registry = BindingExecutorRegistry()
    registry.register("http", _SuccessExecutor())

    ledger = AsyncMock()
    tool = BindingTool(
        name="fetch-order",
        description="Fetch order data",
        parameters_schema={"type": "object"},
        binding_config=HTTPBindingConfig(method="GET", url="https://svc.local/orders/{id}"),
        executor_registry=registry,
        ledger=ledger,
    )

    result = await tool(id=42)
    assert result["status"] == "ok"
    assert result["echo"] == {"id": 42}

    ledger.record_execution.assert_awaited_once()  # type: ignore[attr-defined]
    call_kwargs = ledger.record_execution.await_args.kwargs  # type: ignore[attr-defined]
    assert call_kwargs["capability_name"] == "fetch-order"
    assert call_kwargs["task_type"] == "binding:http"
    assert call_kwargs["status"] == "success"
    assert call_kwargs["input_params"]["binding_type"] == "http"
    assert call_kwargs["input_params"]["mode"] == "active"
    assert call_kwargs["input_params"]["parameters"] == {"id": 42}
    assert isinstance(call_kwargs["output_result"]["result_summary"], str)


@pytest.mark.asyncio
async def test_binding_tool_records_error_then_reraises() -> None:
    registry = BindingExecutorRegistry()
    registry.register("http", _FailExecutor())

    ledger = AsyncMock()
    tool = BindingTool(
        name="write-order",
        description="Write order data",
        parameters_schema={"type": "object"},
        binding_config=HTTPBindingConfig(method="POST", mode="shadow", url="https://svc.local/orders"),
        executor_registry=registry,
        ledger=ledger,
    )

    with pytest.raises(RuntimeError, match="executor failure"):
        await tool(order_id=7)

    ledger.record_execution.assert_awaited_once()  # type: ignore[attr-defined]
    call_kwargs = ledger.record_execution.await_args.kwargs  # type: ignore[attr-defined]
    assert call_kwargs["status"] == "error"
    assert call_kwargs["error_message"] == "executor failure"
    assert call_kwargs["input_params"]["mode"] == "shadow"


def test_binding_tool_summarize_truncates_long_payload() -> None:
    long_result = {"payload": "x" * 1000}
    summary = BindingTool._summarize(long_result, max_length=50)
    assert summary.endswith("...(truncated)")
    assert len(summary) > 50
