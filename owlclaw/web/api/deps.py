"""Dependency injection registry for console API providers."""

from __future__ import annotations

from typing import Any, cast

from fastapi import Header

from owlclaw.web.contracts import (
    AgentsProvider,
    CapabilitiesProvider,
    GovernanceProvider,
    LedgerProvider,
    OverviewProvider,
    SettingsProvider,
    TriggersProvider,
)

_PROVIDERS: dict[str, Any] = {}


def set_providers(**providers: Any) -> None:
    """Register provider instances used by FastAPI dependencies."""
    _PROVIDERS.update(providers)


def clear_providers() -> None:
    """Clear provider registry, mainly for tests."""
    _PROVIDERS.clear()


def _get_provider(name: str) -> Any:
    provider = _PROVIDERS.get(name)
    if provider is None:
        raise RuntimeError(f"Provider '{name}' is not registered.")
    return provider


async def get_overview_provider() -> OverviewProvider:
    return cast(OverviewProvider, _get_provider("overview"))


async def get_governance_provider() -> GovernanceProvider:
    return cast(GovernanceProvider, _get_provider("governance"))


async def get_triggers_provider() -> TriggersProvider:
    return cast(TriggersProvider, _get_provider("triggers"))


async def get_agents_provider() -> AgentsProvider:
    return cast(AgentsProvider, _get_provider("agents"))


async def get_capabilities_provider() -> CapabilitiesProvider:
    return cast(CapabilitiesProvider, _get_provider("capabilities"))


async def get_ledger_provider() -> LedgerProvider:
    return cast(LedgerProvider, _get_provider("ledger"))


async def get_settings_provider() -> SettingsProvider:
    return cast(SettingsProvider, _get_provider("settings"))


async def get_tenant_id(x_owlclaw_tenant: str | None = Header(default=None)) -> str:
    """Extract tenant id from request header with default fallback.

    Note:
        This header-based fallback is suitable for single-tenant/self-hosted usage.
        In multi-tenant production deployments, tenant_id should come from
        authenticated request context, not directly from client headers.
    """
    if x_owlclaw_tenant is None or not x_owlclaw_tenant.strip():
        return "default"
    return x_owlclaw_tenant.strip()

