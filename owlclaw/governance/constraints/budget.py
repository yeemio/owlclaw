"""Budget constraint: hide high-cost capabilities when agent budget is exhausted."""

import asyncio
from datetime import date
from decimal import Decimal, InvalidOperation

from owlclaw.governance.ledger import Ledger
from owlclaw.governance.visibility import CapabilityView, FilterResult, RunContext


class BudgetConstraint:
    """Evaluates visibility based on agent budget and capability cost."""

    def __init__(self, ledger: Ledger, config: dict | None = None) -> None:
        config = config or {}
        self.ledger = ledger
        self.high_cost_threshold = self._safe_decimal(
            config.get("high_cost_threshold"),
            default=Decimal("0.1"),
        )
        self.budget_limits: dict[str, str | Decimal] = config.get(
            "budget_limits", {}
        )
        ttl_raw = config.get("reservation_ttl_seconds", 60.0)
        try:
            self._reservation_ttl_seconds = max(0.0, float(ttl_raw))
        except (TypeError, ValueError):
            self._reservation_ttl_seconds = 60.0
        self._reservation_lock = asyncio.Lock()
        self._reserved_by_agent: dict[tuple[str, str], list[tuple[Decimal, float]]] = {}

    @staticmethod
    def _safe_decimal(value: object, *, default: Decimal) -> Decimal:
        if value is None:
            return default
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return default

    async def evaluate(
        self,
        capability: CapabilityView,
        agent_id: str,
        context: RunContext,
    ) -> FilterResult:
        """Allow capability if budget is sufficient or capability is low-cost."""
        budget_limit = self.budget_limits.get(agent_id)
        if not budget_limit:
            return FilterResult(visible=True)

        start_of_month = date.today().replace(day=1)
        end_date = date.today()
        cost_summary = await self.ledger.get_cost_summary(
            tenant_id=context.tenant_id,
            agent_id=agent_id,
            start_date=start_of_month,
            end_date=end_date,
        )
        used_cost = cost_summary.total_cost
        limit_decimal = self._safe_decimal(budget_limit, default=Decimal("0"))
        estimated_cost = self._estimate_capability_cost(capability)
        if estimated_cost <= self.high_cost_threshold:
            return FilterResult(visible=True)

        reserve_key = (context.tenant_id, agent_id)
        async with self._reservation_lock:
            self._cleanup_expired_reservations(reserve_key)
            reserved = self._reserved_total(reserve_key)
            remaining = limit_decimal - used_cost - reserved
            if remaining < estimated_cost:
                return FilterResult(
                    visible=False,
                    reason=(
                        "budget_insufficient_after_reservation "
                        f"(used {used_cost}, reserved {reserved}, limit {budget_limit})"
                    ),
                )
            self._reserve_budget(reserve_key, estimated_cost)
        return FilterResult(visible=True)

    def _estimate_capability_cost(self, capability: CapabilityView) -> Decimal:
        """Estimate single-call cost from metadata or default."""
        owlclaw = capability.metadata.get("owlclaw") or {}
        constraints = owlclaw.get("constraints") or {}
        raw = constraints.get("estimated_cost")
        if raw is not None:
            return self._safe_decimal(raw, default=Decimal("0.05"))
        return Decimal("0.05")

    def _cleanup_expired_reservations(self, reserve_key: tuple[str, str]) -> None:
        now = asyncio.get_running_loop().time()
        kept = [
            (amount, expires_at)
            for amount, expires_at in self._reserved_by_agent.get(reserve_key, [])
            if expires_at > now
        ]
        if kept:
            self._reserved_by_agent[reserve_key] = kept
            return
        self._reserved_by_agent.pop(reserve_key, None)

    def _reserved_total(self, reserve_key: tuple[str, str]) -> Decimal:
        reservations = self._reserved_by_agent.get(reserve_key, [])
        return sum((amount for amount, _ in reservations), Decimal("0"))

    def _reserve_budget(self, reserve_key: tuple[str, str], amount: Decimal) -> None:
        expires_at = asyncio.get_running_loop().time() + self._reservation_ttl_seconds
        self._reserved_by_agent.setdefault(reserve_key, []).append((amount, expires_at))
