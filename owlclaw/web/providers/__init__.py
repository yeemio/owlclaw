"""Default providers for console backend."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from owlclaw.web.providers.capabilities import DefaultCapabilitiesProvider
from owlclaw.web.providers.governance import DefaultGovernanceProvider
from owlclaw.web.providers.ledger import DefaultLedgerProvider
from owlclaw.web.providers.overview import DefaultOverviewProvider
from owlclaw.web.providers.triggers import DefaultTriggersProvider


class _EmptyAgentsProvider:
    async def list_agents(self, tenant_id: str) -> list[dict[str, Any]]:
        _ = tenant_id
        return []

    async def get_agent_detail(self, agent_id: str, tenant_id: str) -> dict[str, Any] | None:
        _ = (agent_id, tenant_id)
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
        "triggers": DefaultTriggersProvider(),
        "agents": _EmptyAgentsProvider(),
        "capabilities": DefaultCapabilitiesProvider(),
        "ledger": DefaultLedgerProvider(),
        "settings": _EmptySettingsProvider(),
    }


__all__ = [
    "DefaultOverviewProvider",
    "DefaultGovernanceProvider",
    "DefaultCapabilitiesProvider",
    "DefaultLedgerProvider",
    "DefaultTriggersProvider",
    "create_default_provider_bundle",
]
