"""Binding tool wrapper that dispatches to executors and records Ledger events."""

from __future__ import annotations

import json
import logging
import time
import uuid
from decimal import Decimal
from typing import Any, Protocol

from owlclaw.capabilities.bindings.executor import BindingExecutorRegistry
from owlclaw.capabilities.bindings.schema import BindingConfig

logger = logging.getLogger(__name__)


class LedgerProtocol(Protocol):
    """Protocol for governance ledger integration."""

    async def record_execution(
        self,
        tenant_id: str,
        agent_id: str,
        run_id: str,
        capability_name: str,
        task_type: str,
        input_params: dict[str, Any],
        output_result: dict[str, Any] | None,
        decision_reasoning: str | None,
        execution_time_ms: int,
        llm_model: str,
        llm_tokens_input: int,
        llm_tokens_output: int,
        estimated_cost: Decimal,
        status: str,
        error_message: str | None = None,
    ) -> None:
        """Record one invocation."""


class BindingTool:
    """Auto-generated callable tool for declarative binding execution."""

    def __init__(
        self,
        name: str,
        description: str,
        parameters_schema: dict[str, Any],
        binding_config: BindingConfig,
        executor_registry: BindingExecutorRegistry,
        ledger: LedgerProtocol | None = None,
        *,
        tenant_id: str = "default",
        agent_id: str = "binding-tool",
    ) -> None:
        self.name = name
        self.description = description
        self.parameters_schema = parameters_schema
        self.binding_config = binding_config
        self.executor_registry = executor_registry
        self.ledger = ledger
        self.tenant_id = tenant_id
        self.agent_id = agent_id

    async def __call__(self, **kwargs: Any) -> dict[str, Any]:
        """Execute binding with timing and optional ledger recording."""
        start = time.monotonic()
        executor = self.executor_registry.get(self.binding_config.type)
        run_id = str(uuid.uuid4())
        try:
            result = await executor.execute(self.binding_config, kwargs)
            elapsed_ms = int((time.monotonic() - start) * 1000)
            status = self._derive_status(result)
            await self._record_ledger(
                run_id=run_id,
                parameters=kwargs,
                result_summary=self._summarize(result),
                elapsed_ms=elapsed_ms,
                status=status,
                error_message=None,
            )
            return result
        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            await self._record_ledger(
                run_id=run_id,
                parameters=kwargs,
                result_summary=self._summarize({"error": str(exc)}),
                elapsed_ms=elapsed_ms,
                status="error",
                error_message=str(exc),
            )
            raise

    async def _record_ledger(
        self,
        *,
        run_id: str,
        parameters: dict[str, Any],
        result_summary: str,
        elapsed_ms: int,
        status: str,
        error_message: str | None,
    ) -> None:
        if self.ledger is None:
            return
        try:
            await self.ledger.record_execution(
                tenant_id=self.tenant_id,
                agent_id=self.agent_id,
                run_id=run_id,
                capability_name=self.name,
                task_type=f"binding:{self.binding_config.type}",
                input_params={
                    "tool_name": self.name,
                    "binding_type": self.binding_config.type,
                    "mode": self.binding_config.mode,
                    "parameters": parameters,
                },
                output_result={
                    "result_summary": result_summary,
                    "elapsed_ms": elapsed_ms,
                    "status": status,
                    "binding_type": self.binding_config.type,
                    "mode": self.binding_config.mode,
                },
                decision_reasoning=None,
                execution_time_ms=elapsed_ms,
                llm_model="binding-executor",
                llm_tokens_input=0,
                llm_tokens_output=0,
                estimated_cost=Decimal("0"),
                status=status,
                error_message=error_message,
            )
        except Exception:
            logger.exception("Failed to record binding execution for tool '%s'", self.name)

    @staticmethod
    def _summarize(result: dict[str, Any], max_length: int = 500) -> str:
        """Summarize invocation result payload for ledger storage."""
        text = json.dumps(result, ensure_ascii=False, default=str)
        if len(text) > max_length:
            return f"{text[:max_length]}...(truncated)"
        return text

    @staticmethod
    def _derive_status(result: dict[str, Any]) -> str:
        raw = result.get("status")
        if isinstance(raw, str) and raw.strip().lower() == "shadow":
            return "shadow"
        return "success"
