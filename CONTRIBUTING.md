# Contributing to OwlClaw

## Development Setup

```bash
git clone https://github.com/yeemio/owlclaw.git
cd owlclaw
poetry install
```

## Development Workflow

1. Read `docs/ARCHITECTURE_ANALYSIS.md` to understand the architecture
2. For new features, create a spec first (`.kiro/specs/{feature-name}/`)
3. Write tests alongside implementation
4. Run checks before committing:

```bash
poetry run ruff check .
poetry run mypy owlclaw/
poetry run pytest
```

## Commit Convention

```
<type>(<scope>): <description>

type: feat | fix | refactor | test | docs | chore
scope: agent | governance | triggers | integrations | cli | mcp | skills
```

## Spec Workflow

New features and major refactors require a three-layer spec:

```
.kiro/specs/{feature-name}/
├── requirements.md    # WHAT
├── design.md          # HOW
└── tasks.md           # WHO/WHEN
```

See `.kiro/SPEC_DOCUMENTATION_STANDARD.md` for details.
