# OwlClaw

> **Agent base for business applications** — let mature systems gain AI autonomy without rewriting.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

---

## What is OwlClaw?

OwlClaw is an **agent infrastructure layer** that lets existing business applications gain AI-driven autonomy — without rewriting their core logic.

Instead of building yet another agent framework from scratch, OwlClaw **combines mature open-source capabilities**:

| Component | Source | Role |
|-----------|--------|------|
| Durable Execution | [Hatchet](https://hatchet.run/) (MIT) | Crash recovery, scheduling, cron |
| Knowledge Format | [Agent Skills](https://agentskills.io/) (Anthropic) | Standardized skill documents |
| LLM Access | [litellm](https://github.com/BerriAI/litellm) | Unified 100+ model access |
| Observability | [Langfuse](https://langfuse.com/) | LLM tracing and evaluation |

**OwlClaw builds what nobody else does**: business application onboarding layer, governance (capability visibility filtering), and an Agent runtime with identity, memory, and knowledge.

## Core Philosophy

> **Don't control the Agent — empower it.**
> **Don't reinvent wheels — combine them.**

## Quick Start

```python
from owlclaw import OwlClaw

app = OwlClaw("mionyee-trading")

# Mount business application's Skills (Agent Skills spec)
app.mount_skills("./capabilities/")

# Register capability handlers
@app.handler("entry-monitor")
async def check_entry(session) -> dict:
    return await monitor_service.check_opportunities(session)

# Configure Agent identity
app.configure(
    soul="docs/SOUL.md",
    identity="docs/IDENTITY.md",
    heartbeat_interval_minutes=30,
)

app.run()
```

## Installation

```bash
pip install owlclaw
# or
poetry add owlclaw
```

## Architecture

See [docs/ARCHITECTURE_ANALYSIS.md](docs/ARCHITECTURE_ANALYSIS.md) for the complete architecture design.

## Development

```bash
# Install dependencies
poetry install

# Run tests
poetry run pytest

# Lint
poetry run ruff check .

# Type check
poetry run mypy owlclaw/
```

## License

MIT — see [LICENSE](LICENSE).
