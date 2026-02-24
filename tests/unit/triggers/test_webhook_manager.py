from __future__ import annotations

import asyncio

import pytest

from owlclaw.triggers.webhook import AuthMethod, EndpointConfig, EndpointFilter, RetryPolicy, WebhookEndpointManager
from owlclaw.triggers.webhook.persistence.repositories import InMemoryEndpointRepository


def _valid_config(name: str = "orders", *, enabled: bool = True, target_agent_id: str = "agent-1") -> EndpointConfig:
    return EndpointConfig(
        name=name,
        target_agent_id=target_agent_id,
        auth_method=AuthMethod(type="bearer", token="token-1"),
        retry_policy=RetryPolicy(max_attempts=3),
        enabled=enabled,
    )


@pytest.mark.asyncio
async def test_manager_rejects_invalid_config() -> None:
    manager = WebhookEndpointManager(InMemoryEndpointRepository())
    config = EndpointConfig(name="", target_agent_id="", auth_method=AuthMethod(type="bearer", token=None))

    with pytest.raises(ValueError, match="name is required"):
        await manager.create_endpoint(config)


@pytest.mark.asyncio
async def test_manager_concurrent_create_generates_unique_ids() -> None:
    manager = WebhookEndpointManager(InMemoryEndpointRepository())

    async def _create(index: int) -> str:
        endpoint = await manager.create_endpoint(_valid_config(name=f"n-{index}"))
        return endpoint.id

    ids = await asyncio.gather(*[_create(i) for i in range(20)])
    assert len(set(ids)) == 20


@pytest.mark.asyncio
async def test_manager_list_with_filters() -> None:
    manager = WebhookEndpointManager(InMemoryEndpointRepository())
    ep1 = await manager.create_endpoint(_valid_config(name="a", target_agent_id="agent-a", enabled=True))
    await manager.create_endpoint(_valid_config(name="b", target_agent_id="agent-a", enabled=False))
    await manager.create_endpoint(_valid_config(name="c", target_agent_id="agent-c", enabled=True))

    by_agent = await manager.list_endpoints(EndpointFilter(tenant_id="default", target_agent_id="agent-a"))
    enabled_only = await manager.list_endpoints(EndpointFilter(tenant_id="default", enabled=True))

    assert {item.config.name for item in by_agent} == {"a", "b"}
    assert {item.config.name for item in enabled_only} == {"a", "c"}
    fetched = await manager.get_endpoint(ep1.id)
    assert fetched is not None
    assert fetched.config.target_agent_id == "agent-a"
