"""Repository layer for webhook trigger persistence."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from owlclaw.triggers.webhook.persistence.models import (
    WebhookEndpointModel,
    WebhookEventModel,
    WebhookExecutionModel,
    WebhookIdempotencyKeyModel,
    WebhookTransformationRuleModel,
)


class EndpointRepository:
    """CRUD repository for webhook endpoints."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, endpoint: WebhookEndpointModel) -> WebhookEndpointModel:
        self._session.add(endpoint)
        await self._session.flush()
        await self._session.refresh(endpoint)
        return endpoint

    async def get(self, endpoint_id: UUID) -> WebhookEndpointModel | None:
        stmt = select(WebhookEndpointModel).where(WebhookEndpointModel.id == endpoint_id)
        return await self._session.scalar(stmt)

    async def list(self, *, tenant_id: str, enabled: bool | None = None) -> list[WebhookEndpointModel]:
        stmt = select(WebhookEndpointModel).where(WebhookEndpointModel.tenant_id == tenant_id)
        if enabled is not None:
            stmt = stmt.where(WebhookEndpointModel.enabled == enabled)
        result = await self._session.execute(stmt.order_by(WebhookEndpointModel.created_at.asc()))
        return list(result.scalars().all())

    async def update(self, endpoint: WebhookEndpointModel) -> WebhookEndpointModel:
        await self._session.flush()
        await self._session.refresh(endpoint)
        return endpoint

    async def delete(self, endpoint_id: UUID) -> None:
        await self._session.execute(delete(WebhookEndpointModel).where(WebhookEndpointModel.id == endpoint_id))


class EventRepository:
    """Repository for webhook event logs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, event: WebhookEventModel) -> WebhookEventModel:
        self._session.add(event)
        await self._session.flush()
        await self._session.refresh(event)
        return event

    async def list_by_request_id(self, *, tenant_id: str, request_id: str) -> list[WebhookEventModel]:
        stmt = (
            select(WebhookEventModel)
            .where(WebhookEventModel.tenant_id == tenant_id, WebhookEventModel.request_id == request_id)
            .order_by(WebhookEventModel.timestamp.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class IdempotencyRepository:
    """Repository for webhook idempotency keys."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, key: str) -> WebhookIdempotencyKeyModel | None:
        stmt = select(WebhookIdempotencyKeyModel).where(WebhookIdempotencyKeyModel.key == key)
        return await self._session.scalar(stmt)

    async def upsert(self, item: WebhookIdempotencyKeyModel) -> WebhookIdempotencyKeyModel:
        existing = await self.get(item.key)
        if existing is None:
            self._session.add(item)
            await self._session.flush()
            await self._session.refresh(item)
            return item
        existing.result = item.result
        existing.execution_id = item.execution_id
        existing.expires_at = item.expires_at
        await self._session.flush()
        await self._session.refresh(existing)
        return existing

    async def delete_expired(self, *, now: datetime) -> int:
        result = await self._session.execute(
            delete(WebhookIdempotencyKeyModel).where(WebhookIdempotencyKeyModel.expires_at < now)
        )
        return int(result.rowcount or 0)


class TransformationRuleRepository:
    """Repository for webhook transformation rules."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, rule: WebhookTransformationRuleModel) -> WebhookTransformationRuleModel:
        self._session.add(rule)
        await self._session.flush()
        await self._session.refresh(rule)
        return rule

    async def get(self, rule_id: UUID) -> WebhookTransformationRuleModel | None:
        stmt = select(WebhookTransformationRuleModel).where(WebhookTransformationRuleModel.id == rule_id)
        return await self._session.scalar(stmt)

    async def list(self, *, tenant_id: str) -> list[WebhookTransformationRuleModel]:
        stmt = (
            select(WebhookTransformationRuleModel)
            .where(WebhookTransformationRuleModel.tenant_id == tenant_id)
            .order_by(WebhookTransformationRuleModel.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class ExecutionRepository:
    """Repository for webhook execution records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, execution: WebhookExecutionModel) -> WebhookExecutionModel:
        self._session.add(execution)
        await self._session.flush()
        await self._session.refresh(execution)
        return execution

    async def get(self, execution_id: UUID) -> WebhookExecutionModel | None:
        stmt = select(WebhookExecutionModel).where(WebhookExecutionModel.id == execution_id)
        return await self._session.scalar(stmt)


class InMemoryEndpointRepository:
    """In-memory endpoint repository for deterministic property tests."""

    def __init__(self) -> None:
        self._items: dict[UUID, WebhookEndpointModel] = {}

    async def create(self, endpoint: WebhookEndpointModel) -> WebhookEndpointModel:
        self._items[endpoint.id] = endpoint
        return endpoint

    async def list(self, *, tenant_id: str, enabled: bool | None = None) -> list[WebhookEndpointModel]:
        items = [item for item in self._items.values() if item.tenant_id == tenant_id]
        if enabled is not None:
            items = [item for item in items if item.enabled == enabled]
        return sorted(items, key=lambda item: item.created_at)


class InMemoryEventRepository:
    """In-memory event repository for round-trip property tests."""

    def __init__(self) -> None:
        self._items: list[WebhookEventModel] = []

    async def create(self, event: WebhookEventModel) -> WebhookEventModel:
        self._items.append(event)
        return event

    async def list_by_request_id(self, *, tenant_id: str, request_id: str) -> list[WebhookEventModel]:
        items = [item for item in self._items if item.tenant_id == tenant_id and item.request_id == request_id]
        return sorted(items, key=lambda item: item.timestamp)


class InMemoryIdempotencyRepository:
    """In-memory idempotency repository for tests."""

    def __init__(self) -> None:
        self._items: dict[str, WebhookIdempotencyKeyModel] = {}

    async def get(self, key: str) -> WebhookIdempotencyKeyModel | None:
        return self._items.get(key)

    async def upsert(self, item: WebhookIdempotencyKeyModel) -> WebhookIdempotencyKeyModel:
        self._items[item.key] = item
        return item


class InMemoryTransformationRuleRepository:
    """In-memory transformation rule repository for tests."""

    def __init__(self) -> None:
        self._items: dict[UUID, WebhookTransformationRuleModel] = {}

    async def create(self, rule: WebhookTransformationRuleModel) -> WebhookTransformationRuleModel:
        self._items[rule.id] = rule
        return rule

    async def get(self, rule_id: UUID) -> WebhookTransformationRuleModel | None:
        return self._items.get(rule_id)


class InMemoryExecutionRepository:
    """In-memory execution repository for tests."""

    def __init__(self) -> None:
        self._items: dict[UUID, WebhookExecutionModel] = {}

    async def create(self, execution: WebhookExecutionModel) -> WebhookExecutionModel:
        self._items[execution.id] = execution
        return execution

    async def get(self, execution_id: UUID) -> WebhookExecutionModel | None:
        return self._items.get(execution_id)
