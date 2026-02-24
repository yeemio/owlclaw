# OwlHub Architecture

## Phase Overview

## Phase 1: Static Index

```
Repositories -> IndexBuilder -> index.json -> CLI search/install
```

## Phase 2: Static Discovery Site

```
index.json + statistics -> SiteGenerator -> static pages/rss/sitemap
```

## Phase 3: Service API

```
Clients -> FastAPI -> auth/review/statistics/blacklist/audit + index storage
```

## Migration Path

1. Keep `index.json` contract stable across phases.
2. Add API mode while preserving index-mode fallback in CLI.
3. Move persistence from local files to database in incremental steps.

## Key Design Decisions

- Backward compatibility first: index-mode remains supported.
- Security by default: authz + rate limit + CSRF + checksum validation.
- Operational visibility: `/health`, `/metrics`, structured logs.
