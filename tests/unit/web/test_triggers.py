"""Tests for triggers API and provider."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

from owlclaw.web import create_console_app
from owlclaw.web.providers.triggers import DefaultTriggersProvider


class _TriggersProviderStub:
    async def list_triggers(self, tenant_id: str) -> list[dict[str, Any]]:
        _ = tenant_id
        return [{"id": "cron-job-1", "type": "cron", "enabled": True, "next_run": None, "success_rate": 1.0}]

    async def get_trigger_history(
        self,
        trigger_id: str,
        tenant_id: str,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        _ = (trigger_id, tenant_id, limit, offset)
        return ([{"id": "h1", "trigger_id": trigger_id}], 1)


class _OverviewProviderStub:
    async def get_overview(self, tenant_id: str) -> dict[str, Any]:
        _ = tenant_id
        return {
            "total_cost_today": Decimal("0"),
            "total_executions_today": 0,
            "success_rate_today": 0.0,
            "active_agents": 0,
            "health_checks": [],
        }


class _GovernanceProviderStub:
    async def get_budget_trend(self, tenant_id: str, start_date: date, end_date: date, granularity: str) -> list[dict[str, Any]]:
        _ = (tenant_id, start_date, end_date, granularity)
        return []

    async def get_circuit_breaker_states(self, tenant_id: str) -> list[dict[str, Any]]:
        _ = tenant_id
        return []

    async def get_visibility_matrix(self, tenant_id: str, agent_id: str | None) -> dict[str, Any]:
        _ = (tenant_id, agent_id)
        return {"items": []}


class _LedgerProviderStub:
    async def query_records(
        self,
        tenant_id: str,
        agent_id: str | None,
        capability_name: str | None,
        status: str | None,
        start_date: date | None,
        end_date: date | None,
        min_cost: Decimal | None,
        max_cost: Decimal | None,
        limit: int,
        offset: int,
        order_by: str | None,
    ) -> tuple[list[dict[str, Any]], int]:
        _ = (
            tenant_id,
            agent_id,
            capability_name,
            status,
            start_date,
            end_date,
            min_cost,
            max_cost,
            limit,
            offset,
            order_by,
        )
        return [], 0

    async def get_record_detail(self, record_id: str, tenant_id: str) -> dict[str, Any] | None:
        _ = (record_id, tenant_id)
        return None


def _build_app(provider: _TriggersProviderStub):
    return create_console_app(
        providers={
            "overview": _OverviewProviderStub(),
            "governance": _GovernanceProviderStub(),
            "triggers": provider,
            "agents": object(),
            "capabilities": object(),
            "ledger": _LedgerProviderStub(),
            "settings": object(),
        }
    )


def test_triggers_list_route_returns_items() -> None:
    app = _build_app(_TriggersProviderStub())
    client = TestClient(app)

    response = client.get("/api/v1/triggers")
    assert response.status_code == 200
    assert response.json()["items"][0]["type"] == "cron"


def test_triggers_history_route_returns_paginated_payload() -> None:
    app = _build_app(_TriggersProviderStub())
    client = TestClient(app)

    response = client.get("/api/v1/triggers/cron-job-1/history?limit=10&offset=0")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["trigger_id"] == "cron-job-1"


@dataclass
class _Record:
    id: uuid.UUID
    tenant_id: str
    agent_id: str
    run_id: str
    capability_name: str
    task_type: str
    input_params: dict[str, Any]
    output_result: dict[str, Any] | None
    decision_reasoning: str | None
    execution_time_ms: int
    llm_model: str
    llm_tokens_input: int
    llm_tokens_output: int
    estimated_cost: Decimal
    status: str
    error_message: str | None
    migration_weight: int | None
    execution_mode: str | None
    risk_level: Decimal | None
    approval_by: str | None
    approval_time: datetime | None
    created_at: datetime


class _FakeRowsResult:
    def __init__(self, rows: list[_Record]) -> None:
        self._rows = rows

    def scalars(self) -> _FakeRowsResult:
        return self

    def all(self) -> list[_Record]:
        return self._rows


class _FakeSession:
    def __init__(self, rows: list[_Record]) -> None:
        self._rows = rows

    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        _ = (exc_type, exc, tb)

    async def execute(self, statement: Any) -> _FakeRowsResult:
        _ = statement
        return _FakeRowsResult(self._rows)


def _fake_session_factory(rows: list[_Record]):
    def _factory(_engine: Any):
        def _session() -> _FakeSession:
            return _FakeSession(rows)

        return _session

    return _factory


@pytest.mark.asyncio
async def test_default_triggers_provider_returns_unified_six_types(monkeypatch: pytest.MonkeyPatch) -> None:
    from owlclaw.web.providers import triggers as module

    now = datetime.now(tz=UTC)
    rows = [
        _Record(
            id=uuid.uuid4(),
            tenant_id="default",
            agent_id="agent-a",
            run_id="run-1",
            capability_name="nightly-cron",
            task_type="cron_execution",
            input_params={"trigger_type": "cron", "trigger_id": "nightly-cron"},
            output_result=None,
            decision_reasoning=None,
            execution_time_ms=100,
            llm_model="gpt-5",
            llm_tokens_input=0,
            llm_tokens_output=0,
            estimated_cost=Decimal("0"),
            status="success",
            error_message=None,
            migration_weight=None,
            execution_mode=None,
            risk_level=None,
            approval_by=None,
            approval_time=None,
            created_at=now - timedelta(minutes=1),
        ),
        _Record(
            id=uuid.uuid4(),
            tenant_id="default",
            agent_id="agent-a",
            run_id="run-2",
            capability_name="queue-orders",
            task_type="queue_trigger",
            input_params={"trigger_type": "queue", "trigger_id": "queue-orders"},
            output_result=None,
            decision_reasoning=None,
            execution_time_ms=100,
            llm_model="gpt-5",
            llm_tokens_input=0,
            llm_tokens_output=0,
            estimated_cost=Decimal("0"),
            status="failed",
            error_message="oops",
            migration_weight=None,
            execution_mode=None,
            risk_level=None,
            approval_by=None,
            approval_time=None,
            created_at=now - timedelta(minutes=2),
        ),
    ]
    monkeypatch.setattr(module, "get_engine", lambda: object())
    monkeypatch.setattr(module, "create_session_factory", _fake_session_factory(rows))

    provider = DefaultTriggersProvider()
    items = await provider.list_triggers("default")
    assert len(items) >= 6
    assert {"cron", "webhook", "queue", "db_change", "api", "signal"}.issubset({item["type"] for item in items})
    cron_item = next(item for item in items if item["id"] == "nightly-cron")
    assert cron_item["enabled"] is True


@pytest.mark.asyncio
async def test_default_triggers_provider_history_is_paginated(monkeypatch: pytest.MonkeyPatch) -> None:
    from owlclaw.web.providers import triggers as module

    now = datetime.now(tz=UTC)
    rows = [
        _Record(
            id=uuid.uuid4(),
            tenant_id="default",
            agent_id="agent-a",
            run_id=f"run-{idx}",
            capability_name="nightly-cron",
            task_type="cron_execution",
            input_params={"trigger_type": "cron", "trigger_id": "nightly-cron"},
            output_result=None,
            decision_reasoning=None,
            execution_time_ms=100,
            llm_model="gpt-5",
            llm_tokens_input=0,
            llm_tokens_output=0,
            estimated_cost=Decimal("0"),
            status="success",
            error_message=None,
            migration_weight=None,
            execution_mode=None,
            risk_level=None,
            approval_by=None,
            approval_time=None,
            created_at=now - timedelta(minutes=idx),
        )
        for idx in range(5)
    ]
    monkeypatch.setattr(module, "get_engine", lambda: object())
    monkeypatch.setattr(module, "create_session_factory", _fake_session_factory(rows))

    provider = DefaultTriggersProvider()
    items, total = await provider.get_trigger_history(trigger_id="nightly-cron", tenant_id="default", limit=2, offset=1)
    assert total == 5
    assert len(items) == 2
