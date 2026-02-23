# Memory Lifecycle Best Practices

## Capacity and retention

- Set `max_entries` per agent based on expected daily memory writes.
- Use `retention_days` to cap stale, low-value memory accumulation.
- Keep `time_decay_half_life_hours` aligned with business cadence.

## Compaction policy

- Start with `compaction_threshold=50`.
- Lower threshold for high-frequency repetitive domains.
- Keep summary entries tagged with `compacted` for auditability.

## Security and channels

- Keep security classification enabled (`internal/confidential/restricted`).
- Use channel-aware output filtering for MCP/Langfuse consumers.
- Never disable masking for external channels.

## Degradation readiness

- Enable TF-IDF fallback for embedding outages.
- Enable keyword fallback for vector search outages.
- Enable file fallback (`MEMORY.md`) for temporary store unavailability.

## Operations

- Run scheduled maintenance daily (archive + cleanup).
- Track memory counts and tag distributions with `owlclaw memory stats`.
- Test backend migration in staging before production rollout.
