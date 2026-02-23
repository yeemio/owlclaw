# Memory Configuration Guide

`owlclaw.yaml` memory section:

```yaml
memory:
  vector_backend: pgvector          # pgvector | qdrant | inmemory
  embedding_model: text-embedding-3-small
  embedding_dimensions: 1536
  tfidf_dimensions: 256
  enable_tfidf_fallback: true
  enable_keyword_fallback: true
  enable_file_fallback: true
  file_fallback_path: MEMORY.md

  snapshot_max_tokens: 500
  time_decay_half_life_hours: 168
  max_entries: 10000
  retention_days: 365
  compaction_threshold: 50

  qdrant_url: http://localhost:6333
  qdrant_collection_name: owlclaw_memory
```

Key notes:

- `vector_backend` controls storage engine selection.
- `embedding_dimensions` must match vector backend schema/collection dimensions.
- `enable_tfidf_fallback` handles embedding provider outage.
- `enable_keyword_fallback` handles vector query outage.
- `enable_file_fallback` writes to `MEMORY.md` when primary store write fails.
- `compaction_threshold` controls when same-tag memories are merged.
