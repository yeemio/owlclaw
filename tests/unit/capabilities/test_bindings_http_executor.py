from __future__ import annotations

from collections.abc import Callable, Coroutine

import httpx
import pytest

from owlclaw.capabilities.bindings import CredentialResolver, HTTPBindingConfig, HTTPBindingExecutor, RetryConfig


def _transport(handler: Callable[[httpx.Request], Coroutine[None, None, httpx.Response]]) -> httpx.MockTransport:
    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_http_executor_active_get_with_response_mapping() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/orders/42"
        return httpx.Response(200, json={"data": {"id": 42}})

    executor = HTTPBindingExecutor(transport=_transport(handler))
    config = HTTPBindingConfig(
        method="GET",
        url="https://svc.local/orders/{order_id}",
        response_mapping={"path": "$.data.id", "status_codes": {"200": "success"}},
    )
    result = await executor.execute(config, {"order_id": 42})
    assert result["status_code"] == 200
    assert result["data"] == 42


@pytest.mark.asyncio
async def test_http_executor_active_post_with_template_substitution() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        body = await request.aread()
        assert b"sku-001" in body
        return httpx.Response(201, json={"ok": True})

    resolver = CredentialResolver(config_secrets={"API_TOKEN": "token_123"})
    executor = HTTPBindingExecutor(credential_resolver=resolver, transport=_transport(handler))
    config = HTTPBindingConfig(
        method="POST",
        url="https://svc.local/orders",
        headers={"Authorization": "Bearer ${API_TOKEN}"},
        body_template={"sku": "{sku}"},
    )
    result = await executor.execute(config, {"sku": "sku-001"})
    assert result["status_code"] == 201
    assert result["data"]["ok"] is True


@pytest.mark.asyncio
async def test_http_executor_shadow_mode_blocks_write_operations() -> None:
    called = {"value": False}

    async def handler(request: httpx.Request) -> httpx.Response:
        called["value"] = True
        return httpx.Response(200, json={"ok": True})

    executor = HTTPBindingExecutor(transport=_transport(handler))
    config = HTTPBindingConfig(method="POST", mode="shadow", url="https://svc.local/orders")
    result = await executor.execute(config, {"id": 1})
    assert result["status"] == "shadow"
    assert result["sent"] is False
    assert called["value"] is False


@pytest.mark.asyncio
async def test_http_executor_timeout_retry_with_backoff() -> None:
    attempts = {"value": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        attempts["value"] += 1
        if attempts["value"] < 2:
            raise httpx.ReadTimeout("timeout")
        return httpx.Response(200, json={"ok": True})

    executor = HTTPBindingExecutor(transport=_transport(handler))
    config = HTTPBindingConfig(
        method="GET",
        url="https://svc.local/ping",
        retry=RetryConfig(max_attempts=2, backoff_ms=1, backoff_multiplier=1.0),
        timeout_ms=10,
    )
    result = await executor.execute(config, {})
    assert result["status_code"] == 200
    assert attempts["value"] == 2


@pytest.mark.asyncio
async def test_http_executor_status_code_mapping_to_semantic_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "not found"})

    executor = HTTPBindingExecutor(transport=_transport(handler))
    config = HTTPBindingConfig(
        method="GET",
        url="https://svc.local/orders/404",
        response_mapping={"status_codes": {"404": "not_found"}},
    )
    result = await executor.execute(config, {})
    assert result["data"]["error_type"] == "not_found"

