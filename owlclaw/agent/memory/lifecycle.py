"""Memory lifecycle management — auto-archive, auto-cleanup, optional Ledger and Hatchet cron."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from owlclaw.agent.memory.models import MemoryConfig
from owlclaw.agent.memory.store import MemoryStore

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class MaintenanceResult:
    """Result of run_maintenance for one agent/tenant."""

    agent_id: str
    tenant_id: str
    archived_count: int = 0
    deleted_count: int = 0
    duration_ms: int = 0
    error: str | None = None


class MemoryLifecycleManager:
    """Runs periodic maintenance: archive excess entries, delete expired low-access entries.

    Intended to be invoked by Hatchet cron (e.g. daily at midnight). Register with
    @app.cron(\"0 0 * * *\", focus=\"memory_maintenance\") and call run_maintenance
    or run_maintenance_for_agents from the cron handler.
    """

    def __init__(
        self,
        store: MemoryStore,
        config: MemoryConfig,
        ledger: Any = None,
    ) -> None:
        self._store = store
        self._config = config
        self._ledger = ledger

    async def run_maintenance(
        self,
        agent_id: str,
        tenant_id: str,
    ) -> MaintenanceResult:
        """Run archive-excess and delete-expired for one agent/tenant. Optionally record to Ledger."""
        start = time.perf_counter()
        result = MaintenanceResult(agent_id=agent_id, tenant_id=tenant_id)
        try:
            count = await self._store.count(agent_id, tenant_id)
            if count > self._config.max_entries:
                to_archive = await self._store.list_entries(
                    agent_id,
                    tenant_id,
                    order_created_asc=True,
                    limit=max(1, count - self._config.max_entries),
                    include_archived=False,
                )
                if to_archive:
                    ids = [e.id for e in to_archive]
                    result.archived_count = await self._store.archive(ids)
                    logger.info(
                        "memory maintenance: archived %d entries agent_id=%s tenant_id=%s",
                        result.archived_count,
                        agent_id,
                        tenant_id,
                    )

            cutoff = _utc_now() - timedelta(days=self._config.retention_days)
            expired_ids = await self._store.get_expired_entry_ids(
                agent_id,
                tenant_id,
                before=cutoff,
                max_access_count=0,
            )
            if expired_ids:
                result.deleted_count = await self._store.delete(expired_ids)
                logger.info(
                    "memory maintenance: deleted %d expired entries agent_id=%s tenant_id=%s",
                    result.deleted_count,
                    agent_id,
                    tenant_id,
                )

            result.duration_ms = int((time.perf_counter() - start) * 1000)
            if self._ledger is not None:
                await self._record_maintenance(agent_id, tenant_id, result)
        except Exception as e:
            result.error = str(e)
            result.duration_ms = int((time.perf_counter() - start) * 1000)
            logger.exception("memory maintenance failed agent_id=%s tenant_id=%s", agent_id, tenant_id)
        return result

    async def _record_maintenance(
        self,
        agent_id: str,
        tenant_id: str,
        result: MaintenanceResult,
    ) -> None:
        """Record maintenance run to Ledger (non-blocking)."""
        assert self._ledger is not None
        await self._ledger.record_execution(
            tenant_id=tenant_id,
            agent_id=agent_id,
            run_id="memory-maintenance",
            capability_name="memory.maintenance",
            task_type="lifecycle",
            input_params={"agent_id": agent_id, "tenant_id": tenant_id},
            output_result={
                "archived_count": result.archived_count,
                "deleted_count": result.deleted_count,
                "duration_ms": result.duration_ms,
            },
            decision_reasoning=None,
            execution_time_ms=result.duration_ms,
            llm_model="",
            llm_tokens_input=0,
            llm_tokens_output=0,
            estimated_cost=Decimal("0"),
            status="error" if result.error else "success",
            error_message=result.error,
        )

    async def run_maintenance_for_agents(
        self,
        agents: list[tuple[str, str]],
    ) -> list[MaintenanceResult]:
        """Run maintenance for multiple (agent_id, tenant_id) pairs (e.g. from cron)."""
        return [await self.run_maintenance(aid, tid) for aid, tid in agents]
