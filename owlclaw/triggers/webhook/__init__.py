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
    ParsedPayload,
    RetryPolicy,
    ValidationError,
    ValidationResult,
    WebhookEndpoint,
)

__all__ = [
    "AgentInput",
    "AuthMethod",
    "EndpointFilter",
    "EndpointConfig",
    "ExecutionOptions",
    "ExecutionResult",
    "ExecutionStatus",
    "ParsedPayload",
    "RetryPolicy",
    "ValidationError",
    "ValidationResult",
    "WebhookEndpoint",
    "WebhookEndpointManager",
]
