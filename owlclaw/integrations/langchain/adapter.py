"""Adapter to register and execute LangChain runnables as OwlClaw capabilities."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from owlclaw.integrations.langchain.config import LangChainConfig
from owlclaw.integrations.langchain.errors import ErrorHandler
from owlclaw.integrations.langchain.retry import RetryPolicy, calculate_backoff_delay, should_retry
from owlclaw.integrations.langchain.schema import SchemaBridge
from owlclaw.integrations.langchain.trace import TraceManager

logger = logging.getLogger(__name__)


@dataclass
class RunnableConfig:
    """Configuration for one registered runnable."""

    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None = None
    input_transformer: Any | None = None
    output_transformer: Any | None = None
    fallback: str | None = None
    retry_policy: dict[str, Any] | None = None
    timeout_seconds: int | None = None
    enable_tracing: bool = True


class LangChainAdapter:
    """LangChain integration adapter."""

    def __init__(
        self,
        app: Any,
        config: LangChainConfig,
        *,
        schema_bridge: SchemaBridge | None = None,
        trace_manager: TraceManager | None = None,
        error_handler: ErrorHandler | None = None,
    ) -> None:
        self._app = app
        self._config = config
        self._schema_bridge = schema_bridge or SchemaBridge()
        self._trace_manager = trace_manager or TraceManager(config)
        self._error_handler = error_handler or ErrorHandler()

    def register_runnable(self, runnable: Any, config: RunnableConfig) -> None:
        """Register runnable as capability handler."""
        self._validate_runnable(runnable)
        if not config.name.strip():
            raise ValueError("Runnable config name must be non-empty")
        if not config.description.strip():
            raise ValueError("Runnable config description must be non-empty")
        if not isinstance(config.input_schema, dict) or not config.input_schema:
            raise ValueError("Runnable config input_schema must be a non-empty dict")

        handler = self._create_handler(runnable, config)
        self._register_handler(config.name, handler)

    def _create_handler(self, runnable: Any, config: RunnableConfig):
        """Create wrapped capability handler."""

        async def handler(session: dict[str, Any]) -> dict[str, Any]:
            context = session.get("context") if isinstance(session, dict) else None
            payload = session.get("input", session) if isinstance(session, dict) else {}
            if not isinstance(payload, dict):
                payload = {"input": payload}
            return await self.execute(runnable, payload, context, config)

        return handler

    async def execute(
        self,
        runnable: Any,
        input_data: dict[str, Any],
        context: Any,
        config: RunnableConfig,
    ) -> dict[str, Any]:
        """Execute runnable with validation, trace, and error mapping."""
        span = None
        if config.enable_tracing:
            span = self._trace_manager.create_span(
                name=f"langchain_{config.name}",
                input_data=input_data,
                context=context if isinstance(context, dict) else None,
            )

        retry_policy = self._build_retry_policy(config.retry_policy)
        last_error: Exception | None = None
        try:
            self._schema_bridge.validate_input(input_data, config.input_schema)
            transformed_input = self._schema_bridge.transform_input(input_data, config.input_transformer)

            for attempt in range(1, retry_policy.max_attempts + 1):
                try:
                    result = await self._execute_with_timeout(runnable, transformed_input, config.timeout_seconds)
                    transformed_output = self._schema_bridge.transform_output(result, config.output_transformer)
                    if span is not None:
                        span.end(output=transformed_output)
                    return transformed_output
                except Exception as exc:
                    last_error = exc
                    if should_retry(exc, attempt=attempt, policy=retry_policy):
                        delay_seconds = calculate_backoff_delay(attempt, retry_policy)
                        if delay_seconds > 0:
                            await asyncio.sleep(delay_seconds)
                        logger.warning(
                            "Retrying runnable=%s attempt=%d/%d after error=%s",
                            config.name,
                            attempt,
                            retry_policy.max_attempts,
                            type(exc).__name__,
                        )
                        continue
                    raise
        except Exception as exc:
            effective_error = last_error or exc
            if span is not None:
                span.record_error(effective_error)
                span.end(output={"error": str(effective_error)})
            if config.fallback:
                return await self._error_handler.handle_fallback(
                    config.fallback,
                    input_data,
                    context,
                    effective_error,
                )
            return self._error_handler.map_exception(effective_error)

    async def _execute_with_timeout(self, runnable: Any, input_data: Any, timeout_seconds: int | None) -> Any:
        """Execute runnable with async preference and timeout support."""
        self._validate_runnable(runnable)
        coroutine = self._as_coroutine(runnable, input_data)
        if timeout_seconds is None:
            return await coroutine
        return await asyncio.wait_for(coroutine, timeout=timeout_seconds)

    @staticmethod
    def _as_coroutine(runnable: Any, input_data: Any) -> Any:
        if callable(getattr(runnable, "ainvoke", None)):
            return runnable.ainvoke(input_data)
        if callable(getattr(runnable, "invoke", None)):
            loop = asyncio.get_running_loop()
            return loop.run_in_executor(None, runnable.invoke, input_data)
        raise TypeError(
            f"Unsupported runnable type: {type(runnable).__name__}. "
            "Runnable must implement invoke() or ainvoke()."
        )

    @staticmethod
    def _validate_runnable(runnable: Any) -> None:
        if callable(getattr(runnable, "ainvoke", None)) or callable(getattr(runnable, "invoke", None)):
            return
        raise TypeError(
            f"Unsupported runnable type: {type(runnable).__name__}. "
            "Runnable must implement invoke() or ainvoke()."
        )

    def _register_handler(self, name: str, handler: Any) -> None:
        registry = getattr(self._app, "registry", None)
        if registry is not None:
            registry.register_handler(name, handler)
            return

        register_capability = getattr(self._app, "register_capability", None)
        if callable(register_capability):
            register_capability(name=name, handler=handler)
            return

        raise RuntimeError(
            "App does not expose capability registry. "
            "Expected app.registry.register_handler(...) or app.register_capability(...)."
        )

    @staticmethod
    def _build_retry_policy(raw_policy: dict[str, Any] | None) -> RetryPolicy:
        if raw_policy is None:
            return RetryPolicy(max_attempts=1, retryable_errors=[])
        return RetryPolicy(
            max_attempts=int(raw_policy.get("max_attempts", 1)),
            initial_delay_ms=int(raw_policy.get("initial_delay_ms", 0)),
            max_delay_ms=int(raw_policy.get("max_delay_ms", 0)),
            backoff_multiplier=float(raw_policy.get("backoff_multiplier", 2.0)),
            retryable_errors=list(raw_policy.get("retryable_errors", [])),
        )
