"""Tests for ledger API and provider."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

from owlclaw.web import create_console_app
from owlclaw.web.providers.ledger import DefaultLedgerProvider


class _LedgerProviderStub:
    def __init__(self) -> None:
        self.last_query_args: dict[str, Any] | None = None

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
        self.last_query_args = {
            "tenant_id": tenant_id,
            "agent_id": agent_id,
            "capability_name": capability_name,
            "status": status,
            "start_date": start_date,
            "end_date": end_date,
            "min_cost": min_cost,
            "max_cost": max_cost,
            "limit": limit,
            "offset": offset,
            "order_by": order_by,
        }
        return (
            [
                {
                    "id": "r1",
                    "status": "success",
                    "estimated_cost": "1.50",
                }
            ],
            1,
        )

    async def get_record_detail(self, record_id: str, tenant_id: str) -> dict[str, Any] | None:
        if record_id == "missing":
            return None
        return {"id": record_id, "tenant_id": tenant_id, "status": "success"}


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


def _build_app(ledger_provider: _LedgerProviderStub):
    return create_console_app(
        providers={
            "overview": _OverviewProviderStub(),
            "governance": _GovernanceProviderStub(),
            "triggers": object(),
            "agents": object(),
            "capabilities": object(),
            "ledger": ledger_provider,
            "settings": object(),
        }
    )


def test_ledger_list_route_returns_paginated_payload() -> None:
    provider = _LedgerProviderStub()
    app = _build_app(provider)
    client = TestClient(app)

    response = client.get(
        "/api/v1/ledger?agent_id=a1&capability_name=cap-x&status=success&start_date=2026-03-01&end_date=2026-03-02&min_cost=1.2&max_cost=2.5&limit=20&offset=5&order_by=cost_desc"
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["offset"] == 5
    assert payload["items"][0]["estimated_cost"] == "1.50"
    assert provider.last_query_args is not None
    assert provider.last_query_args["agent_id"] == "a1"
    assert provider.last_query_args["order_by"] == "cost_desc"


def test_ledger_detail_route_returns_404_when_not_found() -> None:
    provider = _LedgerProviderStub()
    app = _build_app(provider)
    client = TestClient(app)

    response = client.get("/api/v1/ledger/missing")
    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "NOT_FOUND"
    assert payload["error"]["message"] == "Ledger record not found"


def test_ledger_detail_route_returns_payload() -> None:
    provider = _LedgerProviderStub()
    app = _build_app(provider)
    client = TestClient(app)

    response = client.get("/api/v1/ledger/rec-1")
    assert response.status_code == 200
    assert response.json()["id"] == "rec-1"


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
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def scalars(self) -> _FakeRowsResult:
        return self

    def all(self) -> list[Any]:
        return self._rows

    def scalar_one_or_none(self) -> Any:
        if not self._rows:
            return None
        return self._rows[0]


class _FakeCountResult:
    def __init__(self, count: int) -> None:
        self._count = count

    def scalar_one(self) -> int:
        return self._count


class _FakeSession:
    def __init__(self, results: list[Any]) -> None:
        self._results = list(results)

    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        _ = (exc_type, exc, tb)

    async def execute(self, statement: Any) -> Any:
        _ = statement
        return self._results.pop(0)


def _fake_session_factory(results: list[Any]):
    def _factory(_engine: Any):
        def _session() -> _FakeSession:
            return _FakeSession(results)

        return _session

    return _factory


@pytest.mark.asyncio
async def test_default_ledger_provider_query_records_serializes_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    from owlclaw.web.providers import ledger as module

    record = _Record(
        id=uuid.uuid4(),
        tenant_id="default",
        agent_id="agent-1",
        run_id="run-1",
        capability_name="cap-a",
        task_type="analysis",
        input_params={"foo": "bar"},
        output_result={"ok": True},
        decision_reasoning="because",
        execution_time_ms=120,
        llm_model="gpt-5",
        llm_tokens_input=10,
        llm_tokens_output=20,
        estimated_cost=Decimal("1.23"),
        status="success",
        error_message=None,
        migration_weight=100,
        execution_mode="agent",
        risk_level=Decimal("0.25"),
        approval_by=None,
        approval_time=None,
        created_at=datetime(2026, 3, 2, 10, 0, tzinfo=UTC),
    )

    monkeypatch.setattr(module, "get_engine", lambda: object())
    monkeypatch.setattr(
        module,
        "create_session_factory",
        _fake_session_factory([_FakeCountResult(1), _FakeRowsResult([record])]),
    )

    provider = DefaultLedgerProvider()
    items, total = await provider.query_records(
        tenant_id="default",
        agent_id="agent-1",
        capability_name=None,
        status="success",
        start_date=None,
        end_date=None,
        min_cost=Decimal("1.0"),
        max_cost=Decimal("2.0"),
        limit=50,
        offset=0,
        order_by="created_at_desc",
    )
    assert total == 1
    assert items[0]["capability_name"] == "cap-a"
    assert items[0]["estimated_cost"] == "1.23"


@pytest.mark.asyncio
async def test_default_ledger_provider_detail_returns_none_for_bad_uuid() -> None:
    provider = DefaultLedgerProvider()
    detail = await provider.get_record_detail(record_id="not-a-uuid", tenant_id="default")
    assert detail is None
