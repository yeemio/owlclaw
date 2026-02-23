"""Unit tests for Ledger and LedgerRecord."""

import asyncio
import contextlib
from datetime import date
from decimal import Decimal
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlclaw.governance.ledger import Ledger, LedgerRecord


def test_ledger_record_has_required_columns():
    """LedgerRecord defines all required fields."""
    assert hasattr(LedgerRecord, "tenant_id")
    assert hasattr(LedgerRecord, "agent_id")
    assert hasattr(LedgerRecord, "run_id")
    assert hasattr(LedgerRecord, "capability_name")
    assert hasattr(LedgerRecord, "task_type")
    assert hasattr(LedgerRecord, "input_params")
    assert hasattr(LedgerRecord, "output_result")
    assert hasattr(LedgerRecord, "status")
    assert hasattr(LedgerRecord, "created_at")


def test_ledger_record_table_name():
    """LedgerRecord table is ledger_records."""
    assert LedgerRecord.__tablename__ == "ledger_records"


@pytest.mark.asyncio
async def test_ledger_record_execution_enqueues():
    """record_execution enqueues a record without raising."""
    session_factory = MagicMock()
    ledger = Ledger(session_factory, batch_size=2, flush_interval=0.1)
    await ledger.record_execution(
        tenant_id="default",
        agent_id="agent1",
        run_id="run1",
        capability_name="cap1",
        task_type="t1",
        input_params={},
        output_result=None,
        decision_reasoning=None,
        execution_time_ms=100,
        llm_model="gpt-4o-mini",
        llm_tokens_input=10,
        llm_tokens_output=5,
        estimated_cost=Decimal("0.001"),
        status="success",
        error_message=None,
    )
    assert ledger._write_queue.qsize() == 1


@pytest.mark.asyncio
async def test_ledger_record_execution_rejects_blank_scope_fields():
    session_factory = MagicMock()
    ledger = Ledger(session_factory, batch_size=2, flush_interval=0.1)
    with pytest.raises(ValueError, match="tenant_id must be a non-empty string"):
        await ledger.record_execution(
            tenant_id=" ",
            agent_id="agent1",
            run_id="run1",
            capability_name="cap1",
            task_type="t1",
            input_params={},
            output_result=None,
            decision_reasoning=None,
            execution_time_ms=100,
            llm_model="gpt-4o-mini",
            llm_tokens_input=10,
            llm_tokens_output=5,
            estimated_cost=Decimal("0.001"),
            status="success",
            error_message=None,
        )


@pytest.mark.asyncio
async def test_ledger_record_execution_rejects_non_dict_input_params():
    session_factory = MagicMock()
    ledger = Ledger(session_factory, batch_size=2, flush_interval=0.1)
    with pytest.raises(ValueError, match="input_params must be a dictionary"):
        await ledger.record_execution(
            tenant_id="default",
            agent_id="agent1",
            run_id="run1",
            capability_name="cap1",
            task_type="t1",
            input_params="bad",  # type: ignore[arg-type]
            output_result=None,
            decision_reasoning=None,
            execution_time_ms=100,
            llm_model="gpt-4o-mini",
            llm_tokens_input=10,
            llm_tokens_output=5,
            estimated_cost=Decimal("0.001"),
            status="success",
            error_message=None,
        )


@pytest.mark.asyncio
async def test_ledger_start_stop():
    """start() and stop() manage background task."""
    session_factory = MagicMock()
    ledger = Ledger(session_factory, batch_size=10, flush_interval=60.0)
    await ledger.start()
    assert ledger._writer_task is not None
    await ledger.stop()
    assert ledger._writer_task is None


@pytest.mark.asyncio
async def test_ledger_start_is_idempotent_when_running():
    """Calling start() twice should keep a single running writer task."""
    session_factory = MagicMock()
    ledger = Ledger(session_factory, batch_size=10, flush_interval=60.0)
    await ledger.start()
    first_task = ledger._writer_task
    assert first_task is not None
    await ledger.start()
    assert ledger._writer_task is first_task
    await ledger.stop()


@pytest.mark.asyncio
async def test_ledger_can_restart_after_stop():
    """After stop(), start() should create a new writer task."""
    session_factory = MagicMock()
    ledger = Ledger(session_factory, batch_size=10, flush_interval=60.0)
    await ledger.start()
    first_task = ledger._writer_task
    await ledger.stop()
    await ledger.start()
    second_task = ledger._writer_task
    assert second_task is not None
    assert second_task is not first_task
    await ledger.stop()


def test_ledger_rejects_invalid_batch_size():
    session_factory = MagicMock()
    with pytest.raises(ValueError, match="batch_size must be a positive integer"):
        Ledger(session_factory, batch_size=0, flush_interval=1.0)


def test_ledger_rejects_invalid_flush_interval():
    session_factory = MagicMock()
    with pytest.raises(ValueError, match="flush_interval must be a positive number"):
        Ledger(session_factory, batch_size=1, flush_interval=0)


