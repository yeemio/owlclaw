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

### Skills mount and decorators

- **`app.mount_skills(path)`** — Scans the given directory for `SKILL.md` files (following the [Agent Skills](https://agentskills.io/) spec). Each file's YAML frontmatter (name, description, optional `owlclaw` extensions) is loaded at startup; full instruction text is loaded on demand when building Agent prompts. You must call `mount_skills()` before using `@app.handler` or `@app.state`.

- **`@app.handler(skill_name)`** — Registers a capability handler for the Skill with the given name. The handler is invoked when the Agent calls this capability (e.g. via function calling). Handlers can be sync or async; they receive a session context and return a result (e.g. a dict).

- **`@app.state(name)`** — Registers a state provider. The Agent can query it (e.g. via a built-in `query_state` tool) to get current business state. The provider must return a dict. It can be sync or async.

See [examples/basic_usage.py](examples/basic_usage.py) and [examples/capabilities/](examples/capabilities/) for a minimal runnable example and sample SKILL.md files.

### Hatchet integration (durable execution and cron)

OwlClaw uses [Hatchet](https://hatchet.run/) (MIT) for durable task execution, cron triggers, and self-scheduling. All Hatchet usage is isolated in `owlclaw.integrations.hatchet`.

```python
from owlclaw.integrations.hatchet import HatchetClient, HatchetConfig

config = HatchetConfig.from_yaml("owlclaw.yaml")  # or HatchetConfig(server_url=..., api_token=...)
client = HatchetClient(config)
client.connect()

@client.task(name="agent-run", retries=3)
async def agent_run(ctx):
    return {"status": "ok"}

await client.schedule_task("agent-run", delay_seconds=300)
client.start_worker()  # blocking
```

- **Config**: `HatchetConfig.from_yaml("owlclaw.yaml")` or env vars (`${HATCHET_API_TOKEN}`). See [deploy/owlclaw.yaml.example](deploy/owlclaw.yaml.example).
- **Deploy**: Development with Hatchet Lite — `docker compose -f deploy/docker-compose.lite.yml up -d`. Production — [deploy/docker-compose.prod.yml](deploy/docker-compose.prod.yml).
- **Cron**: Use `@client.task(name="...", cron="*/5 * * * *")` for periodic runs (5 fields: min hour day month dow).

Examples: [examples/hatchet_basic_task.py](examples/hatchet_basic_task.py), [examples/hatchet_cron_task.py](examples/hatchet_cron_task.py), [examples/hatchet_self_schedule.py](examples/hatchet_self_schedule.py).

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
