# Memory Backend Selection Guide

## pgvector

Use when:

- You already run PostgreSQL for OwlClaw.
- You want simpler deployment and operations.
- Memory scale is moderate (single-cluster friendly).

Pros:

- Single data stack.
- Strong transactional consistency for metadata.
- Lower operational overhead.

## Qdrant

Use when:

- Memory volume/query QPS is high.
- You need dedicated vector infrastructure.
- You want independent vector scaling and tuning.

Pros:

- Vector-focused indexing and retrieval.
- Better isolation between OLTP and vector workloads.

Tradeoff:

- Extra component to deploy and monitor.

## InMemory

Use when:

- Local development, CI tests, or mock mode.
- You do not require persistence.

Pros:

- Zero infrastructure dependencies.
- Fast iteration in tests.

Tradeoff:

- Data is process-local and ephemeral.

## Migration

Use:

```bash
owlclaw memory migrate-backend \
  --agent <agent_id> \
  --source-backend pgvector \
  --target-backend qdrant
```

Migrate agent-by-agent (and tenant-by-tenant) to control risk and rollback scope.
