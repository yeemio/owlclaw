# API Trigger Protocol Notes

## Sync/Async semantics

- `response_mode=sync`: server waits for Agent result; success `200`, timeout `408`.
- `response_mode=async`: server returns `202` with `run_id` and `Location: /runs/{run_id}/result`.

## Language-agnostic constraints

- Contract payload uses JSON Schema / OpenAPI only.
- Protocol does not expose Python terms (Callable, decorator metadata, class names).
- SDK-level decorators are treated as syntax sugar over this protocol contract.

## Standard error codes

- `400` invalid request payload
- `401` unauthorized
- `429` governance rate limit
- `503` budget/service unavailable
- `408` sync timeout
