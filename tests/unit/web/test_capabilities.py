"""Tests for capabilities API and provider."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

from owlclaw.db.exceptions import ConfigurationError
from owlclaw.web import create_console_app
from owlclaw.web.providers import capabilities as capabilities_module
from owlclaw.web.providers.capabilities import DefaultCapabilitiesProvider


class _CapabilitiesProviderStub:
    def __init__(self) -> None:
        self.last_category: str | None = None

    async def list_capabilities(self, tenant_id: str, category: str | None) -> list[dict[str, Any]]:
        _ = tenant_id
        self.last_category = category
        return [{"name": "cap-a", "category": category or "handler"}]

    async def get_capability_schema(self, capability_name: str) -> dict[str, Any] | None:
        if capability_name == "missing":
            return None
        return {"type": "object", "properties": {"x": {"type": "string"}}, "required": ["x"]}


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


def _build_app(provider: _CapabilitiesProviderStub):
    return create_console_app(
        providers={
            "overview": _OverviewProviderStub(),
            "governance": _GovernanceProviderStub(),
            "triggers": object(),
            "agents": object(),
            "capabilities": provider,
            "ledger": _LedgerProviderStub(),
            "settings": object(),
        }
    )


def test_capabilities_list_route_passes_category() -> None:
    provider = _CapabilitiesProviderStub()
    app = _build_app(provider)
    client = TestClient(app)

    response = client.get("/api/v1/capabilities?category=binding")
    assert response.status_code == 200
    assert response.json()["items"][0]["category"] == "binding"
    assert provider.last_category == "binding"


def test_capabilities_schema_route_returns_schema() -> None:
    provider = _CapabilitiesProviderStub()
    app = _build_app(provider)
    client = TestClient(app)

    response = client.get("/api/v1/capabilities/cap-a/schema")
    assert response.status_code == 200
    assert response.json()["type"] == "object"


def test_capabilities_schema_route_returns_404_when_missing() -> None:
    provider = _CapabilitiesProviderStub()
    app = _build_app(provider)
    client = TestClient(app)

    response = client.get("/api/v1/capabilities/missing/schema")
    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "NOT_FOUND"
    assert payload["error"]["message"] == "Capability schema not found"


def test_capabilities_invalid_category_returns_error_response_shape() -> None:
    provider = _CapabilitiesProviderStub()
    app = _build_app(provider)
    client = TestClient(app)

    response = client.get("/api/v1/capabilities?category=invalid")
    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert "Request validation failed" in payload["error"]["message"]


@dataclass
class _FakeBindingConfig:
    type: str = "http"


class _FakeBindingHandler:
    def __init__(self) -> None:
        self.parameters_schema = {"type": "object", "properties": {"q": {"type": "string"}}, "required": ["q"]}
        self.binding_config = _FakeBindingConfig()

    def __call__(self, q: str) -> dict[str, Any]:
        _ = q
        return {"ok": True}


def _handler_with_signature(user_id: int, include_detail: bool = False) -> dict[str, Any]:
    _ = (user_id, include_detail)
    return {"ok": True}


class _FakeSkill:
    pass


class _FakeSkillsLoader:
    def get_skill(self, name: str) -> _FakeSkill | None:
        if name == "skill_cap":
            return _FakeSkill()
        return None


class _FakeRegistry:
    def __init__(self) -> None:
        self.handlers: dict[str, Any] = {
            "skill_cap": _handler_with_signature,
            "binding_cap": _FakeBindingHandler(),
            "handler_cap": _handler_with_signature,
        }
        self.skills_loader = _FakeSkillsLoader()

    def get_capability_metadata(self, name: str) -> dict[str, Any]:
        return {
            "name": name,
            "description": f"{name} description",
            "task_type": "analysis",
            "constraints": {},
            "focus": [],
            "risk_level": "low",
            "requires_confirmation": False,
            "handler": "callable",
        }


@pytest.mark.asyncio
async def test_default_capabilities_provider_classifies_and_adds_stats() -> None:
    async def _stats_fetcher(_tenant_id: str) -> dict[str, dict[str, Any]]:
        return {"binding_cap": {"executions": 3, "success_rate": 0.6667, "avg_latency_ms": 123.4}}

    provider = DefaultCapabilitiesProvider(
        capability_registry=_FakeRegistry(),  # type: ignore[arg-type]
        stats_fetcher=_stats_fetcher,
    )
    items = await provider.list_capabilities(tenant_id="default", category=None)
    by_name = {item["name"]: item for item in items}
    assert by_name["binding_cap"]["category"] == "binding"
    assert by_name["skill_cap"]["category"] == "skill"
    assert by_name["handler_cap"]["category"] == "handler"
    assert by_name["binding_cap"]["stats"]["executions"] == 3


@pytest.mark.asyncio
async def test_default_capabilities_provider_filters_by_category() -> None:
    provider = DefaultCapabilitiesProvider(
        capability_registry=_FakeRegistry(),  # type: ignore[arg-type]
        stats_fetcher=lambda _tenant_id: _async_value({}),
    )
    items = await provider.list_capabilities(tenant_id="default", category="binding")
    assert [item["name"] for item in items] == ["binding_cap"]


@pytest.mark.asyncio
async def test_default_capabilities_provider_get_schema_from_signature() -> None:
    provider = DefaultCapabilitiesProvider(
        capability_registry=_FakeRegistry(),  # type: ignore[arg-type]
        stats_fetcher=lambda _tenant_id: _async_value({}),
    )
    schema = await provider.get_capability_schema("handler_cap")
    assert schema is not None
    assert schema["properties"]["user_id"]["type"] == "integer"
    assert "user_id" in schema["required"]


async def _async_value(value: Any) -> Any:
    return value


@pytest.mark.asyncio
async def test_default_capabilities_provider_returns_empty_without_registry() -> None:
    provider = DefaultCapabilitiesProvider(capability_registry=None, stats_fetcher=lambda _tenant_id: _async_value({}))
    items = await provider.list_capabilities(tenant_id="default", category=None)
    assert items == []


@pytest.mark.asyncio
async def test_default_capabilities_provider_schema_none_for_missing_registry_and_handler() -> None:
    provider_without_registry = DefaultCapabilitiesProvider(capability_registry=None, stats_fetcher=lambda _tenant_id: _async_value({}))
    assert await provider_without_registry.get_capability_schema("any") is None

    provider_with_registry = DefaultCapabilitiesProvider(
        capability_registry=_FakeRegistry(),  # type: ignore[arg-type]
        stats_fetcher=lambda _tenant_id: _async_value({}),
    )
    assert await provider_with_registry.get_capability_schema("missing") is None


def test_default_capabilities_provider_schema_wraps_non_object_parameters_schema() -> None:
    class _SchemaOnlyHandler:
        parameters_schema = {"x": {"type": "string"}}

        def __call__(self, x: str) -> dict[str, Any]:
            _ = x
            return {"ok": True}

    provider = DefaultCapabilitiesProvider(capability_registry=None, stats_fetcher=lambda _tenant_id: _async_value({}))
    schema = provider._build_schema_from_handler(_SchemaOnlyHandler())
    assert schema["type"] == "object"
    assert schema["properties"]["x"]["type"] == "string"


def test_default_capabilities_provider_schema_handles_type_hints_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def _handler(*args: Any, **kwargs: Any) -> dict[str, Any]:
        _ = (args, kwargs)
        return {"ok": True}

    provider = DefaultCapabilitiesProvider(capability_registry=None, stats_fetcher=lambda _tenant_id: _async_value({}))
    monkeypatch.setattr(capabilities_module, "get_type_hints", lambda _callable: (_ for _ in ()).throw(RuntimeError("boom")))
    schema = provider._build_schema_from_handler(_handler)
    assert schema["type"] == "object"
    assert schema["properties"] == {}
    assert schema["required"] == []


def test_default_capabilities_provider_annotation_to_schema_covers_core_types() -> None:
    provider = DefaultCapabilitiesProvider(capability_registry=None, stats_fetcher=lambda _tenant_id: _async_value({}))
    assert provider._annotation_to_schema(inspect.Parameter.empty)["type"] == "string"
    assert provider._annotation_to_schema(str)["type"] == "string"
    assert provider._annotation_to_schema(int)["type"] == "integer"
    assert provider._annotation_to_schema(float)["type"] == "number"
    assert provider._annotation_to_schema(bool)["type"] == "boolean"
    assert provider._annotation_to_schema(dict)["type"] == "object"
    assert provider._annotation_to_schema(list)["type"] == "array"
    assert provider._annotation_to_schema(list[int])["items"]["type"] == "integer"
    assert provider._annotation_to_schema(dict[str, Any])["type"] == "object"
    assert provider._annotation_to_schema(int | None)["type"] == "integer"
    assert provider._annotation_to_schema(int | str | None)["type"] == "string"


@pytest.mark.asyncio
async def test_default_capabilities_provider_collect_stats_aggregates_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [
        ("cap_a", 4, 3, 12.5),
        ("cap_b", 0, 0, None),
    ]

    class _FakeResult:
        def all(self) -> list[tuple[str, int, int, float | None]]:
            return rows

    class _FakeSession:
        async def execute(self, _statement: Any) -> _FakeResult:
            return _FakeResult()

    class _FakeSessionContext:
        async def __aenter__(self) -> _FakeSession:
            return _FakeSession()

        async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
            _ = (exc_type, exc, tb)
            return False

    def _fake_create_session_factory(_engine: Any):
        def _factory() -> _FakeSessionContext:
            return _FakeSessionContext()

        return _factory

    monkeypatch.setattr(capabilities_module, "get_engine", lambda: object())
    monkeypatch.setattr(capabilities_module, "create_session_factory", _fake_create_session_factory)

    provider = DefaultCapabilitiesProvider(capability_registry=None, stats_fetcher=lambda _tenant_id: _async_value({}))
    stats = await provider._collect_capability_stats("tenant-a")
    assert stats["cap_a"]["executions"] == 4
    assert stats["cap_a"]["success_rate"] == 0.75
    assert stats["cap_a"]["avg_latency_ms"] == 12.5
    assert stats["cap_b"]["success_rate"] == 0.0


@pytest.mark.asyncio
async def test_default_capabilities_provider_collect_stats_returns_empty_when_db_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        capabilities_module,
        "get_engine",
        lambda: (_ for _ in ()).throw(ConfigurationError("missing db url")),
    )
    provider = DefaultCapabilitiesProvider(capability_registry=None, stats_fetcher=lambda _tenant_id: _async_value({}))
    assert await provider._collect_capability_stats("tenant-a") == {}
