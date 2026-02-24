from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from owlclaw.triggers.webhook import EventFilter, EventLogger, build_event
from owlclaw.triggers.webhook.persistence.repositories import InMemoryEventRepository


@pytest.mark.asyncio
async def test_event_logger_records_and_queries_events() -> None:
    repo = InMemoryEventRepository()
    logger = EventLogger(repo)
    endpoint_id = str(uuid4())
    request_id = "req-1"

    await logger.log_request(build_event(endpoint_id=endpoint_id, request_id=request_id, event_type="request"))
    await logger.log_validation(build_event(endpoint_id=endpoint_id, request_id=request_id, event_type="validation"))
    await logger.log_transformation(
        build_event(endpoint_id=endpoint_id, request_id=request_id, event_type="transformation")
    )
    await logger.log_execution(build_event(endpoint_id=endpoint_id, request_id=request_id, event_type="execution"))

    events = await logger.query_events(EventFilter(tenant_id="default", request_id=request_id))
    assert [event.event_type for event in events] == ["request", "validation", "transformation", "execution"]


@pytest.mark.asyncio
async def test_event_logger_filters_and_pagination() -> None:
    repo = InMemoryEventRepository()
    logger = EventLogger(repo)
    endpoint_id = str(uuid4())
    now = datetime.now(timezone.utc)
    for idx in range(5):
        event = build_event(endpoint_id=endpoint_id, request_id="req-2", event_type="execution", status="completed")
        event.timestamp = now + timedelta(seconds=idx)
        await logger.log_execution(event)

    page1 = await logger.query_events(EventFilter(tenant_id="default", request_id="req-2", page=1, page_size=2))
    page2 = await logger.query_events(EventFilter(tenant_id="default", request_id="req-2", page=2, page_size=2))
    assert len(page1) == 2
    assert len(page2) == 2
    assert page1[0].timestamp < page1[1].timestamp


@pytest.mark.asyncio
async def test_event_logger_preserves_error_payload() -> None:
    repo = InMemoryEventRepository()
    logger = EventLogger(repo)
    endpoint_id = str(uuid4())
    error = {"type": "RuntimeError", "message": "boom", "traceback": "line 1\nline 2"}
    await logger.log_execution(
        build_event(
            endpoint_id=endpoint_id,
            request_id="req-err",
            event_type="execution",
            status="failed",
            error=error,
        )
    )

    events = await logger.query_events(EventFilter(tenant_id="default", request_id="req-err"))
    assert len(events) == 1
    assert events[0].error == error
