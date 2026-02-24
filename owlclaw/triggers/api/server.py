"""HTTP API trigger server implementation."""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from decimal import Decimal
from time import monotonic
from typing import Any, Protocol
from uuid import uuid4

from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from owlclaw.security.sanitizer import InputSanitizer
from owlclaw.triggers.api.auth import AuthProvider
from owlclaw.triggers.api.config import APITriggerConfig
from owlclaw.triggers.api.handler import parse_request_payload
from owlclaw.triggers.signal.api import register_signal_admin_route
from owlclaw.triggers.signal.router import SignalRouter


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
class GovernanceDecision:
    """Governance result for one incoming API request."""

    allowed: bool
    status_code: int | None = None
    reason: str | None = None


class GovernanceGateProtocol(Protocol):
    async def evaluate_request(
        self,
        event_name: str,
        tenant_id: str,
        payload: dict[str, Any],
    ) -> GovernanceDecision: ...


class APITriggerServer:
    """Starlette-based dynamic API trigger server."""

    def __init__(
        self,
        *,
        host: str = "0.0.0.0",
        port: int = 8080,
        auth_provider: AuthProvider | None = None,
        agent_runtime: AgentRuntimeProtocol | None = None,
        governance_gate: GovernanceGateProtocol | None = None,
        sanitizer: InputSanitizer | None = None,
        ledger: LedgerProtocol | None = None,
        agent_id: str = "api-trigger",
        max_body_bytes: int = 1024 * 1024,
        cors_origins: list[str] | None = None,
    ) -> None:
        self._host = host
        self._port = port
        self._auth_provider = auth_provider
        self._agent_runtime = agent_runtime
        self._governance_gate = governance_gate
        self._sanitizer = sanitizer if sanitizer is not None else InputSanitizer()
        self._ledger = ledger
        self._agent_id = agent_id
        self._max_body_bytes = max_body_bytes

        self._configs: dict[str, APITriggerConfig] = {}
        self._app = Starlette(routes=[])
        self._server: Any | None = None
        self._server_task: asyncio.Task[None] | None = None
        self._runs: dict[str, dict[str, Any]] = {}
        self._signal_admin_registered: bool = False
        origins = cors_origins if cors_origins is not None else ["*"]
        self._app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])
        self._app.router.routes.append(Route("/runs/{run_id}/result", endpoint=self._get_run_result, methods=["GET"]))

    @property
    def app(self) -> Starlette:
        return self._app

    def register(self, config: APITriggerConfig, fallback: Callable[[dict[str, Any]], Awaitable[Any]] | None = None) -> None:
        route_key = f"{config.method}:{config.path}"
        if route_key in self._configs:
            raise ValueError(f"API trigger already registered: {route_key}")

        async def endpoint(request: Request) -> JSONResponse:
            started = monotonic()
            auth_response, auth_identity = await self._authenticate(config, request)
            if auth_response is not None:
                await self._record_execution(
                    config=config,
                    run_id="auth-failed",
                    status="failed",
                    started=started,
                    payload={"auth_identity": auth_identity},
                    output={"error": "unauthorized"},
                    reason="auth_failed",
                )
                return auth_response

            if request.headers.get("content-length"):
                with contextlib.suppress(ValueError):
                    if int(request.headers["content-length"]) > self._max_body_bytes:
                        return JSONResponse({"error": "payload_too_large"}, status_code=413)

            parsed = await parse_request_payload(request)
            body = parsed.body
            if self._sanitizer is not None:
                raw = json.dumps(body, ensure_ascii=False)
                sanitized = self._sanitizer.sanitize(raw, source="api")
                if sanitized.changed:
                    with contextlib.suppress(Exception):
                        parsed_body = json.loads(sanitized.sanitized)
                        body = parsed_body if isinstance(parsed_body, dict) else {"value": parsed_body}

            payload = {
                "body": body,
                "query": parsed.query,
                "path": parsed.path_params,
                "method": request.method,
                "url": str(request.url),
                "auth_identity": auth_identity,
            }

            if self._governance_gate is not None:
                decision = await self._governance_gate.evaluate_request(config.event_name, config.tenant_id, payload)
                if not decision.allowed:
                    status_code = decision.status_code if decision.status_code is not None else 429
                    await self._record_execution(
                        config=config,
                        run_id="governance-blocked",
                        status="blocked",
                        started=started,
                        payload=payload,
                        output=None,
                        reason=decision.reason or "governance_blocked",
                    )
                    return JSONResponse({"error": decision.reason or "governance_blocked"}, status_code=status_code)

            if config.response_mode == "sync":
                response = await self._handle_sync(config, payload, fallback, started)
                return response

            return await self._handle_async(config, payload, fallback, started)

        self._app.router.routes.append(Route(config.path, endpoint=endpoint, methods=[config.method]))
        self._configs[route_key] = config

    def register_signal_admin(
        self,
        *,
        signal_router: SignalRouter,
        path: str = "/admin/signal",
        require_auth: bool = True,
    ) -> None:
        """Register POST /admin/signal on the same Starlette service."""
        if self._signal_admin_registered:
            raise ValueError("Signal admin route already registered")
        register_signal_admin_route(
            app_routes=self._app.router.routes,
            router=signal_router,
            auth_provider=self._auth_provider,
            require_auth=require_auth,
            path=path,
        )
        self._signal_admin_registered = True

    async def start(self) -> None:
        if self._server_task is not None:
            return
        try:
            import uvicorn  # type: ignore[import-not-found]
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

    async def _authenticate(self, config: APITriggerConfig, request: Request) -> tuple[JSONResponse | None, str | None]:
        if not config.auth_required:
            return None, None
        if self._auth_provider is None:
            return JSONResponse({"error": "unauthorized", "reason": "auth_provider_missing"}, status_code=401), None
        result = await self._auth_provider.authenticate(request)
        if result.ok:
            return None, result.identity
        return JSONResponse({"error": "unauthorized", "reason": result.reason or "auth_failed"}, status_code=401), result.identity

    async def _handle_sync(
        self,
        config: APITriggerConfig,
        payload: dict[str, Any],
        fallback: Callable[[dict[str, Any]], Awaitable[Any]] | None,
        started: float,
    ) -> JSONResponse:
        run_id = f"sync-{uuid4().hex}"
        if self._agent_runtime is None:
            if fallback is None:
                return JSONResponse({"error": "runtime_unavailable"}, status_code=503)
            result = await fallback(payload)
            await self._record_execution(config, run_id, "success", started, payload, {"result": result}, "fallback")
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
            await self._record_execution(config, run_id, "failed", started, payload, None, "timeout", "sync timeout")
            return JSONResponse({"error": "timeout"}, status_code=408)

        await self._record_execution(config, run_id, "success", started, payload, {"result": result}, "sync_completed")
        return JSONResponse({"status": "ok", "result": result})

    async def _handle_async(
        self,
        config: APITriggerConfig,
        payload: dict[str, Any],
        fallback: Callable[[dict[str, Any]], Awaitable[Any]] | None,
        started: float,
    ) -> JSONResponse:
        run_id = f"run-{uuid4().hex}"
        self._runs[run_id] = {"status": "pending"}

        async def _background() -> None:
            try:
                if self._agent_runtime is not None:
                    result = await self._agent_runtime.trigger_event(
                        event_name=config.event_name,
                        payload=payload,
                        focus=config.focus,
                        tenant_id=config.tenant_id,
                    )
                elif fallback is not None:
                    result = await fallback(payload)
                else:
                    raise RuntimeError("runtime_unavailable")
                self._runs[run_id] = {"status": "completed", "result": result}
                await self._record_execution(config, run_id, "success", started, payload, {"result": result}, "async_completed")
            except Exception as exc:
                self._runs[run_id] = {"status": "failed", "error": str(exc)}
                await self._record_execution(config, run_id, "failed", started, payload, None, "async_failed", str(exc))

        asyncio.create_task(_background())
        return JSONResponse(
            {"status": "accepted", "run_id": run_id},
            status_code=202,
            headers={"Location": f"/runs/{run_id}/result"},
        )

    async def _get_run_result(self, request: Request) -> JSONResponse:
        run_id = str(request.path_params.get("run_id", "")).strip()
        run = self._runs.get(run_id)
        if run is None:
            return JSONResponse({"error": "not_found"}, status_code=404)
        return JSONResponse({"run_id": run_id, **run})

    async def _record_execution(
        self,
        config: APITriggerConfig,
        run_id: str,
        status: str,
        started: float,
        payload: dict[str, Any],
        output: dict[str, Any] | None,
        reason: str,
        error_message: str | None = None,
    ) -> None:
        if self._ledger is None:
            return
        with contextlib.suppress(Exception):
            await self._ledger.record_execution(
                tenant_id=config.tenant_id,
                agent_id=self._agent_id,
                run_id=run_id,
                capability_name="api_trigger",
                task_type="trigger",
                input_params=payload,
                output_result=output,
                decision_reasoning=reason,
                execution_time_ms=int((monotonic() - started) * 1000),
                llm_model="",
                llm_tokens_input=0,
                llm_tokens_output=0,
                estimated_cost=Decimal("0"),
                status=status,
                error_message=error_message,
            )
