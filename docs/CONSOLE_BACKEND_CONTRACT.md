# Console Backend Contract (Round 2)

## Base

- REST base path: `/api/v1`
- Auth: optional bearer token from `OWLCLAW_CONSOLE_TOKEN`
- Error shape (all 4xx/5xx):

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Agent not found",
    "details": {}
  }
}
```

## REST Endpoints

### Overview

- `GET /overview`
- Response: `OverviewMetrics`

### Governance

- `GET /governance/budget?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&granularity=day|week|month`
- `GET /governance/circuit-breakers`
- `GET /governance/visibility-matrix?agent_id=<optional>`

### Agents

- `GET /agents` -> `{ "items": [...] }`
- `GET /agents/{agent_id}` -> agent detail

### Capabilities

- `GET /capabilities?category=handler|skill|binding`
- Response: `{ "items": [...] }`
- `GET /capabilities/{name}/schema`

### Triggers

- `GET /triggers` -> `{ "items": [...] }`
- `GET /triggers/{id}/history?limit=<int>&offset=<int>`
- Response: paginated `{ "items": [...], "total": <int>, "offset": <int>, "limit": <int> }`

### Ledger

- `GET /ledger` query params:
  - `agent_id`
  - `capability_name`
  - `status`
  - `start_date`
  - `end_date`
  - `min_cost`
  - `max_cost`
  - `limit`
  - `offset`
  - `order_by=created_at_desc|created_at_asc|cost_desc|cost_asc`
- Response: paginated `{ "items": [...], "total": <int>, "offset": <int>, "limit": <int> }`
- `GET /ledger/{record_id}`

### Settings

- `GET /settings`

## WebSocket Contract

- Endpoint: `GET /api/v1/ws` (upgrade)
- Initial and periodic message types:
  - `overview`
  - `triggers`
  - `ledger`

Example:

```json
{
  "type": "overview",
  "payload": {
    "total_cost_today": "2.5",
    "total_executions_today": 10,
    "success_rate_today": 0.9,
    "active_agents": 2
  }
}
```

