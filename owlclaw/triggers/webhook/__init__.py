"""Webhook trigger core types and contracts."""

from owlclaw.triggers.webhook.configuration import WebhookConfigManager, dump_config
from owlclaw.triggers.webhook.event_logger import EventLogger, build_event
from owlclaw.triggers.webhook.execution import ExecutionTrigger
from owlclaw.triggers.webhook.governance import GovernanceClient
from owlclaw.triggers.webhook.http.app import HttpGatewayConfig, create_webhook_app
from owlclaw.triggers.webhook.manager import WebhookEndpointManager
from owlclaw.triggers.webhook.monitoring import MonitoringService
from owlclaw.triggers.webhook.transformer import PayloadTransformer
from owlclaw.triggers.webhook.types import (
    AgentInput,
    AlertRecord,
    AuthMethod,
    EndpointConfig,
    EndpointFilter,
    EventFilter,
    EventType,
    ExecutionOptions,
    ExecutionResult,
    ExecutionStatus,
    FieldMapping,
    GovernanceContext,
    GovernanceDecision,
    HealthCheckResult,
    HealthStatusSnapshot,
    HttpRequest,
    MetricRecord,
    MetricStats,
    ParsedPayload,
    RetryPolicy,
    TransformationRule,
    ValidationError,
    ValidationResult,
    WebhookEndpoint,
    WebhookEventRecord,
    WebhookGlobalConfig,
    WebhookSystemConfig,
)
from owlclaw.triggers.webhook.validator import RequestValidator

__all__ = [
    "AgentInput",
    "AlertRecord",
    "AuthMethod",
    "EndpointFilter",
    "EndpointConfig",
    "EventFilter",
    "EventLogger",
    "EventType",
    "ExecutionOptions",
    "ExecutionResult",
    "ExecutionStatus",
    "ExecutionTrigger",
    "FieldMapping",
    "GovernanceClient",
    "GovernanceContext",
    "GovernanceDecision",
    "HealthCheckResult",
    "HealthStatusSnapshot",
    "HttpGatewayConfig",
    "HttpRequest",
    "MetricRecord",
    "MetricStats",
    "MonitoringService",
    "PayloadTransformer",
    "ParsedPayload",
    "RequestValidator",
    "RetryPolicy",
    "TransformationRule",
    "ValidationError",
    "ValidationResult",
    "WebhookEventRecord",
    "WebhookEndpoint",
    "WebhookEndpointManager",
    "WebhookConfigManager",
    "WebhookGlobalConfig",
    "WebhookSystemConfig",
    "build_event",
    "create_webhook_app",
    "dump_config",
]
