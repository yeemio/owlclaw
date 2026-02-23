"""Integration tests for agent built-in tools component contracts."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from owlclaw.agent import BuiltInTools, BuiltInToolsContext
from owlclaw.agent.memory.embedder_random import RandomEmbedder
from owlclaw.agent.memory.models import MemoryConfig
from owlclaw.agent.memory.service import MemoryService
from owlclaw.agent.memory.store_inmemory import InMemoryStore
from owlclaw.agent.runtime.context import AgentRunContext
from owlclaw.agent.runtime.runtime import AgentRuntime

pytestmark = pytest.mark.integration


class _Registry:
    def __init__(self, *, delay_seconds: float = 0.0) -> None:
        self.delay_seconds = delay_seconds
        self.calls: list[str] = []

    async def get_state(self, state_name: str) -> dict[str, object]:
        self.calls.append(state_name)
        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)
        if state_name != "market_state":
            raise ValueError(f"No state provider registered for '{state_name}'")
        return {"is_trading_time": False, "phase": "post_close"}


class _Memory:
    def __init__(self) -> None:
        self.writes: list[tuple[str, list[str]]] = []

    async def write(self, *, content: str, tags: list[str]) -> dict[str, str]:
        self.writes.append((content, tags))
        return {"memory_id": "mem-1", "created_at": "2026-02-23T00:00:00Z"}

    async def search(self, *, query: str, limit: int, tags: list[str]) -> list[dict[str, object]]:
        if query == "lesson":
            return [{"content": "lesson", "tags": tags, "score": 0.9}]
        return []


class _MemoryServiceAdapter:
    """Adapter from MemoryService API to BuiltInTools memory interface."""

    def __init__(self, service: MemoryService, *, agent_id: str, tenant_id: str) -> None:
        self._service = service
        self._agent_id = agent_id
        self._tenant_id = tenant_id

    async def write(self, *, content: str, tags: list[str]) -> dict[str, str]:
        memory_id = await self._service.remember(
            agent_id=self._agent_id,
            tenant_id=self._tenant_id,
            content=content,
            tags=tags,
        )
        return {"memory_id": str(memory_id), "created_at": "2026-02-23T00:00:00Z"}

    async def search(self, *, query: str, limit: int, tags: list[str]) -> list[dict[str, object]]:
        results = await self._service.recall(
            agent_id=self._agent_id,
            tenant_id=self._tenant_id,
            query=query,
            limit=limit,
            tags=tags,
        )
        return [
            {
                "memory_id": str(item.entry.id),
                "content": item.entry.content,
                "tags": item.entry.tags,
                "score": item.score,
            }
            for item in results
        ]


def _tool_call(name: str, arguments: dict[str, object]) -> object:
    return SimpleNamespace(
        function=SimpleNamespace(name=name, arguments=json.dumps(arguments))
    )


@pytest.mark.asyncio
async def test_schedule_tools_integrate_with_hatchet_client_contract() -> None:
    hatchet = AsyncMock()
    hatchet.schedule_task.return_value = "once-1"
    hatchet.schedule_cron.return_value = "cron-1"
    hatchet.cancel_task.return_value = True
    ledger = AsyncMock()
    tools = BuiltInTools(hatchet_client=hatchet, ledger=ledger)
    ctx = BuiltInToolsContext(agent_id="agent-a", run_id="run-a", tenant_id="tenant-a")

    once = await tools.execute("schedule_once", {"delay_seconds": 60, "focus": "check"}, ctx)
    cron = await tools.execute("schedule_cron", {"cron_expression": "0 9 * * 1-5", "focus": "daily"}, ctx)
    cancelled = await tools.execute("cancel_schedule", {"schedule_id": "once-1"}, ctx)

    assert once["schedule_id"] == "once-1"
    assert cron["schedule_id"] == "cron-1"
    assert cancelled["cancelled"] is True
    hatchet.schedule_task.assert_awaited_once()
    hatchet.schedule_cron.assert_awaited_once()
    hatchet.cancel_task.assert_awaited_once_with("once-1")


@pytest.mark.asyncio
async def test_query_state_integrates_with_registry_async_and_timeout() -> None:
    registry = _Registry(delay_seconds=0.0)
    tools = BuiltInTools(capability_registry=registry, timeout_seconds=0.1)
    ctx = BuiltInToolsContext(agent_id="agent-a", run_id="run-a")

    result = await tools.execute("query_state", {"state_name": "market_state"}, ctx)
    assert result["state"]["phase"] == "post_close"
    assert registry.calls == ["market_state"]

    slow_registry = _Registry(delay_seconds=0.05)
    timeout_tools = BuiltInTools(capability_registry=slow_registry, timeout_seconds=0.01)
    timeout_result = await timeout_tools.execute("query_state", {"state_name": "market_state"}, ctx)
    assert "error" in timeout_result
    assert "timed out" in timeout_result["error"]


@pytest.mark.asyncio
async def test_builtin_tools_record_complete_ledger_context() -> None:
    hatchet = AsyncMock()
    hatchet.schedule_task.return_value = "once-1"
    hatchet.cancel_task.return_value = True
    memory = _Memory()
    registry = _Registry()
    ledger = AsyncMock()
    tools = BuiltInTools(
        capability_registry=registry,
        ledger=ledger,
        hatchet_client=hatchet,
        memory_system=memory,
    )
    ctx = BuiltInToolsContext(agent_id="agent-a", run_id="run-a", tenant_id="tenant-a")

    await tools.execute("query_state", {"state_name": "market_state"}, ctx)
    await tools.execute("schedule_once", {"delay_seconds": 5, "focus": "later"}, ctx)
    await tools.execute("remember", {"content": "lesson", "tags": ["trading"]}, ctx)
    await tools.execute("recall", {"query": "lesson", "limit": 3, "tags": ["trading"]}, ctx)
    await tools.execute("cancel_schedule", {"schedule_id": "once-1"}, ctx)
    await tools.execute("log_decision", {"reasoning": "recorded", "decision_type": "other"}, ctx)

    assert ledger.record_execution.await_count >= 6
    first = ledger.record_execution.await_args_list[0].kwargs
    assert first["tenant_id"] == "tenant-a"
    assert first["agent_id"] == "agent-a"
    assert first["run_id"] == "run-a"
    assert "capability_name" in first
    assert "input_params" in first
    assert "status" in first


@pytest.mark.asyncio
async def test_agent_runtime_dispatches_builtin_tool_calls() -> None:
    registry = _Registry()
    builtin_tools = BuiltInTools(capability_registry=registry)
    runtime = AgentRuntime(
        agent_id="agent-a",
        app_dir=".",
        builtin_tools=builtin_tools,
    )
    context = AgentRunContext(agent_id="agent-a", trigger="cron", run_id="run-a")

    result = await runtime._execute_tool(  # noqa: SLF001
        _tool_call("query_state", {"state_name": "market_state"}),
        context,
    )
    assert result["state"]["is_trading_time"] is False


@pytest.mark.asyncio
async def test_memory_service_adapter_contract_with_builtin_tools() -> None:
    service = MemoryService(
        store=InMemoryStore(),
        embedder=RandomEmbedder(dimensions=8),
        config=MemoryConfig(vector_backend="inmemory", embedding_dimensions=8),
    )
    memory = _MemoryServiceAdapter(service, agent_id="agent-a", tenant_id="tenant-a")
    tools = BuiltInTools(memory_system=memory)
    ctx = BuiltInToolsContext(agent_id="agent-a", run_id="run-a", tenant_id="tenant-a")

    remember_result = await tools.execute("remember", {"content": "lesson about retries", "tags": ["ops"]}, ctx)
    recall_result = await tools.execute("recall", {"query": "lesson", "limit": 3, "tags": ["ops"]}, ctx)

    assert remember_result["memory_id"]
    assert recall_result["count"] >= 1
    assert any("lesson about retries" in item["content"] for item in recall_result["memories"])
