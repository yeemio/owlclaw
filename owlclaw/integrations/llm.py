"""LLM integration — all LLM calls MUST go through this module.

This layer isolates litellm so that routing, tracing, and provider swap
can be centralized. Provides:

- acompletion(): minimal pass-through for litellm.acompletion (tests, simple use)
- LLMConfig, LLMClient: full config + routing + fallback (integrations-llm spec)
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Minimal facade (architecture rule)
# ---------------------------------------------------------------------------


async def acompletion(**kwargs: Any) -> Any:
    """Async LLM completion. Delegates to litellm; all callers must use this.

    Args:
        **kwargs: Passed through to litellm.acompletion (model, messages,
            tools, tool_choice, etc.).

    Returns:
        litellm response object (e.g. choices[0].message with tool_calls).
    """
    import litellm

    return await litellm.acompletion(**kwargs)


# ---------------------------------------------------------------------------
# LLM error types (Task 6.1)
# ---------------------------------------------------------------------------


class LLMError(Exception):
    """Base exception for LLM integration errors."""

    def __init__(self, message: str, *, model: str | None = None, cause: Exception | None = None):
        super().__init__(message)
        self.message = message
        self.model = model
        self.cause = cause


class AuthenticationError(LLMError):
    """Raised when API key is invalid or missing."""


class RateLimitError(LLMError):
    """Raised when provider rate limit is exceeded (retriable)."""


class ContextWindowExceededError(LLMError):
    """Raised when prompt exceeds model context window."""


class ServiceUnavailableError(LLMError):
    """Raised when LLM provider is unavailable (fallback may be attempted)."""


# ---------------------------------------------------------------------------
# LLMConfig (Task 1)
# ---------------------------------------------------------------------------


def _substitute_env(value: str) -> str:
    """Replace ${VAR} with environment variable values."""
    if not isinstance(value, str):
        return value
    pattern = re.compile(r"\$\{([^}]+)\}|\$([A-Za-z_][A-Za-z0-9_]*)")
    def repl(m: re.Match) -> str:
        name = m.group(1) or m.group(2) or ""
        return os.environ.get(name, "")
    return pattern.sub(repl, value)


def _substitute_env_dict(data: dict) -> dict:
    """Recursively substitute ${VAR} in string values."""
    out: dict[str, Any] = {}
    for k, v in data.items():
        if isinstance(v, dict):
            out[k] = _substitute_env_dict(v)
        elif isinstance(v, str):
            out[k] = _substitute_env(v)
        else:
            out[k] = v
    return out


class ModelConfig(BaseModel):
    """Single model configuration."""

    name: str
    provider: str
    api_key_env: str = "OPENAI_API_KEY"
    temperature: float = 0.7
    max_tokens: int = 4096
    context_window: int = 128000
    supports_function_calling: bool = True
    cost_per_1k_prompt_tokens: float = 0.0
    cost_per_1k_completion_tokens: float = 0.0


class TaskTypeRouting(BaseModel):
    """task_type to model routing rule."""

    task_type: str
    model: str
    fallback_models: list[str] = Field(default_factory=list)
    temperature: float | None = None
    max_tokens: int | None = None


class LLMConfig(BaseModel):
    """LLM integration config (from owlclaw.yaml llm section)."""

    default_model: str = "gpt-4o-mini"
    models: dict[str, ModelConfig] = Field(default_factory=dict)
    task_type_routing: list[TaskTypeRouting] = Field(default_factory=list)
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    langfuse_enabled: bool = False
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "https://cloud.langfuse.com"
    mock_mode: bool = False
    mock_responses: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def from_yaml(cls, config_path: str | Path) -> LLMConfig:
        """Load LLM config from owlclaw.yaml (llm section)."""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        llm_data = data.get("llm", {})
        llm_data = _substitute_env_dict(llm_data)
        return cls.model_validate(llm_data)

    @classmethod
    def default_for_owlclaw(cls) -> LLMConfig:
        """Minimal config using default model (no yaml)."""
        return cls(
            default_model="gpt-4o-mini",
            models={
                "gpt-4o-mini": ModelConfig(
                    name="gpt-4o-mini",
                    provider="openai",
                    api_key_env="OPENAI_API_KEY",
                    cost_per_1k_prompt_tokens=0.00015,
                    cost_per_1k_completion_tokens=0.0006,
                ),
            },
        )


# ---------------------------------------------------------------------------
# LLMResponse, LLMClient (Task 2)
# ---------------------------------------------------------------------------


@dataclass
class LLMResponse:
    """Unified LLM response shape."""

    content: str | None
    function_calls: list[dict[str, Any]]
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost: float

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class LLMClient:
    """OwlClaw wrapper over litellm with config, routing, fallback."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self._langfuse: Any = None
        if config.langfuse_enabled and config.langfuse_public_key and config.langfuse_secret_key:
            try:
                from langfuse import Langfuse
                self._langfuse = Langfuse(
                    public_key=config.langfuse_public_key,
                    secret_key=config.langfuse_secret_key,
                    host=config.langfuse_host,
                )
            except ImportError:
                logger.warning("langfuse not installed; tracing disabled")
            except Exception as e:
                logger.warning("Langfuse init failed: %s", e)
        try:
            import litellm
            litellm.drop_params = True
        except ImportError:
            pass

    def _route_model(self, task_type: str | None) -> tuple[str, ModelConfig, list[str]]:
        """Route task_type to model name, ModelConfig, and fallback list."""
        fallback: list[str] = []
        if task_type:
            for routing in self.config.task_type_routing:
                if routing.task_type == task_type:
                    model_name = routing.model
                    if model_name not in self.config.models:
                        raise ValueError(f"Unknown model '{model_name}' in task_type_routing")
                    return model_name, self.config.models[model_name], list(routing.fallback_models)
        model_name = self.config.default_model
        if model_name not in self.config.models:
            raise ValueError(f"Default model '{model_name}' not in config.models")
        return model_name, self.config.models[model_name], fallback

    def _wrap_litellm_error(self, e: Exception, model: str) -> LLMError:
        """Map litellm exception to OwlClaw LLM error and log details."""
        msg = str(e)
        err_name = type(e).__name__
        msg_lower = msg.lower()
        logger.warning(
            "LLM call failed model=%s error_type=%s message=%s",
            model,
            err_name,
            msg[:200] + ("..." if len(msg) > 200 else ""),
        )
        if "Authentication" in err_name or "authentication" in msg_lower or ("invalid" in msg_lower and "api" in msg_lower and "key" in msg_lower):
            return AuthenticationError(msg, model=model, cause=e)
        if "RateLimit" in err_name or "rate_limit" in msg_lower or "too many requests" in msg_lower:
            return RateLimitError(msg, model=model, cause=e)
        if "ContextWindow" in err_name or ("context" in msg_lower and "window" in msg_lower):
            return ContextWindowExceededError(msg, model=model, cause=e)
        if "ServiceUnavailable" in err_name or "503" in msg or "unavailable" in msg_lower:
            return ServiceUnavailableError(msg, model=model, cause=e)
        return ServiceUnavailableError(
            f"LLM call failed: {msg}", model=model, cause=e
        )

    async def _call_with_fallback(
        self,
        params: dict[str, Any],
        fallback_models: list[str],
    ) -> Any:
        """Call litellm; on failure try fallback models. Wraps litellm exceptions as OwlClaw errors."""
        models_to_try = [params["model"]] + fallback_models
        last_error: Exception | None = None
        last_model = ""
        for attempt, model in enumerate(models_to_try):
            last_model = model
            try:
                call_params = {**params, "model": model}
                return await acompletion(**call_params)
            except Exception as e:
                last_error = e
                err_name = type(e).__name__
                if (
                    "RateLimit" in err_name or "rate_limit" in str(e).lower()
                ) and attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay_seconds)
                    continue
                if "Authentication" in err_name or "InvalidApiKey" in err_name:
                    raise self._wrap_litellm_error(e, model) from e
                if attempt < len(models_to_try) - 1:
                    logger.warning("Model %s failed, trying fallback: %s", model, e)
                    continue
        if last_error:
            raise self._wrap_litellm_error(last_error, last_model) from last_error
        raise ServiceUnavailableError("All models failed", model=last_model)

    def _parse_response(self, response: Any, model: str) -> LLMResponse:
        """Parse litellm response into LLMResponse."""
        choice = response.choices[0]
        message = choice.message
        function_calls: list[dict[str, Any]] = []
        tool_calls = getattr(message, "tool_calls", None) or []
        for tc in tool_calls:
            name = getattr(getattr(tc, "function", None), "name", "unknown")
            args_raw = getattr(getattr(tc, "function", None), "arguments", "{}")
            try:
                args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
            except json.JSONDecodeError:
                args = {}
            function_calls.append({
                "id": getattr(tc, "id", ""),
                "name": name,
                "arguments": args,
            })
        usage = getattr(response, "usage", None)
        prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
        mc = self.config.models.get(model)
        cost = 0.0
        if mc:
            cost = (
                prompt_tokens / 1000 * mc.cost_per_1k_prompt_tokens
                + completion_tokens / 1000 * mc.cost_per_1k_completion_tokens
            )
        return LLMResponse(
            content=getattr(message, "content", None) or None,
            function_calls=function_calls,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost=round(cost, 6),
        )

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        task_type: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stream: bool = False,
    ) -> LLMResponse:
        """Complete LLM call with routing and fallback."""
        if self.config.mock_mode and self.config.mock_responses:
            key = task_type or "default"
            content = self.config.mock_responses.get(key, self.config.mock_responses.get("default", ""))
            return LLMResponse(
                content=content,
                function_calls=[],
                model="mock",
                prompt_tokens=0,
                completion_tokens=0,
                cost=0.0,
            )
        model_name, model_config, fallback = self._route_model(task_type)
        temp = temperature if temperature is not None else model_config.temperature
        max_tok = max_tokens if max_tokens is not None else model_config.max_tokens
        params: dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "temperature": temp,
            "max_tokens": max_tok,
        }
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"
        trace: Any = None
        if self._langfuse:
            try:
                trace = self._langfuse.trace(
                    name="llm_call",
                    metadata={"task_type": task_type, "model": model_name},
                )
            except Exception as e:
                logger.warning("Langfuse trace create failed: %s", e)
        try:
            response = await self._call_with_fallback(params, fallback)
            llm_resp = self._parse_response(response, model_name)
            if trace:
                try:
                    trace.generation(
                        name="completion",
                        model=model_name,
                        input=messages,
                        output=llm_resp.content or llm_resp.function_calls,
                        usage={
                            "prompt_tokens": llm_resp.prompt_tokens,
                            "completion_tokens": llm_resp.completion_tokens,
                            "total_tokens": llm_resp.total_tokens,
                        },
                        metadata={"cost": llm_resp.cost},
                    )
                except Exception as e:
                    logger.warning("Langfuse generation record failed: %s", e)
            return llm_resp
        except Exception as e:
            if trace:
                with contextlib.suppress(Exception):
                    trace.update(status="error", output=str(e))
            raise
