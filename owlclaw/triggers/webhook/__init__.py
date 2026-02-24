"""Webhook trigger core types and contracts."""

from owlclaw.triggers.webhook.types import (
    AgentInput,
    AuthMethod,
    EndpointConfig,
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
    "EndpointConfig",
    "ExecutionOptions",
    "ExecutionResult",
    "ExecutionStatus",
    "ParsedPayload",
    "RetryPolicy",
    "ValidationError",
    "ValidationResult",
    "WebhookEndpoint",
]
