"""FastAPI gateway for webhook trigger pipeline."""

from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from owlclaw.triggers.webhook.event_logger import EventLogger, build_event
from owlclaw.triggers.webhook.execution import ExecutionTrigger
from owlclaw.triggers.webhook.governance import GovernanceClient
from owlclaw.triggers.webhook.manager import WebhookEndpointManager
from owlclaw.triggers.webhook.monitoring import MonitoringService
from owlclaw.triggers.webhook.transformer import PayloadTransformer
from owlclaw.triggers.webhook.types import (
    AuthMethod,
    EndpointConfig,
    EventFilter,
    ExecutionOptions,
    FieldMapping,
    GovernanceContext,
    HttpRequest,
    MetricRecord,
    TransformationRule,
    ValidationError,
)
from owlclaw.triggers.webhook.validator import RequestValidator


@dataclass(slots=True)
class HttpGatewayConfig:
    """Configuration for webhook HTTP gateway."""

    cors_origins: list[str] = field(default_factory=lambda: ["*"])
    tls_enabled: bool = False
    per_ip_limit_per_minute: int = 120
    per_endpoint_limit_per_minute: int = 300


class _RateLimiter:
    def __init__(self, *, per_ip_limit: int, per_endpoint_limit: int) -> None:
        self._per_ip_limit = per_ip_limit
        self._per_endpoint_limit = per_endpoint_limit
        self._ip_window: dict[str, deque[datetime]] = {}
        self._endpoint_window: dict[str, deque[datetime]] = {}

    def check(self, ip: str, endpoint_id: str) -> ValidationError | None:
        now = datetime.now(timezone.utc)
        if self._check_key(self._ip_window, ip, now, self._per_ip_limit):
            return ValidationError(code="RATE_LIMITED", message="ip rate limit exceeded", status_code=429)
        if self._check_key(self._endpoint_window, endpoint_id, now, self._per_endpoint_limit):
            return ValidationError(code="RATE_LIMITED", message="endpoint rate limit exceeded", status_code=429)
        return None

    @staticmethod
    def _check_key(store: dict[str, deque[datetime]], key: str, now: datetime, limit: int) -> bool:
        window = store.get(key)
        if window is None:
            window = deque()
            store[key] = window
        cutoff = now - timedelta(minutes=1)
        while window and window[0] < cutoff:
            window.popleft()
        if len(window) >= limit:
            return True
        window.append(now)
        return False


