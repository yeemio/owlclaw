"""Capability visibility filter and constraint evaluator protocol.

Filters capabilities before they are presented to the LLM, based on
constraints (budget, time, rate limit, circuit breaker). Evaluators
run in parallel; failures are fail-open (capability remains visible).
"""

import asyncio
import inspect
import logging
from dataclasses import dataclass
from typing import Any, Protocol

logger = logging.getLogger(__name__)


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return False


def _coerce_focus(value: Any) -> list[str]:
    if isinstance(value, str):
        v = value.strip()
        return [v] if v else []
    if isinstance(value, list):
        out: list[str] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                continue
            normalized = item.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            out.append(normalized)
        return out
    return []


def _coerce_risk_level(value: Any) -> str:
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"low", "medium", "high", "critical"}:
            return normalized
    return "low"


@dataclass
class FilterResult:
    """Result of a single constraint evaluation."""

    visible: bool
    reason: str = ""


@dataclass
class RunContext:
    """Context passed to constraint evaluators (tenant, optional extras)."""

    tenant_id: str
    confirmed_capabilities: set[str] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.tenant_id, str) or not self.tenant_id.strip():
            raise ValueError("tenant_id must be a non-empty string")
        self.tenant_id = self.tenant_id.strip()
        if self.confirmed_capabilities is None:
            return
        self.confirmed_capabilities = {
            str(name).strip()
            for name in self.confirmed_capabilities
            if str(name).strip()
        } or None

    def is_confirmed(self, capability_name: str) -> bool:
        if not self.confirmed_capabilities:
            return False
        if not isinstance(capability_name, str):
            return False
        normalized = capability_name.strip()
        if not normalized:
            return False
        return normalized in self.confirmed_capabilities


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
        self.focus = _coerce_focus(focus)
        self.risk_level = _coerce_risk_level(risk_level)
        self.requires_confirmation = _coerce_bool(requires_confirmation)

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
        valid_capabilities: list[CapabilityView] = []
        for cap in capabilities:
            if isinstance(cap, CapabilityView):
                valid_capabilities.append(cap)
            else:
                logger.warning("Skipping invalid capability entry of type %s", type(cap).__name__)
        if not self._evaluators:
            return list(valid_capabilities)

        filtered: list[CapabilityView] = []
        for cap in valid_capabilities:
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
            result = evaluator.evaluate(capability, agent_id, context)
            if inspect.isawaitable(result):
                result = await result
            if isinstance(result, FilterResult):
                return result
            logger.warning(
                "Evaluator %s returned invalid result type %s (fail-open)",
                type(evaluator).__name__,
                type(result).__name__,
            )
            return FilterResult(visible=True)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(
                "Evaluator %s raised (fail-open): %s",
                type(evaluator).__name__,
                e,
            )
            return FilterResult(visible=True)
