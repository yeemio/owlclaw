"""Unit tests for Ledger and LedgerRecord."""

from decimal import Decimal
from unittest.mock import MagicMock

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
