"""Model router: select LLM model by task_type with fallback chain."""

import logging
from dataclasses import dataclass

from owlclaw.governance.visibility import RunContext

logger = logging.getLogger(__name__)


@dataclass
class ModelSelection:
    """Selected model and its fallback chain."""

    model: str
    fallback: list[str]


class Router:
    """Selects LLM model by task_type; supports fallback on failure."""

    def __init__(self, config: dict) -> None:
        self._rules = config.get("rules", [])
        self._default_model = config.get("default_model", "gpt-4o-mini")

    async def select_model(
        self,
        task_type: str,
        context: RunContext,
    ) -> ModelSelection:
        """Return model and fallback chain for the given task_type."""
        for rule in self._rules:
            if rule.get("task_type") == task_type:
                return ModelSelection(
                    model=rule.get("model", self._default_model),
                    fallback=rule.get("fallback", []),
                )
        return ModelSelection(model=self._default_model, fallback=[])

    async def handle_model_failure(
        self,
        failed_model: str,
        task_type: str,
        error: Exception,
        fallback_chain: list[str],
    ) -> str | None:
        """Return next model from fallback chain, or None if exhausted."""
        if not fallback_chain:
            return None
        next_model = fallback_chain[0]
        logger.warning(
            "Model %s failed for task_type %s, falling back to %s: %s",
            failed_model,
            task_type,
            next_model,
            error,
        )
        return next_model
