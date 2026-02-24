"""Webhook trigger core types and contracts."""

from owlclaw.triggers.webhook.execution import ExecutionTrigger
from owlclaw.triggers.webhook.governance import GovernanceClient
from owlclaw.triggers.webhook.manager import WebhookEndpointManager
from owlclaw.triggers.webhook.transformer import PayloadTransformer
from owlclaw.triggers.webhook.types import (
    AgentInput,
    AuthMethod,
    EndpointConfig,
    EndpointFilter,
    ExecutionOptions,
    ExecutionResult,
    ExecutionStatus,
    FieldMapping,
    GovernanceContext,
    GovernanceDecision,
    HttpRequest,
    ParsedPayload,
    RetryPolicy,
    TransformationRule,
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
    "ExecutionTrigger",
    "FieldMapping",
    "GovernanceClient",
    "GovernanceContext",
    "GovernanceDecision",
    "HttpRequest",
    "PayloadTransformer",
    "ParsedPayload",
    "RequestValidator",
    "RetryPolicy",
    "TransformationRule",
    "ValidationError",
    "ValidationResult",
    "WebhookEndpoint",
    "WebhookEndpointManager",
]
