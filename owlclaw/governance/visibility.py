"""Capability visibility filter and constraint evaluator protocol.

Filters capabilities before they are presented to the LLM, based on
constraints (budget, time, rate limit, circuit breaker). Evaluators
run in parallel; failures are fail-open (capability remains visible).
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Protocol

logger = logging.getLogger(__name__)


@dataclass
class FilterResult:
    """Result of a single constraint evaluation."""

    visible: bool
    reason: str = ""


@dataclass
class RunContext:
    """Context passed to constraint evaluators (tenant, optional extras)."""

    tenant_id: str


class CapabilityView:
    """Read-only view of a capability for constraint evaluation.

    Matches the shape produced by CapabilityRegistry.list_capabilities()
    and Skill metadata (name, task_type, constraints from owlclaw_config).
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        task_type: str | None = None,
        constraints: dict[str, Any] | None = None,
        focus: list[str] | None = None,
        risk_level: str | None = None,
        requires_confirmation: bool | None = None,
    ):
        self.name = name
        self.description = description
        self.task_type = task_type or ""
        self.constraints = constraints or {}
        self.focus = focus or []
        self.risk_level = risk_level or "low"
        self.requires_confirmation = bool(requires_confirmation)

    @property
    def metadata(self) -> dict[str, Any]:
        """OwlClaw metadata for constraints (design: capability.metadata.get('owlclaw', {}).get('constraints')."""
        return {
            "owlclaw": {
                "constraints": self.constraints,
                "task_type": self.task_type,
                "focus": self.focus,
                "risk_level": self.risk_level,
                "requires_confirmation": self.requires_confirmation,
            }
        }


class ConstraintEvaluator(Protocol):
    """Protocol for constraint evaluators used by VisibilityFilter."""

    async def evaluate(
        self,
        capability: CapabilityView,
        agent_id: str,
        context: RunContext,
    ) -> FilterResult:
        """Evaluate whether the capability should be visible. Must not raise."""
        ...


class VisibilityFilter:
    """Filters capabilities using registered constraint evaluators.

    All evaluators must return visible=True for a capability to be shown.
    Evaluators are run in parallel per capability; any evaluator exception
    is fail-open (capability remains visible) and logged.
    """

    def __init__(self) -> None:
        self._evaluators: list[ConstraintEvaluator] = []

    def register_evaluator(self, evaluator: ConstraintEvaluator) -> None:
        """Register a constraint evaluator."""
        if not hasattr(evaluator, "evaluate") or not callable(evaluator.evaluate):
            raise TypeError("evaluator must provide an async evaluate(capability, agent_id, context) method")
        self._evaluators.append(evaluator)

    async def filter_capabilities(
        self,
        capabilities: list[CapabilityView],
        agent_id: str,
        context: RunContext,
    ) -> list[CapabilityView]:
        """Return only capabilities that pass all evaluators.

        For each capability, evaluators run in parallel. If any evaluator
        raises, that capability is treated as visible (fail-open).
        """
        if not self._evaluators:
            return list(capabilities)

        filtered: list[CapabilityView] = []
        for cap in capabilities:
            results = await asyncio.gather(
                *(
                    self._safe_evaluate(eval_fn, cap, agent_id, context)
                    for eval_fn in self._evaluators
                )
            )
            reasons: list[str] = []
            for r in results:
                if not r.visible:
                    reasons.append(r.reason)
            if reasons:
                logger.info(
                    "Capability %s filtered: %s",
                    cap.name,
                    "; ".join(reasons),
                )
                continue
            filtered.append(cap)
        return filtered

    async def _safe_evaluate(
        self,
        evaluator: ConstraintEvaluator,
        capability: CapabilityView,
        agent_id: str,
        context: RunContext,
    ) -> FilterResult:
        """Run one evaluator; on exception return visible (fail-open)."""
        try:
            return await evaluator.evaluate(capability, agent_id, context)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(
                "Evaluator %s raised (fail-open): %s",
                type(evaluator).__name__,
                e,
            )
            return FilterResult(visible=True)
