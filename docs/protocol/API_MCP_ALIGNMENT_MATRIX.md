# API / MCP Alignment Matrix

> Scope: capability and error-domain alignment between HTTP API and MCP surfaces.
> Last Updated: 2026-02-26

## 1. Capability Alignment

| Capability | HTTP API Surface | MCP Surface | Validation Evidence |
|---|---|---|---|
| runtime trigger | `POST /v1/agent/trigger` | `tools/call` (tool execution path) | `tests/contracts/api/test_openapi_contract_gate.py` + `tests/contracts/mcp/test_mcp_contract_regression.py` |
| execution status/query | status/ledger query endpoints (planned phase) | `resources/list` + `resources/read` | `tests/contracts/mcp/test_mcp_contract_regression.py` |
| server negotiation | API version policy (`VERSIONING.md`) | `initialize` negotiation path | `tests/contracts/mcp/test_mcp_contract_regression.py` |

## 2. Error-domain Alignment

| Canonical error | API behavior | MCP behavior | Retryable | Alert |
|---|---|---|---|---|
| `protocol.unsupported_version` | 400/426 + problem details | initialize/call error payload | false | warning |
| `governance.rate_limited` | 429 | call error | true | warning |
| `governance.budget_exceeded` | 403 | call error | false | critical |
| `internal.unexpected` | 500 | generic execution error | false | critical |

Source of truth:

- `docs/protocol/ERROR_MODEL.md`
- `docs/protocol/VERSIONING.md`

## 3. Review Requirement

Any PR that changes protocol schema, method names, error semantics, or contract tests must:

1. update this matrix if mapping changed,
2. include evidence links in PR description,
3. pass contract gate workflow.

