"""Request handlers for API trigger server."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from starlette.requests import Request


@dataclass(slots=True)
class APITriggerRequest:
    """Normalized request payload consumed by trigger runtime."""

    body: dict[str, Any]
    query: dict[str, str]
    path_params: dict[str, str]


async def parse_request_payload(request: Request) -> APITriggerRequest:
    """Parse request body/query/path into normalized payload."""
    body: dict[str, Any] = {}
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        try:
            parsed = await request.json()
            body = parsed if isinstance(parsed, dict) else {"value": parsed}
        except Exception:
            body = {}
    query = {key: value for key, value in request.query_params.items()}
    path_params = {str(k): str(v) for k, v in request.path_params.items()}
    return APITriggerRequest(body=body, query=query, path_params=path_params)
