# OwlClaw

> **Let existing business systems gain AI autonomy — without rewriting.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

---

## The Problem

Your enterprise has ERP, CRM, HR, and financial systems with years of business logic and data. They work — but they're **passive**: nothing happens unless a human acts.

AI Agent frameworks (LangChain, LangGraph, CrewAI) assume you build from scratch. **None of them are designed to make existing systems intelligent.**

## OwlClaw's Approach

OwlClaw gives your existing business systems AI-driven autonomy through a complete chain:

```
owlclaw scan → owlclaw migrate → SKILL.md → Declarative Binding → Governance → Agent Decision
```

1. **Scan** existing code (AST analysis) to discover capabilities
2. **Migrate** from OpenAPI/ORM to generate SKILL.md with bindings
3. **SKILL.md** describes business rules in Markdown — no AI knowledge required
4. **Declarative Binding** connects to HTTP/Queue/SQL endpoints automatically
5. **Governance** filters what the Agent can see and do (budget, rate limits, circuit breakers)
6. **Agent decides** via LLM function calling — what to do, when, and how

### Business developers write what they know

```markdown
---
name: inventory-monitor
description: >
  Monitor inventory levels and alert when stock falls below safety thresholds.
---

## Available Tools
- get_inventory_levels(warehouse_id): Get current stock levels
- get_safety_stock(product_id): Get safety stock threshold
- send_alert(recipient, message): Send alert notification

## Business Rules
- Alert when stock < 120% of safety level (allow replenishment time)
- Same product: max 1 alert per 24 hours
- Skip weekends and holidays
```

No AI knowledge needed. No prompt engineering. The Agent reads this and autonomously decides when to check inventory, which warehouses to monitor, and whether to alert.

## Quick Start

New here? Follow the 10-minute Lite Mode guide:
- [docs/QUICK_START.md](docs/QUICK_START.md)

```python
from owlclaw import OwlClaw

app = OwlClaw("my-business-agent")

# Mount business Skills
app.mount_skills("./capabilities/")

# Register capability handlers
@app.handler("inventory-monitor")
async def check_inventory(session) -> dict:
    return await inventory_service.check_levels(session)

# Configure Agent identity and behavior
app.configure(
    soul="docs/SOUL.md",
    identity="docs/IDENTITY.md",
    heartbeat_interval_minutes=30,
)

app.run()
```

## Core Philosophy

> **Don't control the Agent — empower it.**
> **Don't reinvent wheels — combine them.**

## What OwlClaw Builds vs Integrates

