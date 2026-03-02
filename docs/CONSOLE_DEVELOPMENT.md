# Console Development Guide

## Overview

The Console is a React SPA under `owlclaw/web/frontend/` and is built into
`owlclaw/web/static/`. The backend API is served from `owlclaw/web/api/`.

## Local Development

1. Start backend service on `:8000` (for `/api/v1`).
2. Start frontend dev server:

```bash
cd owlclaw/web/frontend
npm install
npm run dev
```

The Vite dev proxy forwards `/api/*` to `http://localhost:8000`.

## Build

Build static assets into Python package path:

```bash
cd owlclaw/web/frontend
npm run build
```

Or from repo root:

```bash
make build-console
```

## Test

Frontend unit tests:

```bash
cd owlclaw/web/frontend
npm run test
```

Backend/integration tests:

```bash
poetry run pytest tests/unit/web/test_mount.py tests/integration/test_console_mount.py tests/integration/test_console_integration.py
```

## Runtime Integration

- `owlclaw.web.mount.mount_console(app)` mounts:
  - `/api/v1/*` console backend API
  - `/console/*` static SPA with fallback to `index.html`
  - `/` redirect to `/console/`
- If `owlclaw/web/static/index.html` is missing, mount is skipped gracefully.

