"""Tests for LangChain metrics collection and export."""

from __future__ import annotations

from typing import Any

import pytest

from owlclaw.integrations.langchain.adapter import LangChainAdapter, RunnableConfig
from owlclaw.integrations.langchain.config import LangChainConfig
from owlclaw.integrations.langchain.metrics import MetricsCollector


def test_metrics_collect_and_export_json() -> None:
    metrics = MetricsCollector()
    metrics.record_execution(capability="entry-monitor", status="success", duration_ms=12)
    metrics.record_execution(
        capability="entry-monitor",
        status="error",
        duration_ms=20,
        error_type="ValidationError",
        fallback_used=True,
        retry_count=2,
    )

    payload = metrics.export_json()

    assert payload["executions_total"]["entry-monitor:success"] == 1
    assert payload["executions_total"]["entry-monitor:error"] == 1
    assert payload["errors_total"]["entry-monitor:ValidationError"] == 1
    assert payload["fallback_total"]["entry-monitor"] == 1
    assert payload["retries_total"]["entry-monitor"] == 2


def test_metrics_export_prometheus() -> None:
    metrics = MetricsCollector()
    metrics.record_execution(capability="entry-monitor", status="success", duration_ms=10)

    output = metrics.export_prometheus()

    assert "langchain_executions_total" in output
    assert "entry-monitor" in output
    assert "langchain_latency_ms_avg" in output


class DummyRegistry:
    def register_handler(self, name: str, handler: Any) -> None:
        return None


class DummyApp:
    def __init__(self) -> None:
        self.registry = DummyRegistry()


class EchoRunnable:
    async def ainvoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"echo": payload["text"]}


@pytest.mark.asyncio
async def test_adapter_metrics_integration() -> None:
    adapter = LangChainAdapter(DummyApp(), LangChainConfig())
    config = RunnableConfig(
        name="entry-monitor",
        description="metrics",
        input_schema={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    )

    await adapter.execute(EchoRunnable(), {"text": "hello"}, None, config)
    metrics = adapter.metrics("json")

    assert metrics["executions_total"]["entry-monitor:success"] >= 1