| Component | Source | Role |
|-----------|--------|------|
| **Agent Runtime** | OwlClaw (built) | Identity, memory, knowledge, function calling decisions |
| **Governance** | OwlClaw (built) | Capability visibility filtering, Ledger audit, budget control |
| **Business Onboarding** | OwlClaw (built) | scan → migrate → SKILL.md → Declarative Binding |
| **Trigger Layer** | OwlClaw (built) | Cron / Webhook / Queue / DB Change / API / Signal |
| Durable Execution | [Hatchet](https://hatchet.run/) (MIT) | Crash recovery, scheduling, cron |
| Knowledge Format | [Agent Skills](https://agentskills.io/) (Anthropic) | Standardized skill documents |
| LLM Access | [litellm](https://github.com/BerriAI/litellm) | Unified 100+ model access |
| Observability | [Langfuse](https://langfuse.com/) | LLM tracing and evaluation |

## OwlClaw and LangChain/LangGraph

OwlClaw is **not** a replacement for LangChain. They solve different problems:

| Dimension | OwlClaw | LangChain / LangGraph |
|-----------|---------|----------------------|
| Core strength | **When** to act, **whether** to act, governance | **How** to act (chains, graphs, RAG) |
| Business onboarding | First-class (SKILL.md + Binding) | Not primary |
| Trigger/scheduling | Built-in (6 trigger types) | Limited |
| Governance | Strong (visibility filter, Ledger, budget) | Usually app-specific |

**They combine**: register a LangChain chain as an OwlClaw capability, and the Agent autonomously decides when to invoke it.

```python
@app.handler(name="query_knowledge_base", knowledge="skills/kb-query/SKILL.md")
async def query_kb(question: str) -> str:
    return await rag_chain.ainvoke(question)
```

## Architecture Overview

```text
Business App Skills (SKILL.md) + Handlers/State + Declarative Bindings
                 |
                 v
         +----------------------+
         |   OwlClaw Runtime    |
         | identity + memory    |
         | governance + routing |
         +----------+-----------+
                    |
      +-------------+------------------+
      |                                |
      v                                v
  Integrations                     Trigger Layer
  (LLM / Hatchet / Langfuse)       (cron / webhook / queue / db / api / signal)
```

See [docs/ARCHITECTURE_ANALYSIS.md](docs/ARCHITECTURE_ANALYSIS.md) for the complete architecture.
See [docs/POSITIONING.md](docs/POSITIONING.md) for OwlClaw's market positioning.

## Key Features

### Skills Mount and Decorators

- **`app.mount_skills(path)`** — Scans for `SKILL.md` files following the [Agent Skills](https://agentskills.io/) spec. YAML frontmatter loaded at startup; full instructions loaded on demand.
- **`@app.handler(skill_name)`** — Registers a capability handler. Invoked when the Agent calls this capability via function calling.
- **`@app.state(name)`** — Registers a state provider the Agent can query via `query_state`.

### Built-in Tools (Agent Self-Management)

- `schedule_once` / `schedule_cron` / `cancel_schedule` — self-scheduling
- `remember` / `recall` — long-term memory operations
- `query_state` — read business state providers
- `log_decision` — governance/audit decision logs

Demo: [examples/agent_tools_demo.py](examples/agent_tools_demo.py) | API: [docs/AGENT_TOOLS_API.md](docs/AGENT_TOOLS_API.md)

### Hatchet Integration (Durable Execution)

OwlClaw uses [Hatchet](https://hatchet.run/) (MIT) for durable task execution, cron triggers, and self-scheduling. All Hatchet usage is isolated in `owlclaw.integrations.hatchet`.

Examples: [examples/hatchet_basic_task.py](examples/hatchet_basic_task.py), [examples/hatchet_cron_task.py](examples/hatchet_cron_task.py)

### LLM Integration

All LLM calls go through `owlclaw.integrations.llm`: config (YAML or code), model routing by `task_type`, fallback chain, optional Langfuse tracing, and mock mode for tests.

Config: [docs/llm/owlclaw.llm.example.yaml](docs/llm/owlclaw.llm.example.yaml) | Examples: [examples/integrations_llm/](examples/integrations_llm/)

### Memory System (STM + LTM)

Pluggable memory backends: `pgvector` (default), `qdrant`, `inmemory`.

```bash
owlclaw memory list --agent <agent_id> --tenant default
owlclaw memory stats --agent <agent_id> --tenant default
owlclaw memory prune --agent <agent_id> --before 2026-01-01T00:00:00+00:00
```

Docs: [docs/memory/configuration.md](docs/memory/configuration.md)

### Database CLI

```bash
owlclaw db init      # Create database, role, pgvector
owlclaw db migrate   # Run Alembic migrations
owlclaw db status    # Connection, version, migration status
owlclaw db check     # Health check
owlclaw db backup    # pg_dump backup
```

Full reference: [docs/cli/db-commands.md](docs/cli/db-commands.md)

## Installation

```bash
pip install owlclaw
# or
poetry add owlclaw
```

## Development

```bash
poetry install
poetry install --with observability   # optional: langfuse, opentelemetry

poetry run pytest                     # tests
poetry run ruff check .               # lint
poetry run mypy owlclaw/              # type check
```

## Links

- Architecture: [docs/ARCHITECTURE_ANALYSIS.md](docs/ARCHITECTURE_ANALYSIS.md)
- Positioning: [docs/POSITIONING.md](docs/POSITIONING.md)
- Examples: [examples/](examples/)
- Contributing: [CONTRIBUTING.md](CONTRIBUTING.md)
- Changelog: [CHANGELOG.md](CHANGELOG.md)
- License: [LICENSE](LICENSE)

## License

MIT — see [LICENSE](LICENSE).
