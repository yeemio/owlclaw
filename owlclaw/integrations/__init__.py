"""External integrations — Hatchet, litellm, Langfuse (isolated layer)."""

from owlclaw.integrations.hatchet import HatchetClient, HatchetConfig
from owlclaw.integrations.llm import (
    AuthenticationError,
    ContextWindowExceededError,
    LLMClient,
    LLMConfig,
    LLMResponse,
    RateLimitError,
    ServiceUnavailableError,
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
    "RateLimitError",
    "ServiceUnavailableError",
]
