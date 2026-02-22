"""External integrations — Hatchet, litellm, Langfuse (isolated layer)."""

from owlclaw.integrations.hatchet import HatchetClient, HatchetConfig
from owlclaw.integrations.llm import (
    AuthenticationError,
    ContextWindowExceededError,
    LLMClient,
    LLMConfig,
    LLMResponse,
    PromptBuilder,
    RateLimitError,
    ServiceUnavailableError,
    TokenEstimator,
    ToolsConverter,
    acompletion,
)

__all__ = [
    "HatchetClient",
    "HatchetConfig",
    "acompletion",
    "AuthenticationError",
    "ContextWindowExceededError",
    "LLMClient",
    "LLMConfig",
    "LLMResponse",
    "PromptBuilder",
    "RateLimitError",
    "ServiceUnavailableError",
    "TokenEstimator",
    "ToolsConverter",
]
