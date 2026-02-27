# OwlClaw Unified Error Model

> Scope: Machine-readable error semantics shared by HTTP API and MCP.
> Status: Active baseline.
> Last Updated: 2026-02-26

---

## 1. Canonical Error Object

All protocol errors must expose these fields:

- `code`: stable error identifier (`domain.reason`).
- `category`: one of `validation|compatibility|governance|auth|runtime|dependency|internal`.
- `retryable`: boolean retry hint for clients.
- `incident_id`: trace-correlated identifier for support.

Recommended extension fields:

- `message`: human-readable summary.
- `details`: structured machine-readable metadata.
- `retry_after`: seconds (when retryable with backoff).

---

## 2. API Representation

API uses Problem Details compatible payload and includes canonical fields:

```json
{
  "type": "https://owlclaw.dev/problems/protocol-version",
  "title": "Unsupported protocol version",
  "status": 400,
  "code": "protocol.unsupported_version",
  "category": "compatibility",
  "retryable": false,
  "incident_id": "inc_20260226_001",
  "details": {
    "supported_versions": ["v1"]
  }
}
```

---

## 3. MCP Representation

MCP error payload must carry equivalent semantics:

```json
{
  "error": {
    "code": "protocol.unsupported_version",
    "message": "Unsupported protocol version",
    "category": "compatibility",
    "retryable": false,
    "incident_id": "inc_20260226_001",
    "details": {
      "supported_versions": ["2025-06", "2025-03"]
    }
  }
}
```

---

## 4. API/MCP Mapping Matrix

| Canonical code | API status | MCP surface | Category | Retryable | Alert level |
|---|---:|---|---|---|---|
| `protocol.unsupported_version` | 400/426 | initialize/call error | compatibility | false | warning |
| `protocol.version_conflict` | 400 | initialize/call error | validation | false | warning |
| `governance.rate_limited` | 429 | tools/call error | governance | true | warning |
| `governance.budget_exceeded` | 403 | tools/call error | governance | false | critical |
| `auth.unauthorized` | 401 | initialize error | auth | false | critical |
| `auth.forbidden` | 403 | call/read error | auth | false | critical |
| `runtime.timeout` | 504 | call/read error | runtime | true | warning |
| `dependency.unavailable` | 503 | call/read error | dependency | true | warning |
| `internal.unexpected` | 500 | generic error | internal | false | critical |

---

## 5. Retry Semantics

Client retry policy should follow `retryable` first, then code-specific guidance:

- If `retryable=false`, do not auto-retry.
- If `retryable=true` and `retry_after` provided, use that delay.
- If `retryable=true` and no `retry_after`, apply capped exponential backoff.

Non-retryable classes by default:

- auth failures
- compatibility violations
- budget exceeded

Retryable classes by default:

- transient rate limit
- runtime timeout
- dependency unavailable

---

## 6. Alerting Semantics

Suggested alert policy:

- `critical`: page on-call immediately.
- `warning`: aggregate and alert on threshold breach.

Recommended initial thresholds:

- `critical` any single event in production.
- `warning` > 5 events in 5 minutes per client.

---

## 7. Consistency Requirements

- API and MCP must share the same canonical `code/category/retryable`.
- Any new canonical code requires:
  - mapping row update in this document,
  - contract tests update,
  - release note entry.

