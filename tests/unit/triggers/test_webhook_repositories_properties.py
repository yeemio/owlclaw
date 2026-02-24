from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.triggers.webhook.persistence.models import WebhookEndpointModel, WebhookEventModel
from owlclaw.triggers.webhook.persistence.repositories import InMemoryEndpointRepository, InMemoryEventRepository


@given(
    endpoint_names=st.lists(
        st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_", min_size=1, max_size=12),
        min_size=1,
        max_size=20,
        unique=True,
    )
)
@settings(max_examples=30, deadline=None)
def test_property_endpoint_query_returns_all_registered_endpoints(endpoint_names: list[str]) -> None:
    """Feature: triggers-webhook, Property 2: 端点查询返回所有已注册端点."""

    async def _run() -> None:
        repo = InMemoryEndpointRepository()
        created_ids = set()
        now = datetime.now(timezone.utc)
        for name in endpoint_names:
            model = WebhookEndpointModel(
                id=uuid4(),
                tenant_id="default",
                name=name,
                url=f"https://example.com/{name}",
                auth_token=f"token-{name}",
                target_agent_id="agent-1",
                auth_method={"type": "bearer"},
                enabled=True,
                created_at=now,
                updated_at=now,
            )
            await repo.create(model)
            created_ids.add(model.id)
        listed = await repo.list(tenant_id="default")
        assert {item.id for item in listed} == created_ids

    import asyncio

    asyncio.run(_run())


@given(
    steps=st.lists(st.integers(min_value=1, max_value=99), min_size=1, max_size=20),
)
@settings(max_examples=30, deadline=None)
def test_property_event_log_persistence_roundtrip(steps: list[int]) -> None:
    """Feature: triggers-webhook, Property 22: 事件日志持久化往返."""

    async def _run() -> None:
        repo = InMemoryEventRepository()
        endpoint_id = uuid4()
        request_id = "req-roundtrip"
        base = datetime.now(timezone.utc)
        for index, step in enumerate(steps):
            await repo.create(
                WebhookEventModel(
                    id=uuid4(),
                    tenant_id="default",
                    endpoint_id=endpoint_id,
                    event_type="request",
                    timestamp=base + timedelta(seconds=index),
                    request_id=request_id,
                    data={"step": step},
                )
            )
        loaded = await repo.list_by_request_id(tenant_id="default", request_id=request_id)
        assert [item.data["step"] for item in loaded] == steps

    import asyncio

    asyncio.run(_run())
