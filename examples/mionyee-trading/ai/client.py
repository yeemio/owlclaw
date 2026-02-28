"""Mionyee-side LLM client wrapped by OwlClaw governance proxy."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from owlclaw.governance.proxy import GovernanceProxy


class MionyeeAIClient:
    """Equivalent entrypoint for mionyee ai/client.py with governance wrapping."""

    def __init__(
        self,
        *,
        proxy: GovernanceProxy,
        default_model: str = "gpt-4o-mini",
        caller_prefix: str = "mionyee.ai",
    ) -> None:
        self.proxy = proxy
        self.default_model = default_model
        self.caller_prefix = caller_prefix.strip(".")

    @classmethod
    def from_config(
        cls,
        config_path: str | Path,
        *,
        default_model: str = "gpt-4o-mini",
        caller_prefix: str = "mionyee.ai",
    ) -> MionyeeAIClient:
        """Build a governed client from owlclaw.yaml."""
        proxy = GovernanceProxy.from_config(str(config_path))
        return cls(proxy=proxy, default_model=default_model, caller_prefix=caller_prefix)

    async def acompletion(
        self,
        *,
        service: str,
        messages: list[dict[str, Any]],
        model: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Replace direct litellm call with GovernanceProxy-acompletion."""
        normalized_service = service.strip().replace(" ", "_")
        if not normalized_service:
            raise ValueError("service must be a non-empty string")
        caller = f"{self.caller_prefix}.{normalized_service}"
        return await self.proxy.acompletion(
            model=model or self.default_model,
            messages=messages,
            caller=caller,
            **kwargs,
        )
