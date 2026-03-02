# Console Development Guide

## Frontend workflow

1. `cd owlclaw/web/frontend`
2. `npm install`
3. `npm run dev`

The Vite dev server runs on `:5173` and proxies `/api` to `http://localhost:8000`.

## Build frontend assets

1. `cd owlclaw/web/frontend`
2. `npm run build`

Artifacts are emitted to `owlclaw/web/static/`.

## Run local console host

Use the lightweight host command:

```bash
poetry run owlclaw start --host 127.0.0.1 --port 8000
```

Then open:

- `http://localhost:8000/console/`
- `http://localhost:8000/healthz`

## Open browser quickly

```bash
poetry run owlclaw console --port 8000
```

If static files are missing, the command prints installation guidance and expected path.

## Test commands

Backend-side console integration tests:

```bash
poetry run pytest tests/unit/web/test_mount.py -q
poetry run pytest tests/unit/cli/test_console_cmd.py -q
poetry run pytest tests/integration/test_console_mount.py tests/integration/test_console_integration.py -q
```

Frontend tests:

```bash
cd owlclaw/web/frontend
npm run test
```

