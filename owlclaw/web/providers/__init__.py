"""Default providers for console backend."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from owlclaw.web.providers.governance import DefaultGovernanceProvider
from owlclaw.web.providers.ledger import DefaultLedgerProvider
from owlclaw.web.providers.overview import DefaultOverviewProvider


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
        "governance": DefaultGovernanceProvider(),
        "triggers": _EmptyTriggersProvider(),
        "agents": _EmptyAgentsProvider(),
        "capabilities": _EmptyCapabilitiesProvider(),
        "ledger": DefaultLedgerProvider(),
        "settings": _EmptySettingsProvider(),
    }


__all__ = ["DefaultOverviewProvider", "DefaultGovernanceProvider", "DefaultLedgerProvider", "create_default_provider_bundle"]
