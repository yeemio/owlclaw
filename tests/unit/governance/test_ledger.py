"""Unit tests for Ledger and LedgerRecord."""

import asyncio
import contextlib
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

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


def _make_record() -> LedgerRecord:
    return LedgerRecord(
        tenant_id="default",
        agent_id="agent1",
        run_id="run1",
        capability_name="cap1",
        task_type="t1",
        input_params={},
        output_result={},
        decision_reasoning=None,
        execution_time_ms=100,
        llm_model="gpt-4o-mini",
        llm_tokens_input=10,
        llm_tokens_output=5,
        estimated_cost=Decimal("0.1234"),
        status="success",
        error_message=None,
    )


def _make_session_factory(*, commit_side_effect=None):
    session = AsyncMock()
    session.add_all = MagicMock()
    session.commit = AsyncMock(side_effect=commit_side_effect)
    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None
    session_factory = MagicMock(return_value=session_cm)
    return session_factory, session


@pytest.mark.asyncio
async def test_ledger_background_writer_flushes_at_batch_size():
    session_factory = MagicMock()
    ledger = Ledger(session_factory, batch_size=2, flush_interval=60.0)
    ledger._flush_batch = AsyncMock()  # type: ignore[method-assign]
    task = asyncio.create_task(ledger._background_writer())

    try:
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
        await ledger.record_execution(
            tenant_id="default",
            agent_id="agent1",
            run_id="run2",
            capability_name="cap2",
            task_type="t2",
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

        for _ in range(50):
            if ledger._flush_batch.await_count >= 1:  # type: ignore[attr-defined]
                break
            await asyncio.sleep(0.01)
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    assert ledger._flush_batch.await_count == 1  # type: ignore[attr-defined]
    flushed_batch = ledger._flush_batch.await_args.args[0]  # type: ignore[attr-defined]
    assert len(flushed_batch) == 2


@pytest.mark.asyncio
async def test_ledger_background_writer_flushes_on_timeout():
    session_factory = MagicMock()
    ledger = Ledger(session_factory, batch_size=10, flush_interval=0.05)
    ledger._flush_batch = AsyncMock()  # type: ignore[method-assign]
    task = asyncio.create_task(ledger._background_writer())

    try:
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

        for _ in range(50):
            if ledger._flush_batch.await_count >= 1:  # type: ignore[attr-defined]
                break
            await asyncio.sleep(0.01)
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    assert ledger._flush_batch.await_count == 1  # type: ignore[attr-defined]
    flushed_batch = ledger._flush_batch.await_args.args[0]  # type: ignore[attr-defined]
    assert len(flushed_batch) == 1


@pytest.mark.asyncio
async def test_ledger_flush_batch_retries_and_falls_back(monkeypatch):
    session_factory, session = _make_session_factory(
        commit_side_effect=RuntimeError("db down")
    )
    ledger = Ledger(session_factory, batch_size=10, flush_interval=1.0)
    ledger._write_to_fallback_log = AsyncMock()  # type: ignore[method-assign]

    sleep_mock = AsyncMock()
    monkeypatch.setattr("owlclaw.governance.ledger.asyncio.sleep", sleep_mock)

    batch = [_make_record()]
    await ledger._flush_batch(batch)

    assert session.commit.await_count == 3
    assert sleep_mock.await_count == 2
    ledger._write_to_fallback_log.assert_awaited_once_with(batch)  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_ledger_get_cost_summary_includes_capability_breakdown():
    session = AsyncMock()
    total_result = MagicMock()
    total_result.scalar_one.return_value = Decimal("3.50")
    by_capability_result = MagicMock()
    by_capability_result.all.return_value = [
        ("cap_a", Decimal("1.25")),
        ("cap_b", Decimal("2.25")),
    ]
    session.execute = AsyncMock(side_effect=[total_result, by_capability_result])

    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None
    session_factory = MagicMock(return_value=session_cm)

    ledger = Ledger(session_factory, batch_size=10, flush_interval=1.0)
    summary = await ledger.get_cost_summary(
        tenant_id="t1",
        agent_id="agent1",
        start_date=date(2026, 2, 1),
        end_date=date(2026, 2, 23),
    )

    assert summary.total_cost == Decimal("3.50")
    assert summary.by_agent == {"agent1": Decimal("3.50")}
    assert summary.by_capability == {
        "cap_a": Decimal("1.25"),
        "cap_b": Decimal("2.25"),
    }
