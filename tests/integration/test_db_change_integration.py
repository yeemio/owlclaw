"""Integration tests for db-change trigger end-to-end with PostgreSQL NOTIFY."""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass, field
from typing import Any

import asyncpg
import pytest
from docker.errors import DockerException
from testcontainers.postgres import PostgresContainer

from owlclaw.triggers.db_change import (
    DBChangeTriggerConfig,
    DBChangeTriggerManager,
    PostgresNotifyAdapter,
)

os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")
pytestmark = pytest.mark.integration


@dataclass
class _Governance:
    async def allow_trigger(self, event_name: str, tenant_id: str) -> bool:  # noqa: ARG002
        return True


@dataclass
class _Runtime:
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def trigger_event(
        self,
        event_name: str,
        payload: dict[str, Any],
        focus: str | None = None,
        tenant_id: str = "default",
    ) -> None:
        self.calls.append(
            {
                "event_name": event_name,
                "payload": payload,
                "focus": focus,
                "tenant_id": tenant_id,
            }
        )


def _sync_url_to_async(url: str) -> str:
    value = url.strip()
    if value.startswith("postgresql+psycopg2://"):
        return "postgresql://" + value[len("postgresql+psycopg2://") :]
    return value


@pytest.fixture(scope="module")
def pg_container() -> PostgresContainer:
    try:
        with PostgresContainer("pgvector/pgvector:pg16") as postgres:
            yield postgres
    except DockerException as exc:
        pytest.skip(f"Docker unavailable for integration test: {exc}")


async def _wait_until(predicate: Any, timeout: float = 5.0) -> None:
    start = asyncio.get_running_loop().time()
    while asyncio.get_running_loop().time() - start < timeout:
        if predicate():
            return
        await asyncio.sleep(0.05)
    raise AssertionError("Condition not met before timeout")


@pytest.mark.asyncio
async def test_db_change_notify_to_manager_flow_and_reconnect(pg_container: PostgresContainer) -> None:
    dsn = _sync_url_to_async(pg_container.get_connection_url())
    runtime = _Runtime()
    adapter = PostgresNotifyAdapter(dsn=dsn, reconnect_interval=0.2)
    manager = DBChangeTriggerManager(
        adapter=adapter,
        governance=_Governance(),
        agent_runtime=runtime,
        retry_interval_seconds=0.2,
    )
    manager.register(
        DBChangeTriggerConfig(
            channel="order_updates",
            event_name="order_changed",
            agent_id="agent-1",
            debounce_seconds=0.05,
            batch_size=1,
        )
    )

    notify_conn = await asyncpg.connect(dsn)
    await manager.start()
    try:
        await notify_conn.execute("SELECT pg_notify('order_updates', $1)", json.dumps({"id": 1, "op": "INSERT"}))
        await _wait_until(lambda: len(runtime.calls) == 1)
        assert runtime.calls[0]["event_name"] == "order_changed"
        assert runtime.calls[0]["payload"]["events"][0]["id"] == 1

        assert adapter._conn is not None  # noqa: SLF001
        await adapter._conn.close()  # noqa: SLF001
        await asyncio.sleep(0.4)

        await notify_conn.execute("SELECT pg_notify('order_updates', $1)", json.dumps({"id": 2, "op": "UPDATE"}))
        await _wait_until(lambda: len(runtime.calls) == 2)
        assert runtime.calls[1]["payload"]["events"][0]["id"] == 2
    finally:
        await manager.stop()
        await notify_conn.close()