def create_webhook_app(
    *,
    manager: WebhookEndpointManager,
    validator: RequestValidator,
    transformer: PayloadTransformer,
    governance: GovernanceClient,
    execution: ExecutionTrigger,
    event_logger: EventLogger,
    monitoring: MonitoringService,
    config: HttpGatewayConfig | None = None,
) -> FastAPI:
    """Create FastAPI app bound to webhook trigger services."""

    cfg = config or HttpGatewayConfig()
    app = FastAPI(title="OwlClaw Webhook Gateway")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.tls_enabled = cfg.tls_enabled
    limiter = _RateLimiter(
        per_ip_limit=cfg.per_ip_limit_per_minute,
        per_endpoint_limit=cfg.per_endpoint_limit_per_minute,
    )

    @app.middleware("http")
    async def _request_trace_middleware(request: Request, call_next: Any) -> JSONResponse:
        request_id = request.headers.get("x-request-id", str(uuid4()))
        request.state.request_id = request_id
        started = datetime.now(timezone.utc)
        response = await call_next(request)
        elapsed = (datetime.now(timezone.utc) - started).total_seconds() * 1000.0
        response.headers["x-request-id"] = request_id
        await monitoring.record_metric(MetricRecord(name="response_time_ms", value=elapsed))
        return response

    @app.post("/webhooks/{endpoint_id}")
    async def receive_webhook(endpoint_id: str, request: Request) -> JSONResponse:
        request_id = str(getattr(request.state, "request_id", uuid4()))
        ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent")
        raw_body = (await request.body()).decode("utf-8")
        await monitoring.record_metric(MetricRecord(name="request_count", value=1))
        await event_logger.log_request(
            build_event(
                endpoint_id=endpoint_id,
                request_id=request_id,
                event_type="request",
                source_ip=ip,
                user_agent=user_agent,
                data={"headers": dict(request.headers)},
            )
        )
        limit_error = limiter.check(ip=ip, endpoint_id=endpoint_id)
        if limit_error is not None:
            await monitoring.record_metric(MetricRecord(name="request_status", value=1, tags={"status": "failure"}))
            return _error_response(limit_error, request_id=request_id)

        endpoint, validation = await validator.validate_request(
            endpoint_id, HttpRequest(headers=dict(request.headers), body=raw_body)
        )
        if not validation.valid:
            await event_logger.log_validation(
                build_event(
                    endpoint_id=endpoint_id,
                    request_id=request_id,
                    event_type="validation",
                    status="failed",
                    error=(None if validation.error is None else {"code": validation.error.code, "message": validation.error.message}),
                )
            )
            await monitoring.record_metric(MetricRecord(name="request_status", value=1, tags={"status": "failure"}))
            assert validation.error is not None
            return _error_response(validation.error, request_id=request_id)
        assert endpoint is not None

        parsed, parse_result = transformer.parse_safe(HttpRequest(headers=dict(request.headers), body=raw_body))
        if not parse_result.valid:
            await monitoring.record_metric(MetricRecord(name="request_status", value=1, tags={"status": "failure"}))
            assert parse_result.error is not None
            return _error_response(parse_result.error, request_id=request_id)
        assert parsed is not None
        await event_logger.log_transformation(
            build_event(
                endpoint_id=endpoint_id,
                request_id=request_id,
                event_type="transformation",
                status="completed",
                data={"content_type": parsed.content_type},
            )
        )

        rule = TransformationRule(
            id=str(uuid4()),
            name="default-rule",
            target_agent_id=endpoint.config.target_agent_id,
            mappings=[FieldMapping(source="$", target="payload", transform=None)],
        )
        agent_input = transformer.transform(parsed, rule)
        governance_result = await governance.validate_execution(
            GovernanceContext(
                tenant_id=endpoint.tenant_id,
                endpoint_id=endpoint.id,
                agent_id=endpoint.config.target_agent_id,
                request_id=request_id,
                source_ip=ip,
                user_agent=user_agent,
            )
        )
        if not governance_result.valid:
            await monitoring.record_metric(MetricRecord(name="request_status", value=1, tags={"status": "failure"}))
            assert governance_result.error is not None
            return _error_response(governance_result.error, request_id=request_id)

        result = await execution.trigger(
            agent_input,
            options=ExecutionOptions(
                mode=endpoint.config.execution_mode,
                timeout_seconds=endpoint.config.timeout_seconds,
                retry_policy=endpoint.config.retry_policy,
            ),
        )
        status = "success" if result.status in {"accepted", "running", "completed"} else "failure"
        await monitoring.record_metric(MetricRecord(name="request_status", value=1, tags={"status": status}))
        await event_logger.log_execution(
            build_event(
                endpoint_id=endpoint.id,
                request_id=request_id,
                event_type="execution",
                status=result.status,
                data={"execution_id": result.execution_id},
                error=result.error,
            )
        )
        return JSONResponse(
            status_code=202,
            content={
                "execution_id": result.execution_id,
                "status": result.status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    @app.post("/endpoints")
    async def create_endpoint(payload: dict[str, Any]) -> JSONResponse:
        config_payload = payload.get("config", payload)
        config = EndpointConfig(
            name=str(config_payload["name"]),
            target_agent_id=str(config_payload["target_agent_id"]),
            auth_method=AuthMethod(
                type=str(config_payload["auth_method"]["type"]),
                token=config_payload["auth_method"].get("token"),
                secret=config_payload["auth_method"].get("secret"),
                algorithm=config_payload["auth_method"].get("algorithm"),
                username=config_payload["auth_method"].get("username"),
                password=config_payload["auth_method"].get("password"),
            ),
            execution_mode=str(config_payload.get("execution_mode", "async")),  # type: ignore[arg-type]
            timeout_seconds=config_payload.get("timeout_seconds"),
        )
        endpoint = await manager.create_endpoint(config)
        return JSONResponse(status_code=201, content={"id": endpoint.id, "url": endpoint.url, "config": asdict(endpoint.config)})

    @app.get("/endpoints")
    async def list_endpoints() -> JSONResponse:
        endpoints = await manager.list_endpoints()
        return JSONResponse(
            status_code=200,
            content={"items": [{"id": item.id, "url": item.url, "config": asdict(item.config)} for item in endpoints]},
        )

    @app.get("/endpoints/{endpoint_id}")
    async def get_endpoint(endpoint_id: str) -> JSONResponse:
        endpoint = await manager.get_endpoint(endpoint_id)
        if endpoint is None:
            return _error_response(ValidationError(code="ENDPOINT_NOT_FOUND", message="endpoint not found", status_code=404), request_id=str(uuid4()))
        return JSONResponse(status_code=200, content={"id": endpoint.id, "url": endpoint.url, "config": asdict(endpoint.config)})

    @app.put("/endpoints/{endpoint_id}")
    async def update_endpoint(endpoint_id: str, payload: dict[str, Any]) -> JSONResponse:
        config_payload = payload.get("config", payload)
        config = EndpointConfig(
            name=str(config_payload["name"]),
            target_agent_id=str(config_payload["target_agent_id"]),
            auth_method=AuthMethod(
                type=str(config_payload["auth_method"]["type"]),
                token=config_payload["auth_method"].get("token"),
                secret=config_payload["auth_method"].get("secret"),
                algorithm=config_payload["auth_method"].get("algorithm"),
                username=config_payload["auth_method"].get("username"),
                password=config_payload["auth_method"].get("password"),
            ),
            execution_mode=str(config_payload.get("execution_mode", "async")),  # type: ignore[arg-type]
            timeout_seconds=config_payload.get("timeout_seconds"),
            enabled=bool(config_payload.get("enabled", True)),
        )
        updated = await manager.update_endpoint(endpoint_id, config)
        return JSONResponse(status_code=200, content={"id": updated.id, "url": updated.url, "config": asdict(updated.config)})

    @app.delete("/endpoints/{endpoint_id}")
    async def delete_endpoint(endpoint_id: str) -> JSONResponse:
        await manager.delete_endpoint(endpoint_id)
        return JSONResponse(status_code=204, content=None)

    @app.get("/health")
    async def health() -> JSONResponse:
        health_status = await monitoring.get_health_status()
        return JSONResponse(
            status_code=200,
            content={
                "status": health_status.status,
                "checks": [{"name": c.name, "status": c.status, "message": c.message} for c in health_status.checks],
                "timestamp": health_status.timestamp.isoformat(),
            },
        )

    @app.get("/metrics")
    async def metrics() -> JSONResponse:
        stats = await monitoring.get_metrics(window="realtime")
        return JSONResponse(
            status_code=200,
            content={
                "request_count": stats.request_count,
                "success_rate": stats.success_rate,
                "failure_rate": stats.failure_rate,
                "avg_response_time": stats.avg_response_time,
                "p95_response_time": stats.p95_response_time,
                "p99_response_time": stats.p99_response_time,
            },
        )

    @app.get("/events")
    async def events(request_id: str | None = None) -> JSONResponse:
        items = await event_logger.query_events(EventFilter(tenant_id="default", request_id=request_id))
        return JSONResponse(
            status_code=200,
            content={"items": [asdict(item) for item in items]},
        )

    return app


def _error_response(error: ValidationError, *, request_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code or 400,
        content={
            "error": {
                "code": error.code,
                "message": error.message,
                "details": error.details,
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        },
    )
