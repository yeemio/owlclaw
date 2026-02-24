from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from owlclaw.triggers.webhook.persistence.models import (
    WebhookEndpointModel,
    WebhookEventModel,
    WebhookExecutionModel,
    WebhookIdempotencyKeyModel,
    WebhookTransformationRuleModel,
)
from owlclaw.triggers.webhook.persistence.repositories import (
    InMemoryEndpointRepository,
    InMemoryEventRepository,
    InMemoryExecutionRepository,
    InMemoryIdempotencyRepository,
    InMemoryTransformationRuleRepository,
)


def _endpoint(name: str, *, tenant_id: str = "default", enabled: bool = True) -> WebhookEndpointModel:
    now = datetime.now(timezone.utc)
    return WebhookEndpointModel(
        id=uuid4(),
        tenant_id=tenant_id,
        name=name,
        url=f"https://example.com/{name}",
        auth_token=f"token-{name}",
        target_agent_id="agent-1",
        auth_method={"type": "bearer"},
        enabled=enabled,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_inmemory_endpoint_repository_create_and_list() -> None:
    repo = InMemoryEndpointRepository()
    ep1 = _endpoint("e1")
    ep2 = _endpoint("e2", enabled=False)
    ep3 = _endpoint("e3", tenant_id="tenant-b")
    await repo.create(ep1)
    await repo.create(ep2)
    await repo.create(ep3)

    default_items = await repo.list(tenant_id="default")
    enabled_items = await repo.list(tenant_id="default", enabled=True)

    assert {item.id for item in default_items} == {ep1.id, ep2.id}
    assert [item.id for item in enabled_items] == [ep1.id]


@pytest.mark.asyncio
async def test_inmemory_event_repository_roundtrip_by_request_id() -> None:
    repo = InMemoryEventRepository()
    endpoint_id = uuid4()
    first = WebhookEventModel(
        id=uuid4(),
        tenant_id="default",
        endpoint_id=endpoint_id,
        event_type="request",
        timestamp=datetime.now(timezone.utc),
        request_id="req-1",
        data={"step": 1},
    )
    second = WebhookEventModel(
        id=uuid4(),
        tenant_id="default",
        endpoint_id=endpoint_id,
        event_type="execution",
        timestamp=datetime.now(timezone.utc) + timedelta(seconds=1),
        request_id="req-1",
        data={"step": 2},
    )
    await repo.create(first)
    await repo.create(second)

    found = await repo.list_by_request_id(tenant_id="default", request_id="req-1")
    assert [item.data for item in found] == [{"step": 1}, {"step": 2}]


@pytest.mark.asyncio
async def test_inmemory_idempotency_repository_upsert_and_get() -> None:
    repo = InMemoryIdempotencyRepository()
    item = WebhookIdempotencyKeyModel(
        key="idem-1",
        tenant_id="default",
        endpoint_id=uuid4(),
        execution_id=uuid4(),
        result={"status": "ok"},
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    await repo.upsert(item)
    found = await repo.get("idem-1")

    assert found is not None
    assert found.result == {"status": "ok"}


@pytest.mark.asyncio
async def test_inmemory_transformation_rule_repository_create_and_get() -> None:
    repo = InMemoryTransformationRuleRepository()
    rule = WebhookTransformationRuleModel(
        id=uuid4(),
        tenant_id="default",
        name="rule-1",
        target_schema={"type": "object"},
        mappings=[],
    )
    await repo.create(rule)
    found = await repo.get(rule.id)

    assert found is not None
    assert found.name == "rule-1"


@pytest.mark.asyncio
async def test_inmemory_execution_repository_create_and_get() -> None:
    repo = InMemoryExecutionRepository()
    execution = WebhookExecutionModel(
        id=uuid4(),
        tenant_id="default",
        endpoint_id=uuid4(),
        agent_id="agent-1",
        request_id="req-1",
        status="accepted",
    )
    await repo.create(execution)
    found = await repo.get(execution.id)

    assert found is not None
    assert found.request_id == "req-1"
