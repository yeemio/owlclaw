from __future__ import annotations

from datetime import datetime, timezone

from owlclaw.triggers.webhook import (
    AgentInput,
    AuthMethod,
    EndpointConfig,
    ExecutionOptions,
    ExecutionResult,
    ParsedPayload,
    RetryPolicy,
    ValidationError,
    ValidationResult,
    WebhookEndpoint,
)


def test_webhook_type_models_roundtrip() -> None:
    auth = AuthMethod(type="bearer", token="token-123")
    retry = RetryPolicy(max_attempts=5, initial_delay_ms=500)
    endpoint_config = EndpointConfig(
        name="orders",
        target_agent_id="agent-1",
        auth_method=auth,
        retry_policy=retry,
    )
    endpoint = WebhookEndpoint(
        id="ep-1",
        url="/webhooks/ep-1",
        auth_token="secret",
        config=endpoint_config,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    parsed = ParsedPayload(content_type="application/json", data={"order_id": "o-1"})
    agent_input = AgentInput(agent_id="agent-1", parameters={"order_id": "o-1"})
    options = ExecutionOptions(mode="async", idempotency_key="idempo-1", retry_policy=retry)
    result = ExecutionResult(
        execution_id="run-1",
        status="accepted",
        started_at=datetime.now(timezone.utc),
    )
    error = ValidationError(code="INVALID_TOKEN", message="token missing")
    validation = ValidationResult(valid=False, error=error)

    assert endpoint.config.auth_method.token == "token-123"
    assert parsed.data["order_id"] == "o-1"
    assert agent_input.parameters["order_id"] == "o-1"
    assert options.retry_policy is retry
    assert result.status == "accepted"
    assert validation.error is error
