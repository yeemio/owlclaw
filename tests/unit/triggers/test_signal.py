from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from owlclaw.triggers.signal import (
    AgentStateManager,
    PendingInstruction,
    Signal,
    SignalResult,
    SignalRouter,
    SignalSource,
    SignalTriggerConfig,
    SignalType,
)
from owlclaw.triggers.signal.handlers import default_handlers
from owlclaw.triggers.signal.persistence import AgentControlStateORM, PendingInstructionORM


class _Runtime:
    async def trigger_event(self, event_name: str, payload: dict, focus: str | None = None, tenant_id: str = "default") -> dict:  # noqa: ARG002
        return {"run_id": "run-1"}


class _Governance:
    def __init__(self, allowed: bool) -> None:
        self.allowed = allowed

    async def allow_trigger(self, event_name: str, tenant_id: str) -> bool:  # noqa: ARG002
        return self.allowed


class _Authorizer:
    def __init__(self, allowed: bool) -> None:
        self.allowed = allowed

    async def authorize(self, signal: Signal) -> tuple[bool, str | None]:  # noqa: ARG002
        return self.allowed, None if self.allowed else "denied"


class _Ledger:
    def __init__(self) -> None:
        self.calls = 0

    async def record_execution(
        self,
        tenant_id: str,
        agent_id: str,
        run_id: str,
        capability_name: str,
        task_type: str,
        input_params: dict,
        output_result: dict | None,
        decision_reasoning: str | None,
        execution_time_ms: int,
        llm_model: str,
        llm_tokens_input: int,
        llm_tokens_output: int,
        estimated_cost: Decimal,
        status: str,
        error_message: str | None = None,
    ) -> None:
        self.calls += 1


def _signal(kind: SignalType) -> Signal:
    return Signal(type=kind, source=SignalSource.CLI, agent_id="a1", tenant_id="t1", operator="op")


def test_signal_config_defaults() -> None:
    cfg = SignalTriggerConfig()
    assert cfg.default_instruct_ttl_seconds == 3600


def test_signal_config_validator_paths() -> None:
    cfg = SignalTriggerConfig(default_instruct_ttl_seconds=60, max_pending_instructions=20)
    assert cfg.default_instruct_ttl_seconds == 60
    assert cfg.max_pending_instructions == 20
    with pytest.raises(ValueError):
        SignalTriggerConfig(default_instruct_ttl_seconds=0)


@pytest.mark.asyncio
async def test_signal_state_pause_resume_and_instruction_flow() -> None:
    state = AgentStateManager(max_pending_instructions=2)
    await state.set_paused("a1", "t1", True)
    snapshot = await state.get("a1", "t1")
    assert snapshot.paused is True

    first = PendingInstruction.create(content="one", operator="op", source=SignalSource.CLI, ttl_seconds=3600)
    second = PendingInstruction.create(content="two", operator="op", source=SignalSource.CLI, ttl_seconds=3600)
    third = PendingInstruction.create(content="three", operator="op", source=SignalSource.CLI, ttl_seconds=3600)
    await state.add_instruction("a1", "t1", first)
    await state.add_instruction("a1", "t1", second)
    await state.add_instruction("a1", "t1", third)
    consumed = await state.consume_instructions("a1", "t1")
    assert [item.content for item in consumed] == ["two", "three"]


@pytest.mark.asyncio
async def test_signal_router_and_handlers() -> None:
    state = AgentStateManager(max_pending_instructions=4)
    paused_calls = 0
    resumed_calls = 0

    async def _on_pause(signal: Signal) -> None:  # noqa: ARG001
        nonlocal paused_calls
        paused_calls += 1

    async def _on_resume(signal: Signal) -> None:  # noqa: ARG001
        nonlocal resumed_calls
        resumed_calls += 1

    handlers = default_handlers(
        state=state,
        runtime=_Runtime(),
        governance=_Governance(True),
        on_pause=_on_pause,
        on_resume=_on_resume,
    )
    router = SignalRouter(handlers=handlers)

    paused = await router.dispatch(_signal(SignalType.PAUSE))
    assert paused.status == "paused"
    assert paused_calls == 1

    resumed = await router.dispatch(_signal(SignalType.RESUME))
    assert resumed.status == "resumed"
    assert resumed_calls == 1

    triggered = await router.dispatch(
        Signal(
            type=SignalType.TRIGGER,
            source=SignalSource.CLI,
            agent_id="a1",
            tenant_id="t1",
            operator="op",
            message="run now",
        )
    )
    assert triggered.status == "triggered"
    assert triggered.run_id == "run-1"


@pytest.mark.asyncio
async def test_trigger_handler_governance_blocked() -> None:
    state = AgentStateManager(max_pending_instructions=4)
    handlers = default_handlers(state=state, runtime=_Runtime(), governance=_Governance(False))
    router = SignalRouter(handlers=handlers)
    blocked = await router.dispatch(
        Signal(
            type=SignalType.TRIGGER,
            source=SignalSource.CLI,
            agent_id="a1",
            tenant_id="t1",
            operator="op",
            message="run now",
        )
    )
    assert blocked.status == "error"
    assert blocked.error_code == "rate_limited"


def test_pending_instruction_expiry() -> None:
    item = PendingInstruction.create(content="x", operator="op", source=SignalSource.CLI, ttl_seconds=1)
    assert item.is_expired(item.created_at) is False
    future = datetime.now(timezone.utc) + timedelta(seconds=5)
    assert item.is_expired(future) is True


