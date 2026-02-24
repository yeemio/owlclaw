from __future__ import annotations

import asyncio

from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.triggers.webhook import AuthMethod, EndpointConfig, WebhookEndpointManager
from owlclaw.triggers.webhook.persistence.repositories import InMemoryEndpointRepository


def _config(name: str, target_agent_id: str = "agent-1") -> EndpointConfig:
    return EndpointConfig(name=name, target_agent_id=target_agent_id, auth_method=AuthMethod(type="bearer", token="t"))


@given(
    endpoint_name=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_", min_size=1, max_size=16),
)
@settings(max_examples=30, deadline=None)
def test_property_endpoint_creation_generates_unique_identity(endpoint_name: str) -> None:
    """Feature: triggers-webhook, Property 1: 端点创建生成唯一标识和完整配置."""

    async def _run() -> None:
        manager = WebhookEndpointManager(InMemoryEndpointRepository())
        endpoint1 = await manager.create_endpoint(_config(endpoint_name))
        endpoint2 = await manager.create_endpoint(_config(f"{endpoint_name}-2"))
        assert endpoint1.id != endpoint2.id
        assert endpoint1.url != endpoint2.url
        assert endpoint1.auth_token != endpoint2.auth_token
        assert endpoint1.config.name == endpoint_name

    asyncio.run(_run())


@given(
    names=st.lists(
        st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_", min_size=1, max_size=12),
        min_size=1,
        max_size=12,
        unique=True,
    )
)
@settings(max_examples=25, deadline=None)
def test_property_endpoint_query_returns_all_registered(names: list[str]) -> None:
    """Feature: triggers-webhook, Property 2: 端点查询返回所有已注册端点."""

    async def _run() -> None:
        manager = WebhookEndpointManager(InMemoryEndpointRepository())
        for name in names:
            await manager.create_endpoint(_config(name))
        listed = await manager.list_endpoints()
        assert {item.config.name for item in listed} == set(names)

    asyncio.run(_run())


@given(
    old_name=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_", min_size=1, max_size=12),
    new_name=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_", min_size=1, max_size=12),
)
@settings(max_examples=30, deadline=None)
def test_property_endpoint_update_is_persisted(old_name: str, new_name: str) -> None:
    """Feature: triggers-webhook, Property 3: 端点更新验证和持久化."""

    async def _run() -> None:
        manager = WebhookEndpointManager(InMemoryEndpointRepository())
        created = await manager.create_endpoint(_config(old_name))
        updated = await manager.update_endpoint(created.id, _config(new_name))
        fetched = await manager.get_endpoint(created.id)
        assert updated.config.name == new_name
        assert fetched is not None
        assert fetched.config.name == new_name

    asyncio.run(_run())


@given(
    endpoint_name=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_", min_size=1, max_size=16),
)
@settings(max_examples=30, deadline=None)
def test_property_endpoint_delete_makes_it_inaccessible(endpoint_name: str) -> None:
    """Feature: triggers-webhook, Property 4: 端点删除后不可访问."""

    async def _run() -> None:
        manager = WebhookEndpointManager(InMemoryEndpointRepository())
        created = await manager.create_endpoint(_config(endpoint_name))
        await manager.delete_endpoint(created.id)
        fetched = await manager.get_endpoint(created.id)
        listed = await manager.list_endpoints()
        assert fetched is None
        assert all(item.id != created.id for item in listed)

    asyncio.run(_run())
