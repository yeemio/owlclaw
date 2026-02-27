# OwlClaw Protocol Versioning

> Scope: Unified versioning policy for HTTP API and MCP surfaces.
> Status: Active baseline (Phase 1 warning gate).
> Last Updated: 2026-02-26

---

## 1. Goals

- Keep API and MCP version semantics consistent.
- Make version choice deterministic and machine-checkable.
- Provide explicit downgrade and upgrade paths for clients.

---

## 2. Version Model

- API version format: `v{major}` (for example `v1`, `v2`).
- MCP protocol version format: `YYYY-MM` (for example `2025-06`).
- Compatibility level is evaluated by contract diff:
  - `compatible`
  - `additive`
  - `breaking`

---

## 3. Selection Priority

Version decision priority is unified across API and MCP:

1. Client-requested version (explicit request field/header/path).
2. Server default version (configured baseline).
3. Negotiated downgrade (highest mutually supported lower version).

If all three fail, the request is rejected with a version negotiation error.

---

## 4. API Rules

### 4.1 Client-requested version

Clients can request API version by one of the allowed mechanisms:

- Path: `/api/v1/...`
- Header: `X-OwlClaw-Api-Version: v1`

If both are provided and conflict, server returns `protocol.version_conflict`.

### 4.2 Default version

When no explicit version is provided, server uses
`OWLCLAW_PROTOCOL_DEFAULT_API_VERSION` (default: `v1`).

### 4.3 Negotiated downgrade

If requested version is not supported, server may downgrade only when:

- client sets `allow_downgrade=true`, and
- downgraded version is explicitly listed in response metadata.

Otherwise, server returns `protocol.unsupported_version`.

---

## 5. MCP Rules

### 5.1 Initialize negotiation

During MCP `initialize`, client submits supported protocol versions.
Server chooses highest compatible version from intersection:

- client supported versions
- server supported versions (`OWLCLAW_PROTOCOL_MCP_VERSIONS`)

### 5.2 Negotiation failure

If intersection is empty, server must return structured error:

- `code`: `protocol.unsupported_version`
- `category`: `compatibility`
- `retryable`: `false`
- `incident_id`: generated trace identifier
- `details.supported_versions`: server version list

---

## 6. Negotiation Failure Response

### 6.1 HTTP API

Status: `400` (invalid version request) or `426` (upgrade required, if policy enabled).

Problem details fields:

- `type`: `https://owlclaw.dev/problems/protocol-version`
- `title`: `Unsupported protocol version`
- `status`: HTTP status code
- `code`: `protocol.unsupported_version`
- `category`: `compatibility`
- `retryable`: `false`
- `incident_id`: trace-correlated identifier

### 6.2 MCP

MCP error payload must contain the same semantic fields:

- `code`
- `category`
- `retryable`
- `incident_id`
- `supported_versions`

---

## 7. Upgrade / Downgrade Examples

### 7.1 API upgrade (v1 -> v2)

1. Client sends dual-read traffic to `v1` and `v2` in canary.
2. Server returns stable parity metrics for 7 days.
3. Client switches primary to `v2`, keeps `v1` fallback for 1 release window.

### 7.2 API downgrade (v2 -> v1)

Trigger conditions:

- `protocol_error_rate` exceeds rollback threshold.
- contract gate detects unplanned breaking behavior.

Action:

1. Switch traffic back to `v1`.
2. Emit governance event with `incident_id`.
3. Open migration follow-up before re-enabling `v2`.

### 7.3 MCP downgrade (2025-06 -> 2025-03)

1. Client initialize with `["2025-06", "2025-03"]`.
2. Server does not support `2025-06`, negotiates `2025-03`.
3. Response includes:
   - `selected_version: "2025-03"`
   - `downgraded_from: "2025-06"`
   - migration hint URL.

---

## 8. Change Governance Linkage

- Version policy must be enforced by protocol governance gate.
- Any `breaking` contract diff requires:
  - migration plan,
  - deprecation window,
  - rollback procedure.

See:

- `docs/protocol/COMPATIBILITY_POLICY.md`
- `docs/protocol/GOVERNANCE_GATE_POLICY.md`

