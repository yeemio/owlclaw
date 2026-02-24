"""DB change trigger manager."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol

from owlclaw.triggers.db_change.adapter import DBChangeAdapter, DBChangeEvent
from owlclaw.triggers.db_change.aggregator import EventAggregator
from owlclaw.triggers.db_change.config import DBChangeTriggerConfig


class GovernanceServiceProtocol(Protocol):
    async def allow_trigger(self, event_name: str, tenant_id: str) -> bool: ...


class AgentRuntimeProtocol(Protocol):
    async def trigger_event(
        self,
        event_name: str,
        payload: dict[str, Any],
        focus: str | None = None,
        tenant_id: str = "default",
    ) -> Any: ...


class LedgerProtocol(Protocol):
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
    ) -> None: ...


@dataclass(slots=True)
class _TriggerState:
    config: DBChangeTriggerConfig
    aggregator: EventAggregator


class DBChangeTriggerManager:
    """Manage db change trigger registrations and dispatch flow."""

    def __init__(
        self,
        *,
        adapter: DBChangeAdapter,
        governance: GovernanceServiceProtocol,
        agent_runtime: AgentRuntimeProtocol,
        ledger: LedgerProtocol | None = None,
    ) -> None:
        self._adapter = adapter
        self._governance = governance
        self._agent_runtime = agent_runtime
        self._ledger = ledger
        self._states: dict[str, _TriggerState] = {}
        self._lock = asyncio.Lock()
        self._started = False
        self._handlers: dict[str, Callable[[list[DBChangeEvent]], Awaitable[None]] | None] = {}
        self._adapter.on_event(self._on_event)

    def register(self, config: DBChangeTriggerConfig, handler: Callable[[list[DBChangeEvent]], Awaitable[None]] | None = None) -> None:
        mode = "hybrid" if config.batch_size and config.debounce_seconds else "batch" if config.batch_size else "debounce" if config.debounce_seconds else "passthrough"
        aggregator = EventAggregator(
            mode=mode,  # type: ignore[arg-type]
            debounce_seconds=config.debounce_seconds,
            batch_size=config.batch_size,
            on_flush=lambda events: self._on_aggregated(config, events),
        )
        self._states[config.channel] = _TriggerState(config=config, aggregator=aggregator)
        self._handlers[config.channel] = handler

    async def start(self) -> None:
        async with self._lock:
            if self._started:
                return
            channels = list(self._states.keys())
            await self._adapter.start(channels)
            self._started = True

    async def stop(self) -> None:
        async with self._lock:
            if not self._started:
                return
            await self._adapter.stop()
            self._started = False

    async def _on_event(self, event: DBChangeEvent) -> None:
        state = self._states.get(event.channel)
        if state is None:
            return
        await state.aggregator.push(event)

    async def _on_aggregated(self, config: DBChangeTriggerConfig, events: list[DBChangeEvent]) -> None:
        allowed = await self._governance.allow_trigger(config.event_name, config.tenant_id)
        if not allowed:
            if self._ledger is not None:
                await self._ledger.record_execution(
                    tenant_id=config.tenant_id,
                    agent_id=config.agent_id,
                    run_id="db-change-blocked",
                    capability_name="db_change_trigger",
                    task_type="trigger",
                    input_params={"channel": config.channel, "event_count": len(events)},
                    output_result=None,
                    decision_reasoning="governance_blocked",
                    execution_time_ms=0,
                    llm_model="",
                    llm_tokens_input=0,
                    llm_tokens_output=0,
                    estimated_cost=Decimal("0"),
                    status="blocked",
                    error_message=None,
                )
            return
        payload = {"channel": config.channel, "events": [event.payload for event in events], "event_count": len(events)}
        await self._agent_runtime.trigger_event(
            event_name=config.event_name,
            payload=payload,
            focus=config.focus,
            tenant_id=config.tenant_id,
        )
        fallback = self._handlers.get(config.channel)
        if fallback is not None:
            await fallback(events)
