# mionyee-trading Example

A complete OwlClaw integration example for a trading-style workflow.

## What This Example Demonstrates

- Mounting multiple trading skills from `skills/`.
- Registering business handlers via `@app.handler`.
- Registering state providers via `@app.state`.
- Wiring identity context files (`docs/SOUL.md`, `docs/IDENTITY.md`).

## Quick Start

```bash
poetry run python examples/mionyee-trading/app.py
```

## Skills Included

- `entry-monitor`
- `morning-decision`
- `knowledge-feedback`

## Notes

- This example is designed for local demonstration and testing.
- It avoids external dependencies and keeps behavior deterministic.
