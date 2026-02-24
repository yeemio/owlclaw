from __future__ import annotations

import httpx
import pytest

from owlclaw.capabilities.bindings import HTTPBindingConfig, HTTPBindingExecutor


@pytest.mark.asyncio
async def test_http_binding_executor_integration_chain() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/write"):
            return httpx.Response(200, json={"status": "written", "id": 1})
        return httpx.Response(200, json={"data": {"status": "ok", "id": 1}})

    executor = HTTPBindingExecutor(transport=httpx.MockTransport(handler))

    read_config = HTTPBindingConfig(
        method="GET",
        url="https://svc.local/orders/{order_id}",
        response_mapping={"path": "$.data", "status_codes": {"200": "success"}},
    )
    read_result = await executor.execute(read_config, {"order_id": 1})
    assert read_result["data"]["status"] == "ok"

    write_config = HTTPBindingConfig(method="POST", mode="shadow", url="https://svc.local/orders/write")
    shadow_result = await executor.execute(write_config, {"order_id": 1})
    assert shadow_result["status"] == "shadow"

    assert len(requests) == 1
    assert requests[0].url.path == "/orders/1"

