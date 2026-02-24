from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from owlclaw.triggers.signal import AgentStateManager, PendingInstruction, SignalSource
from owlclaw.triggers.signal.persistence import AgentControlStateORM, PendingInstructionORM


class _ScalarRows:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self) -> _ScalarRows:
        return self

    def all(self):
        return list(self._rows)


class _Session:
    def __init__(self, *, scalar_values=None, execute_values=None):
        self.scalar_values = list(scalar_values or [])
        self.execute_values = list(execute_values or [])
        self.added = []
        self.deleted = []
        self.commits = 0

    async def __aenter__(self) -> _Session:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    async def scalar(self, stmt):  # noqa: ARG002
        if not self.scalar_values:
            return None
        return self.scalar_values.pop(0)

    async def execute(self, stmt):  # noqa: ARG002
        if not self.execute_values:
            return _ScalarRows([])
        value = self.execute_values.pop(0)
        if isinstance(value, list):
            return _ScalarRows(value)
        return value

    def add(self, obj) -> None:
        self.added.append(obj)

    async def delete(self, obj) -> None:
        self.deleted.append(obj)

    async def commit(self) -> None:
        self.commits += 1


class _Factory:
    def __init__(self, session: _Session):
        self._session = session

    def __call__(self) -> _Session:
        return self._session


@pytest.mark.asyncio
async def test_state_manager_get_from_db_creates_missing_state() -> None:
    session = _Session(scalar_values=[None], execute_values=[[]])
    manager = AgentStateManager(max_pending_instructions=3, session_factory=_Factory(session))  # type: ignore[arg-type]
    state = await manager.get("agent-a", "tenant-a")
    assert state.paused is False
    assert session.commits == 1
    assert any(isinstance(obj, AgentControlStateORM) for obj in session.added)


@pytest.mark.asyncio
async def test_state_manager_set_paused_and_consume_cleanup_db_paths() -> None:
    existing = AgentControlStateORM(agent_id="agent-a", tenant_id="tenant-a", paused=False)
    now = datetime.now(timezone.utc)
    row = PendingInstructionORM(
        agent_id="agent-a",
        tenant_id="tenant-a",
        content="op note",
        operator="ops",
        source="cli",
        created_at=now,
        expires_at=now + timedelta(hours=1),
        consumed=False,
    )

    delete_result = type("DeleteResult", (), {"rowcount": 2})()
    session = _Session(
        scalar_values=[existing, 1, row],
        execute_values=[[row], delete_result],
    )
    manager = AgentStateManager(max_pending_instructions=1, session_factory=_Factory(session))  # type: ignore[arg-type]

    await manager.set_paused("agent-a", "tenant-a", True)
    assert existing.paused is True

    await manager.add_instruction(
        "agent-a",
        "tenant-a",
        PendingInstruction.create(content="new", operator="ops", source=SignalSource.CLI, ttl_seconds=3600),
    )
    assert session.deleted  # oldest evicted when queue is full

    consumed = await manager.consume_instructions("agent-a", "tenant-a")
    assert consumed and consumed[0].content == "op note"
    assert row.consumed is True
    assert row.consumed_at is not None

    cleaned = await manager.cleanup_expired_instructions("agent-a", "tenant-a")
    assert cleaned == 2
