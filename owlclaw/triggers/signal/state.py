"""In-memory state manager for signal pause/instruction control."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone

from owlclaw.triggers.signal.models import PendingInstruction


@dataclass(slots=True)
class AgentState:
    """One agent's mutable signal state."""

    paused: bool = False
    pending_instructions: list[PendingInstruction] = field(default_factory=list)


class AgentStateManager:
    """State operations for pause/resume and pending instructions."""

    def __init__(self, max_pending_instructions: int = 10) -> None:
        self._max_pending_instructions = max_pending_instructions
        self._states: dict[tuple[str, str], AgentState] = {}
        self._lock = asyncio.Lock()

    async def get(self, agent_id: str, tenant_id: str) -> AgentState:
        async with self._lock:
            key = (tenant_id.strip(), agent_id.strip())
            return self._states.setdefault(key, AgentState())

    async def set_paused(self, agent_id: str, tenant_id: str, paused: bool) -> None:
        async with self._lock:
            key = (tenant_id.strip(), agent_id.strip())
            state = self._states.setdefault(key, AgentState())
            state.paused = paused

    async def add_instruction(self, agent_id: str, tenant_id: str, instruction: PendingInstruction) -> None:
        async with self._lock:
            key = (tenant_id.strip(), agent_id.strip())
            state = self._states.setdefault(key, AgentState())
            if len(state.pending_instructions) >= self._max_pending_instructions:
                state.pending_instructions.pop(0)
            state.pending_instructions.append(instruction)

    async def consume_instructions(self, agent_id: str, tenant_id: str) -> list[PendingInstruction]:
        async with self._lock:
            key = (tenant_id.strip(), agent_id.strip())
            state = self._states.setdefault(key, AgentState())
            now = datetime.now(timezone.utc)
            consumed: list[PendingInstruction] = []
            kept: list[PendingInstruction] = []
            for instruction in state.pending_instructions:
                if instruction.consumed or instruction.is_expired(now):
                    continue
                instruction.consumed = True
                consumed.append(instruction)
            for instruction in state.pending_instructions:
                if not instruction.consumed and not instruction.is_expired(now):
                    kept.append(instruction)
            state.pending_instructions = kept
            return consumed

    async def cleanup_expired_instructions(self, agent_id: str, tenant_id: str) -> int:
        async with self._lock:
            key = (tenant_id.strip(), agent_id.strip())
            state = self._states.setdefault(key, AgentState())
            now = datetime.now(timezone.utc)
            before = len(state.pending_instructions)
            state.pending_instructions = [item for item in state.pending_instructions if not item.is_expired(now) and not item.consumed]
            return before - len(state.pending_instructions)
