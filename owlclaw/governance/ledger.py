"""Execution ledger: record and query capability runs.

Uses async queue for non-blocking writes; background batch writer
is started/stopped via start()/stop().
"""

import asyncio
import contextlib
import logging
import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import DECIMAL, DateTime, Index, Integer, String, Text, func, select
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column

from owlclaw.db import Base

logger = logging.getLogger(__name__)


@dataclass
class LedgerQueryFilters:
    """Filters for querying ledger records."""

    agent_id: str | None = None
    capability_name: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    limit: int | None = None
    order_by: str | None = None


@dataclass
class CostSummary:
    """Aggregated cost over a period."""

    total_cost: Decimal


class LedgerRecord(Base):
    """Single capability execution record (audit and cost analysis)."""

    __tablename__ = "ledger_records"
    __table_args__ = (
        Index("idx_ledger_tenant_agent", "tenant_id", "agent_id"),
        Index("idx_ledger_tenant_capability", "tenant_id", "capability_name"),
        Index("idx_ledger_tenant_created", "tenant_id", "created_at"),
        {"comment": "Agent capability execution records for audit and cost analysis"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        primary_key=True,
    )
    agent_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    capability_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    task_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    input_params: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    output_result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    decision_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

    execution_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    llm_model: Mapped[str] = mapped_column(String(100), nullable=False)
    llm_tokens_input: Mapped[int] = mapped_column(Integer, nullable=False)
    llm_tokens_output: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_cost: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 4),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )


class Ledger:
    """Records capability executions via async queue and background writer."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        batch_size: int = 10,
        flush_interval: float = 5.0,
    ) -> None:
        self._session_factory = session_factory
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._write_queue: asyncio.Queue[LedgerRecord] = asyncio.Queue()
        self._writer_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start the background writer task."""
        if self._writer_task is not None and not self._writer_task.done():
            logger.warning("Ledger background writer already running")
            return
        self._writer_task = asyncio.create_task(self._background_writer())

    async def stop(self) -> None:
        """Stop the background writer task."""
        if self._writer_task is not None:
            self._writer_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._writer_task
            self._writer_task = None

    async def record_execution(
        self,
        tenant_id: str,
        agent_id: str,
        run_id: str,
        capability_name: str,
        task_type: str,
        input_params: dict[str, Any],
        output_result: dict[str, Any] | None,
        decision_reasoning: str | None,
        execution_time_ms: int,
        llm_model: str,
        llm_tokens_input: int,
        llm_tokens_output: int,
        estimated_cost: Decimal,
        status: str,
        error_message: str | None = None,
    ) -> None:
        """Enqueue one execution record (non-blocking)."""
        record = LedgerRecord(
            tenant_id=tenant_id,
            agent_id=agent_id,
            run_id=run_id,
            capability_name=capability_name,
            task_type=task_type,
            input_params=input_params,
            output_result=output_result,
            decision_reasoning=decision_reasoning,
            execution_time_ms=execution_time_ms,
            llm_model=llm_model,
            llm_tokens_input=llm_tokens_input,
            llm_tokens_output=llm_tokens_output,
            estimated_cost=estimated_cost,
            status=status,
            error_message=error_message,
        )
        self._write_queue.put_nowait(record)

    async def query_records(
        self,
        tenant_id: str,
        filters: LedgerQueryFilters,
    ) -> list[LedgerRecord]:
        """Query execution records with optional filters."""
        async with self._session_factory() as session:
            stmt = select(LedgerRecord).where(LedgerRecord.tenant_id == tenant_id)
            if filters.agent_id is not None:
                stmt = stmt.where(LedgerRecord.agent_id == filters.agent_id)
            if filters.capability_name is not None:
                stmt = stmt.where(
                    LedgerRecord.capability_name == filters.capability_name
                )
            if filters.start_date is not None:
                start_dt = datetime.combine(
                    filters.start_date, time.min, tzinfo=timezone.utc
                )
                stmt = stmt.where(LedgerRecord.created_at >= start_dt)
            if filters.end_date is not None:
                end_dt = datetime.combine(
                    filters.end_date, time.max, tzinfo=timezone.utc
                )
                stmt = stmt.where(LedgerRecord.created_at <= end_dt)
            if filters.order_by == "created_at DESC":
                stmt = stmt.order_by(LedgerRecord.created_at.desc())
            elif filters.order_by == "created_at ASC":
                stmt = stmt.order_by(LedgerRecord.created_at.asc())
            if filters.limit is not None:
                stmt = stmt.limit(filters.limit)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_cost_summary(
        self,
        tenant_id: str,
        agent_id: str,
        start_date: date,
        end_date: date,
    ) -> CostSummary:
        """Sum estimated_cost for records in the date range."""
        from sqlalchemy import func as sql_func

        async with self._session_factory() as session:
            stmt = (
                select(sql_func.coalesce(sql_func.sum(LedgerRecord.estimated_cost), 0))
                .where(LedgerRecord.tenant_id == tenant_id)
                .where(LedgerRecord.agent_id == agent_id)
                .where(LedgerRecord.created_at >= datetime.combine(
                    start_date, time.min, tzinfo=timezone.utc
                ))
                .where(LedgerRecord.created_at <= datetime.combine(
                    end_date, time.max, tzinfo=timezone.utc
                ))
            )
            result = await session.execute(stmt)
            total = result.scalar_one()
            return CostSummary(total_cost=Decimal(str(total)) if total is not None else Decimal("0"))

    async def _background_writer(self) -> None:
        """Consume queue and flush batches to the database."""
        batch: list[LedgerRecord] = []
        while True:
            try:
                record = await asyncio.wait_for(
                    self._write_queue.get(),
                    timeout=self._flush_interval,
                )
                batch.append(record)
                if len(batch) >= self._batch_size:
                    await self._flush_batch(batch)
                    batch = []
            except asyncio.TimeoutError:
                if batch:
                    await self._flush_batch(batch)
                    batch = []
            except asyncio.CancelledError:
                if batch:
                    await self._flush_batch(batch)
                raise
            except Exception as e:
                logger.exception("Ledger background writer error: %s", e)

    async def _flush_batch(self, batch: list[LedgerRecord]) -> None:
        """Write a batch of records to the database."""
        try:
            async with self._session_factory() as session:
                session.add_all(batch)
                await session.commit()
            logger.debug("Flushed %d ledger records", len(batch))
        except Exception as e:
            logger.exception("Failed to flush ledger batch: %s", e)
            await self._write_to_fallback_log(batch)

    async def _write_to_fallback_log(self, batch: list[LedgerRecord]) -> None:
        """On DB failure, append records to a local fallback log."""
        import json

        for record in batch:
            line = json.dumps(
                {
                    "tenant_id": record.tenant_id,
                    "agent_id": record.agent_id,
                    "capability_name": record.capability_name,
                    "created_at": (
                        record.created_at.isoformat()
                        if getattr(record.created_at, "isoformat", None)
                        else str(record.created_at)
                    ),
                }
            ) + "\n"
            try:
                with open("ledger_fallback.log", "a", encoding="utf-8") as f:
                    f.write(line)
            except OSError as e:
                logger.error("Failed to write fallback log: %s", e)