@pytest.mark.asyncio
async def test_flush_batch_writes_records_and_commits() -> None:
    """3.1.4.1: batch flush writes records successfully."""
    session_factory = MagicMock()
    session = MagicMock()
    session.commit = AsyncMock()
    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None
    session_factory.return_value = session_cm

    ledger = Ledger(session_factory, batch_size=2, flush_interval=0.1)
    batch = cast(
        list[LedgerRecord],
        [MagicMock(spec=LedgerRecord), MagicMock(spec=LedgerRecord)],
    )

    await ledger._flush_batch(batch)

    session.add_all.assert_called_once_with(batch)
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_background_writer_flushes_on_timeout() -> None:
    """3.1.4.2: background writer flushes pending batch on timeout."""
    session_factory = MagicMock()
    ledger = Ledger(session_factory, batch_size=10, flush_interval=0.05)
    ledger._flush_batch = AsyncMock()  # type: ignore[method-assign]

    writer_task = asyncio.create_task(ledger._background_writer())
    try:
        ledger._write_queue.put_nowait(MagicMock(spec=LedgerRecord))
        await asyncio.sleep(0.12)
        assert ledger._flush_batch.await_count >= 1
    finally:
        writer_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await writer_task


@pytest.mark.asyncio
async def test_flush_batch_falls_back_on_write_failure() -> None:
    """3.1.4.3: flush failure falls back to local log path."""
    session_factory = MagicMock()
    session = MagicMock()
    session.commit = AsyncMock(side_effect=RuntimeError("db unavailable"))
    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None
    session_factory.return_value = session_cm

    ledger = Ledger(session_factory, batch_size=2, flush_interval=0.1)
    ledger._write_to_fallback_log = AsyncMock()  # type: ignore[method-assign]
    batch = cast(list[LedgerRecord], [MagicMock(spec=LedgerRecord)])

    with patch("owlclaw.governance.ledger.asyncio.sleep", new=AsyncMock()) as sleep_mock:
        await ledger._flush_batch(batch)

    assert session.commit.await_count == 3
    assert sleep_mock.await_count == 2
    ledger._write_to_fallback_log.assert_awaited_once_with(batch)


@pytest.mark.asyncio
async def test_query_records_applies_filters_and_returns_records() -> None:
    """3.2.4: query interface returns records with filter pipeline applied."""
    session_factory = MagicMock()
    session = MagicMock()
    result = MagicMock()
    expected = [MagicMock(spec=LedgerRecord), MagicMock(spec=LedgerRecord)]
    result.scalars.return_value.all.return_value = expected
    session.execute = AsyncMock(return_value=result)
    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None
    session_factory.return_value = session_cm

    ledger = Ledger(session_factory, batch_size=2, flush_interval=0.1)
    filters = MagicMock()
    filters.agent_id = "agent-1"
    filters.capability_name = "cap-x"
    filters.start_date = None
    filters.end_date = None
    filters.limit = 5
    filters.order_by = "created_at DESC"

    rows = await ledger.query_records("tenant-a", filters)

    assert rows == expected
    session.execute.assert_awaited_once()
    stmt = session.execute.await_args.args[0]
    stmt_sql = str(stmt)
    assert "ledger_records.tenant_id" in stmt_sql
    assert "ledger_records.agent_id" in stmt_sql
    assert "ledger_records.capability_name" in stmt_sql


@pytest.mark.asyncio
async def test_get_cost_summary_returns_decimal_total() -> None:
    """3.2.4: get_cost_summary converts aggregate result to Decimal."""
    session_factory = MagicMock()
    session = MagicMock()
    result = MagicMock()
    result.scalar_one.return_value = Decimal("1.2345")
    session.execute = AsyncMock(return_value=result)
    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None
    session_factory.return_value = session_cm

    ledger = Ledger(session_factory, batch_size=2, flush_interval=0.1)
    summary = await ledger.get_cost_summary(
        tenant_id="tenant-a",
        agent_id="agent-1",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    assert summary.total_cost == Decimal("1.2345")
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_flush_batch_retries_then_succeeds_without_fallback() -> None:
    """3.1.2.2: flush retries with backoff and succeeds before fallback."""
    session_factory = MagicMock()
    session = MagicMock()
    session.commit = AsyncMock(side_effect=[RuntimeError("t1"), RuntimeError("t2"), None])
    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None
    session_factory.return_value = session_cm

    ledger = Ledger(session_factory, batch_size=2, flush_interval=0.1)
    ledger._write_to_fallback_log = AsyncMock()  # type: ignore[method-assign]
    batch = cast(list[LedgerRecord], [MagicMock(spec=LedgerRecord)])

    with patch("owlclaw.governance.ledger.asyncio.sleep", new=AsyncMock()) as sleep_mock:
        await ledger._flush_batch(batch)

    assert session.commit.await_count == 3
    assert sleep_mock.await_count == 2
    ledger._write_to_fallback_log.assert_not_awaited()
