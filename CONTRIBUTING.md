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

## Pull Request Guidelines

Every PR should include:

1. Purpose and scope (what changed and why)
2. Spec/task linkage (`.kiro/specs/{feature}/tasks.md` item)
3. Validation commands and results (`pytest`, `ruff`, `mypy`)
4. Risk notes and rollback hints if behavior changed

Prefer focused PRs over mixed refactor+feature bundles.

## Code Style

- Python 3.10+ with type hints
- Absolute imports (`from owlclaw...`)
- Keep production code free of `TODO/FIXME/HACK`
- Run formatting/lint checks before pushing

## Spec Workflow

New features and major refactors require a three-layer spec:

```
.kiro/specs/{feature-name}/
├── requirements.md    # WHAT
├── design.md          # HOW
└── tasks.md           # WHO/WHEN
```

See `.kiro/SPEC_DOCUMENTATION_STANDARD.md` for details.
