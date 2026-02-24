# Signal Protocol Notes

## Shared schema across entry points

- CLI (`owlclaw agent ...`), HTTP API (`POST /admin/signal`), and MCP tools (`owlclaw_pause/resume/trigger/instruct`) all use the same `signal_request.schema.json` and `signal_response.schema.json`.
- Entry adapters only transform transport-level shape to this contract; core router/handlers consume contract objects directly.

## Error code mapping

- `400 bad_request`
- `401 unauthorized`
- `429 rate_limited`
- `503 service_unavailable`
- `408 timeout`

## Language-agnostic guarantee

- Contract includes no Python-only semantics (`Callable`, decorator metadata, class names).
- Python decorator APIs are syntax sugar over this protocol contract.
