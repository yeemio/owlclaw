# mionyee-trading Example

A complete OwlClaw integration example for a trading-style workflow.

## What This Example Demonstrates

- Mounting multiple trading skills from `skills/`.
- Registering business handlers via `@app.handler`.
- Registering state providers via `@app.state`.
- Wiring identity context files (`docs/SOUL.md`, `docs/IDENTITY.md`).
- Governance overlay glue via `ai/client.py` + `owlclaw.yaml`.

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
- `ai/client.py` shows the mionyee-side replacement from direct `litellm.acompletion`
  to `GovernanceProxy.acompletion`.
