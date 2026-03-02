"""Default providers for console backend."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from owlclaw.web.providers.overview import DefaultOverviewProvider


class _EmptyGovernanceProvider:
    async def get_budget_trend(
        self,
        tenant_id: str,
        start_date: Any,
        end_date: Any,
        granularity: str,
    ) -> list[dict[str, Any]]:
        _ = (tenant_id, start_date, end_date, granularity)
        return []

    async def get_circuit_breaker_states(self, tenant_id: str) -> list[dict[str, Any]]:
        _ = tenant_id
        return []

    async def get_visibility_matrix(self, tenant_id: str, agent_id: str | None) -> dict[str, Any]:
        _ = (tenant_id, agent_id)
        return {"items": []}


class _EmptyTriggersProvider:
    async def list_triggers(self, tenant_id: str) -> list[dict[str, Any]]:
        _ = tenant_id
        return []

    async def get_trigger_history(
        self,
        trigger_id: str,
        tenant_id: str,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        _ = (trigger_id, tenant_id, limit, offset)
        return [], 0


class _EmptyAgentsProvider:
    async def list_agents(self, tenant_id: str) -> list[dict[str, Any]]:
        _ = tenant_id
        return []

    async def get_agent_detail(self, agent_id: str, tenant_id: str) -> dict[str, Any] | None:
        _ = (agent_id, tenant_id)
        return None


class _EmptyCapabilitiesProvider:
    async def list_capabilities(
        self,
        tenant_id: str,
        category: str | None,
    ) -> list[dict[str, Any]]:
        _ = (tenant_id, category)
        return []

    async def get_capability_schema(self, capability_name: str) -> dict[str, Any] | None:
        _ = capability_name
        return None


class _EmptyLedgerProvider:
    async def query_records(
        self,
        tenant_id: str,
        agent_id: str | None,
        capability_name: str | None,
        status: str | None,
        start_date: Any,
        end_date: Any,
        limit: int,
        offset: int,
        order_by: str | None,
    ) -> tuple[list[dict[str, Any]], int]:
        _ = (
            tenant_id,
            agent_id,
            capability_name,
            status,
            start_date,
            end_date,
            limit,
            offset,
            order_by,
        )
        return [], 0

    async def get_record_detail(self, record_id: str, tenant_id: str) -> dict[str, Any] | None:
        _ = (record_id, tenant_id)
        return None


class _EmptySettingsProvider:
    async def get_settings(self, tenant_id: str) -> dict[str, Any]:
        _ = tenant_id
        return {"console": {"enabled": True}}

    async def get_system_info(self) -> dict[str, Any]:
        return {
            "version": "unknown",
            "build_time": datetime.now(timezone.utc).isoformat(),
        }


def create_default_provider_bundle() -> dict[str, Any]:
    """Create default provider set for API bootstrap."""
    return {
        "overview": DefaultOverviewProvider(),
        "governance": _EmptyGovernanceProvider(),
        "triggers": _EmptyTriggersProvider(),
        "agents": _EmptyAgentsProvider(),
        "capabilities": _EmptyCapabilitiesProvider(),
        "ledger": _EmptyLedgerProvider(),
        "settings": _EmptySettingsProvider(),
    }


__all__ = ["DefaultOverviewProvider", "create_default_provider_bundle"]
