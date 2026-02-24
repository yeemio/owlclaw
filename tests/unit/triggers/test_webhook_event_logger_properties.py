from __future__ import annotations

import asyncio
from uuid import uuid4

from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.triggers.webhook import EventFilter, EventLogger, build_event
from owlclaw.triggers.webhook.persistence.repositories import InMemoryEventRepository


@given(request_id=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-", min_size=1, max_size=20))
@settings(max_examples=25, deadline=None)
def test_property_request_processing_has_complete_logs(request_id: str) -> None:
    """Feature: triggers-webhook, Property 19: 请求处理完整日志."""

    async def _run() -> None:
        logger = EventLogger(InMemoryEventRepository())
        endpoint_id = str(uuid4())
        await logger.log_request(build_event(endpoint_id=endpoint_id, request_id=request_id, event_type="request"))
        await logger.log_validation(build_event(endpoint_id=endpoint_id, request_id=request_id, event_type="validation"))
        await logger.log_transformation(
            build_event(endpoint_id=endpoint_id, request_id=request_id, event_type="transformation")
        )
        await logger.log_execution(build_event(endpoint_id=endpoint_id, request_id=request_id, event_type="execution"))
        events = await logger.query_events(EventFilter(tenant_id="default", request_id=request_id))
        assert {e.event_type for e in events} == {"request", "validation", "transformation", "execution"}

    asyncio.run(_run())


@given(duration=st.integers(min_value=1, max_value=5000))
@settings(max_examples=25, deadline=None)
def test_property_execution_completion_log(duration: int) -> None:
    """Feature: triggers-webhook, Property 20: 执行完成日志."""

    async def _run() -> None:
        logger = EventLogger(InMemoryEventRepository())
        endpoint_id = str(uuid4())
        request_id = "req-complete"
        await logger.log_execution(
            build_event(
                endpoint_id=endpoint_id,
                request_id=request_id,
                event_type="execution",
                status="completed",
                duration_ms=duration,
                data={"output": {"ok": True}},
            )
        )
        events = await logger.query_events(EventFilter(tenant_id="default", request_id=request_id))
        assert len(events) == 1
        assert events[0].duration_ms == duration
        assert events[0].status == "completed"

    asyncio.run(_run())


@given(error_message=st.text(min_size=1, max_size=40))
@settings(max_examples=25, deadline=None)
def test_property_error_log_contains_details(error_message: str) -> None:
    """Feature: triggers-webhook, Property 21: 错误日志详细信息."""

    async def _run() -> None:
        logger = EventLogger(InMemoryEventRepository())
        endpoint_id = str(uuid4())
        request_id = "req-error"
        error = {"type": "ValueError", "message": error_message, "traceback": "stack"}
        await logger.log_execution(
            build_event(
                endpoint_id=endpoint_id,
                request_id=request_id,
                event_type="execution",
                status="failed",
                error=error,
            )
        )
        events = await logger.query_events(EventFilter(tenant_id="default", request_id=request_id))
        assert events[0].error == error

    asyncio.run(_run())


@given(request_id=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-", min_size=1, max_size=20))
@settings(max_examples=25, deadline=None)
def test_property_event_log_persistence_roundtrip(request_id: str) -> None:
    """Feature: triggers-webhook, Property 22: 事件日志持久化往返."""

    async def _run() -> None:
        logger = EventLogger(InMemoryEventRepository())
        endpoint_id = str(uuid4())
        original = build_event(
            endpoint_id=endpoint_id,
            request_id=request_id,
            event_type="request",
            source_ip="1.2.3.4",
            user_agent="pytest",
            data={"k": "v"},
        )
        created = await logger.log_request(original)
        events = await logger.query_events(EventFilter(tenant_id="default", request_id=request_id))
        assert len(events) == 1
        assert events[0].id == created.id
        assert events[0].data == {"k": "v"}

    asyncio.run(_run())


@given(retry_count=st.integers(min_value=1, max_value=5))
@settings(max_examples=20, deadline=None)
def test_property_retry_attempts_are_logged(retry_count: int) -> None:
    """Feature: triggers-webhook, Property 30: 重试日志记录."""

    async def _run() -> None:
        logger = EventLogger(InMemoryEventRepository())
        endpoint_id = str(uuid4())
        request_id = "req-retry"
        for attempt in range(1, retry_count + 1):
            await logger.log_execution(
                build_event(
                    endpoint_id=endpoint_id,
                    request_id=request_id,
                    event_type="execution",
                    status="retrying" if attempt < retry_count else "failed",
                    data={"attempt": attempt},
                )
            )
        events = await logger.query_events(
            EventFilter(tenant_id="default", request_id=request_id, event_type="execution")
        )
        assert len(events) == retry_count
        assert events[-1].data == {"attempt": retry_count}

    asyncio.run(_run())
