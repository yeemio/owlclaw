"""HTTP API trigger server implementation."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from owlclaw.triggers.api.auth import AuthProvider
from owlclaw.triggers.api.config import APITriggerConfig
from owlclaw.triggers.api.handler import parse_request_payload


class AgentRuntimeProtocol(Protocol):
    async def trigger_event(
        self,
        event_name: str,
        payload: dict[str, Any],
        focus: str | None = None,
        tenant_id: str = "default",
    ) -> Any: ...


class APITriggerServer:
    """Starlette-based dynamic API trigger server."""

    def __init__(
        self,
        *,
        host: str = "0.0.0.0",
        port: int = 8080,
        auth_provider: AuthProvider | None = None,
        agent_runtime: AgentRuntimeProtocol | None = None,
        cors_origins: list[str] | None = None,
    ) -> None:
        self._host = host
        self._port = port
        self._auth_provider = auth_provider
        self._agent_runtime = agent_runtime
        self._configs: dict[str, APITriggerConfig] = {}
        self._app = Starlette(routes=[])
        self._server: Any | None = None
        self._server_task: asyncio.Task[None] | None = None
        origins = cors_origins if cors_origins is not None else ["*"]
        self._app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])

    @property
    def app(self) -> Starlette:
        return self._app

    def register(self, config: APITriggerConfig, fallback: Callable[[dict[str, Any]], Awaitable[Any]] | None = None) -> None:
        route_key = f"{config.method}:{config.path}"
        if route_key in self._configs:
            raise ValueError(f"API trigger already registered: {route_key}")

        async def endpoint(request: Request) -> JSONResponse:
            auth_result = await self._authenticate(config, request)
            if auth_result is not None:
                return auth_result

            parsed = await parse_request_payload(request)
            payload = {
                "body": parsed.body,
                "query": parsed.query,
                "path": parsed.path_params,
                "method": request.method,
                "url": str(request.url),
            }

            if config.response_mode == "sync":
                if self._agent_runtime is None:
                    if fallback is None:
                        return JSONResponse({"error": "runtime_unavailable"}, status_code=503)
                    result = await fallback(payload)
                    return JSONResponse({"status": "ok", "result": result})
                try:
                    result = await asyncio.wait_for(
                        self._agent_runtime.trigger_event(
                            event_name=config.event_name,
                            payload=payload,
                            focus=config.focus,
                            tenant_id=config.tenant_id,
                        ),
                        timeout=float(config.sync_timeout_seconds),
                    )
                except asyncio.TimeoutError:
                    return JSONResponse({"error": "timeout"}, status_code=408)
                return JSONResponse({"status": "ok", "result": result})

            run_id = f"run-{abs(hash((config.event_name, str(payload)))) % 10_000_000}"
            if self._agent_runtime is not None:
                asyncio.create_task(
                    self._agent_runtime.trigger_event(
                        event_name=config.event_name,
                        payload=payload,
                        focus=config.focus,
                        tenant_id=config.tenant_id,
                    )
                )
            elif fallback is not None:
                asyncio.create_task(fallback(payload))
            return JSONResponse({"status": "accepted", "run_id": run_id}, status_code=202, headers={"Location": f"/runs/{run_id}/result"})

        self._app.router.routes.append(Route(config.path, endpoint=endpoint, methods=[config.method]))
        self._configs[route_key] = config

    async def start(self) -> None:
        if self._server_task is not None:
            return
        try:
            import uvicorn
        except ImportError as exc:  # pragma: no cover - optional runtime dependency
            raise RuntimeError("uvicorn is required to start APITriggerServer") from exc
        config = uvicorn.Config(self._app, host=self._host, port=self._port, log_level="warning")
        self._server = uvicorn.Server(config=config)
        self._server_task = asyncio.create_task(self._server.serve())

    async def stop(self) -> None:
        if self._server is not None:
            self._server.should_exit = True
        if self._server_task is not None:
            await self._server_task
            self._server_task = None
            self._server = None

    async def _authenticate(self, config: APITriggerConfig, request: Request) -> JSONResponse | None:
        if not config.auth_required:
            return None
        if self._auth_provider is None:
            return JSONResponse({"error": "unauthorized", "reason": "auth_provider_missing"}, status_code=401)
        result = await self._auth_provider.authenticate(request)
        if result.ok:
            return None
        return JSONResponse({"error": "unauthorized", "reason": result.reason or "auth_failed"}, status_code=401)
