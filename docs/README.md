# OwlClaw Documentation

## Architecture & Design

| Document | Description |
|----------|-------------|
| [ARCHITECTURE_ANALYSIS.md](ARCHITECTURE_ANALYSIS.md) | Full system architecture — modules, data flow, design decisions |
| [DATABASE_ARCHITECTURE.md](DATABASE_ARCHITECTURE.md) | Database design — schema, migrations, multi-tenant, pgvector |
| [DEEP_ANALYSIS_AND_DISCUSSION.md](DEEP_ANALYSIS_AND_DISCUSSION.md) | Design trade-offs and architectural discussions |

## Development

| Document | Description |
|----------|-------------|
| [DEVELOPMENT.md](DEVELOPMENT.md) | Local development setup — Docker, env vars, first run |
| [TESTING.md](TESTING.md) | Testing guide — unit/integration/e2e, coverage targets |
| [CONFIGURATION.md](CONFIGURATION.md) | `owlclaw.yaml` config reference |
| [WORKTREE_GUIDE.md](WORKTREE_GUIDE.md) | Multi-worktree parallel development workflow |

## Agent & Skills

| Document | Description |
|----------|-------------|
| [AGENT_RUNTIME_API.md](AGENT_RUNTIME_API.md) | AgentRuntime API reference |
| [AGENT_RUNTIME_USAGE.md](AGENT_RUNTIME_USAGE.md) | AgentRuntime usage guide and examples |
| [AGENT_TOOLS_API.md](AGENT_TOOLS_API.md) | Built-in tools reference |
| [SKILL_WRITING_GUIDE.md](SKILL_WRITING_GUIDE.md) | How to write SKILL.md files |

## Integrations

| Document | Description |
|----------|-------------|
| [CRON_TRIGGERS.md](CRON_TRIGGERS.md) | Cron trigger setup and usage |
| [HATCHET_WITHOUT_DOCKER.md](HATCHET_WITHOUT_DOCKER.md) | Running Hatchet in non-Docker environments |
| [MCP_SERVER.md](MCP_SERVER.md) | owlclaw-mcp server setup |
| [GOVERNANCE_GUIDE.md](GOVERNANCE_GUIDE.md) | Governance layer — visibility, ledger, routing |
| [SECURITY_CONFIGURATION.md](SECURITY_CONFIGURATION.md) | Security model — prompt injection, data masking |
| [DECLARATIVE_BINDING_WORKFLOWS.md](DECLARATIVE_BINDING_WORKFLOWS.md) | Declarative binding system for tools |

## CLI

| Document | Description |
|----------|-------------|
| [cli/](cli/) | CLI command reference |

## Release & Deployment

| Document | Description |
|----------|-------------|
| [DEPLOYMENT.md](DEPLOYMENT.md) | Production deployment guide |
| [RELEASE_RUNBOOK.md](RELEASE_RUNBOOK.md) | PyPI + GitHub release runbook |
| [CI_SETUP.md](CI_SETUP.md) | GitHub Actions CI configuration |

## OwlHub

| Document | Description |
|----------|-------------|
| [owlhub/](owlhub/) | OwlHub Skills registry documentation |

## Decision Proposals

| Document | Description |
|----------|-------------|
| [OWLHUB_CLI_NAMING_DECISION_PROPOSAL.md](OWLHUB_CLI_NAMING_DECISION_PROPOSAL.md) | CLI naming conventions decision |
| [OWLHUB_PHASE3_DB_DECISION_PROPOSAL.md](OWLHUB_PHASE3_DB_DECISION_PROPOSAL.md) | OwlHub Phase 3 database backend decision |
| [ZERO_CODE_FASTPATH_DECISION_PROPOSAL.md](ZERO_CODE_FASTPATH_DECISION_PROPOSAL.md) | Zero-code fast path decision |
