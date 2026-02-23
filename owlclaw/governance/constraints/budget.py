"""Budget constraint: hide high-cost capabilities when agent budget is exhausted."""

from datetime import date
from decimal import Decimal
from decimal import InvalidOperation

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
        remaining = limit_decimal - used_cost

        if remaining <= 0:
            estimated_cost = self._estimate_capability_cost(capability)
            if estimated_cost > self.high_cost_threshold:
                return FilterResult(
                    visible=False,
                    reason=(
                        f"Budget exhausted (used {used_cost}, limit {budget_limit})"
                    ),
                )
        return FilterResult(visible=True)

    def _estimate_capability_cost(self, capability: CapabilityView) -> Decimal:
        """Estimate single-call cost from metadata or default."""
        owlclaw = capability.metadata.get("owlclaw") or {}
        constraints = owlclaw.get("constraints") or {}
        raw = constraints.get("estimated_cost")
        if raw is not None:
            return self._safe_decimal(raw, default=Decimal("0.05"))
        return Decimal("0.05")
