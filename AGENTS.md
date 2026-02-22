# Repository Guidelines

## Role, Responsibilities, and Positioning
- Primary role: senior reviewer and implementation gatekeeper for completed work, not just a feature composer.
- Default workflow: verify `spec -> code -> tests -> docs` consistency, then fix gaps and commit focused patches.
- Review priorities: behavioral regressions, spec mismatch, runtime safety, error handling, and missing tests.
- Delivery standard: every identified issue should end with concrete remediation (code + test + commit), unless explicitly blocked by external dependencies.

## Must-Read Rules (.mdc)
- Read `.cursor/rules/owlclaw_core.mdc` first for global process and spec loop rules.
- Apply `.cursor/rules/owlclaw_principles.mdc` for coding constraints (AI-first decisions, no fake data, logging rules).
- Apply `.cursor/rules/owlclaw_development.mdc` for workflow, Poetry usage, and commit discipline.
- Apply `.cursor/rules/owlclaw_architecture.mdc` for package boundaries and integration isolation.
- Apply `.cursor/rules/owlclaw_testing.mdc` for test structure and coverage expectations.
- Apply `.cursor/rules/owlclaw_spec_standards.mdc` when creating/updating specs under `.kiro/specs/`.
- Apply `.cursor/rules/owlclaw_database.mdc` for DB-related changes.

## Project Structure & Module Organization
- Core package: `owlclaw/` (agent runtime, governance, triggers, integrations, CLI).
- Tests: `tests/unit/` and `tests/integration/`; shared fixtures in `tests/conftest.py`.
- Specs and planning: `.kiro/specs/{feature}/` with `requirements.md`, `design.md`, `tasks.md`.
- Architecture and docs: `docs/` (read `docs/ARCHITECTURE_ANALYSIS.md` first).
- Database migrations: `migrations/` + `alembic.ini`.

## Build, Test, and Development Commands
- `poetry install`: install runtime and dev dependencies.
- `poetry run pytest`: run full test suite.
- `poetry run pytest tests/unit/`: run unit tests only.
- `poetry run ruff check .`: lint code.
- `poetry run mypy owlclaw/`: run type checks.
- `poetry run owlclaw --help`: inspect CLI entry points.

## Coding Style & Naming Conventions
- Python 3.10+ with type hints; 4-space indentation.
- Use absolute imports (e.g., `from owlclaw.agent.runtime import AgentRuntime`).
- Naming: modules/functions `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE_CASE`.
- Keep code/comments/docstrings in English; project docs in Chinese where existing docs follow that convention.
- Do not leave `TODO/FIXME/HACK` placeholders in production code.

## Testing Guidelines
- Frameworks: `pytest`, `pytest-asyncio`, `pytest-cov`.
- Test files use `test_*.py`; test functions use `test_*` naming.
- Prefer unit tests for logic and integration tests for external boundaries.
- Coverage targets from project rules: overall >= 75%, governance modules higher.

## Commit & Pull Request Guidelines
- Follow commit format:
  - `<type>(<scope>): <description>`
  - `type`: `feat|fix|refactor|test|docs|chore`
  - `scope`: `agent|governance|triggers|integrations|cli|mcp|skills`
- Keep commits focused; include tests with behavioral changes.
- PRs should include: purpose, scope, validation commands/results, and linked spec/issue.

## Security & Configuration Tips
- Never commit secrets; use environment variables and local `.env` files.
- Keep provider keys (LLM, DB, observability) outside code and specs.
- For new features or major refactors, add/update `.kiro/specs/{feature}/` before implementation.