@pytest.mark.asyncio
async def test_router_unknown_signal_returns_error() -> None:
    async def _fake_handler(signal: Signal) -> SignalResult:  # noqa: ARG001
        return SignalResult(status="ok")

    router = SignalRouter(handlers={SignalType.PAUSE: _fake_handler})
    result = await router.dispatch(_signal(SignalType.RESUME))
    assert result.status == "error"
    assert result.error_code == "bad_request"


@pytest.mark.asyncio
async def test_router_authorization_and_ledger_recording() -> None:
    async def _handler(signal: Signal) -> SignalResult:  # noqa: ARG001
        return SignalResult(status="paused")

    ledger = _Ledger()
    router = SignalRouter(handlers={SignalType.PAUSE: _handler}, authorizer=_Authorizer(True), ledger=ledger)
    result = await router.dispatch(_signal(SignalType.PAUSE))
    assert result.status == "paused"
    assert ledger.calls == 1


@pytest.mark.asyncio
async def test_router_authorization_blocked() -> None:
    async def _handler(signal: Signal) -> SignalResult:  # noqa: ARG001
        return SignalResult(status="paused")

    router = SignalRouter(handlers={SignalType.PAUSE: _handler}, authorizer=_Authorizer(False))
    result = await router.dispatch(_signal(SignalType.PAUSE))
    assert result.status == "error"
    assert result.error_code == "unauthorized"


class _ScalarRows:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)


class _ExecResult:
    def __init__(self, rows=None, rowcount=None):
        self._rows = rows or []
        self.rowcount = rowcount

    def scalars(self):
        return _ScalarRows(self._rows)


class _FakeSession:
    def __init__(self, scalars=None, executes=None):
        self.scalars = list(scalars or [])
        self.executes = list(executes or [])
        self.added = []
        self.deleted = []
        self.commits = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):  # noqa: ANN001
        return False

    async def scalar(self, stmt):  # noqa: ANN001
        _ = stmt
        return self.scalars.pop(0) if self.scalars else None

    async def execute(self, stmt):  # noqa: ANN001
        _ = stmt
        return self.executes.pop(0) if self.executes else _ExecResult()

    def add(self, item):  # noqa: ANN001
        self.added.append(item)

    async def delete(self, item):  # noqa: ANN001
        self.deleted.append(item)

    async def commit(self):
        self.commits += 1


class _FakeSessionFactory:
    def __init__(self, session: _FakeSession):
        self._session = session

    def __call__(self):
        return self._session


@pytest.mark.asyncio
async def test_signal_state_db_get_creates_default_state_when_missing() -> None:
    session = _FakeSession(
        scalars=[None],
        executes=[_ExecResult(rows=[])],
    )
    manager = AgentStateManager(session_factory=_FakeSessionFactory(session))  # type: ignore[arg-type]
    state = await manager.get("a1", "t1")
    assert state.paused is False
    assert state.pending_instructions == []
    assert session.commits == 1
    assert any(isinstance(item, AgentControlStateORM) for item in session.added)


@pytest.mark.asyncio
async def test_signal_state_db_set_paused_add_and_update_paths() -> None:
    existing = AgentControlStateORM(agent_id="a1", tenant_id="t1", paused=False)
    session = _FakeSession(scalars=[None, existing])
    manager = AgentStateManager(session_factory=_FakeSessionFactory(session))  # type: ignore[arg-type]

    await manager.set_paused("a1", "t1", True)
    await manager.set_paused("a1", "t1", False)

    assert session.commits == 2
    assert any(isinstance(item, AgentControlStateORM) for item in session.added)
    assert existing.paused is False


@pytest.mark.asyncio
async def test_signal_state_db_add_consume_and_cleanup_paths() -> None:
    now = datetime.now(timezone.utc)
    oldest = PendingInstructionORM(
        id=uuid4(),
        tenant_id="t1",
        agent_id="a1",
        content="old",
        operator="op",
        source="cli",
        created_at=now - timedelta(minutes=2),
        expires_at=now + timedelta(minutes=5),
        consumed=False,
    )
    row_active = PendingInstructionORM(
        id=uuid4(),
        tenant_id="t1",
        agent_id="a1",
        content="new",
        operator="op",
        source="cli",
        created_at=now - timedelta(minutes=1),
        expires_at=now + timedelta(minutes=5),
        consumed=False,
    )
    session = _FakeSession(
        scalars=[2, oldest],
        executes=[_ExecResult(rows=[row_active]), _ExecResult(rowcount=3)],
    )
    manager = AgentStateManager(max_pending_instructions=2, session_factory=_FakeSessionFactory(session))  # type: ignore[arg-type]
    pending = PendingInstruction.create(content="latest", operator="op", source=SignalSource.CLI, ttl_seconds=3600)
    await manager.add_instruction("a1", "t1", pending)
    consumed = await manager.consume_instructions("a1", "t1")
    cleaned = await manager.cleanup_expired_instructions("a1", "t1")

    assert len(consumed) == 1
    assert consumed[0].content == "new"
    assert cleaned == 3
    assert row_active.consumed is True
    assert row_active.consumed_at is not None
    assert oldest in session.deleted
    assert session.commits == 3
