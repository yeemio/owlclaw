# Contributing to OwlClaw

## Development Setup

```bash
git clone https://github.com/yeemio/owlclaw.git
cd owlclaw
poetry install
pre-commit install
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

## Local CI Debug

```bash
act -W .github/workflows/lint.yml
act -W .github/workflows/test.yml
```

Use GitHub CLI for failed runs:

```bash
gh run list --limit 20
gh run view <run-id> --log-failed
```

## Commit Convention

```
<type>(<scope>): <description>

type: feat | fix | refactor | test | docs | chore
scope: agent | governance | triggers | integrations | cli | mcp | skills
```

Conventional commit types used by release automation:

- `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`
- Breaking changes must include footer:

```text
BREAKING CHANGE: <what changed and migration guidance>
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
