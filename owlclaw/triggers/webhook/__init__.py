"""Webhook trigger core types and contracts."""

from owlclaw.triggers.webhook.manager import WebhookEndpointManager
from owlclaw.triggers.webhook.types import (
    AgentInput,
    AuthMethod,
    EndpointConfig,
    EndpointFilter,
    ExecutionOptions,
    ExecutionResult,
    ExecutionStatus,
    HttpRequest,
    ParsedPayload,
    RetryPolicy,
    ValidationError,
    ValidationResult,
    WebhookEndpoint,
)
from owlclaw.triggers.webhook.validator import RequestValidator

__all__ = [
    "AgentInput",
    "AuthMethod",
    "EndpointFilter",
    "EndpointConfig",
    "ExecutionOptions",
    "ExecutionResult",
    "ExecutionStatus",
    "HttpRequest",
    "ParsedPayload",
    "RequestValidator",
    "RetryPolicy",
    "ValidationError",
    "ValidationResult",
    "WebhookEndpoint",
    "WebhookEndpointManager",
]
