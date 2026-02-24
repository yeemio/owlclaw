# Webhook API Guide

## Overview

Webhook gateway is exposed via FastAPI and provides:
- `POST /webhooks/{endpoint_id}`
- `POST /endpoints`
- `GET /endpoints`
- `GET /endpoints/{endpoint_id}`
- `PUT /endpoints/{endpoint_id}`
- `DELETE /endpoints/{endpoint_id}`
- `GET /health`
- `GET /metrics`
- `GET /events`

OpenAPI is available at:
- `/openapi.json`
- `/docs`

## Authentication

Endpoint-level auth is configured by `auth_method`:
- `bearer`
- `hmac`
- `basic`

Example endpoint creation payload:

```json
{
  "name": "orders",
  "target_agent_id": "agent-1",
  "auth_method": {"type": "bearer", "token": "token-abc"},
  "execution_mode": "async",
  "timeout_seconds": 15,
  "retry_policy": {
    "max_attempts": 3,
    "initial_delay_ms": 200,
    "max_delay_ms": 2000,
    "backoff_multiplier": 2.0
  }
}
```

## Transformation Rule Defaults

Current gateway uses default mapping:
- source: `$`
- target: `payload`

This passes parsed payload to Agent runtime input parameters.

## Request / Response Format

Success response:

```json
{
  "execution_id": "exec-123",
  "status": "accepted",
  "timestamp": "2026-02-24T12:00:00+00:00"
}
```

Error response:

```json
{
  "error": {
    "code": "INVALID_TOKEN",
    "message": "invalid bearer token",
    "details": null,
    "request_id": "req-123",
    "timestamp": "2026-02-24T12:00:01+00:00"
  }
}
```
