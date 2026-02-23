# Repository Guidelines

## Role, Responsibilities, and Positioning
- Primary role: senior reviewer and implementation gatekeeper for completed work, not just a feature composer.
- Default workflow: verify `spec -> code -> tests -> docs` consistency, then fix gaps and commit focused patches.
- Review priorities: behavioral regressions, spec mismatch, runtime safety, error handling, and missing tests.
- Delivery standard: every identified issue should end with concrete remediation (code + test + commit), unless explicitly blocked by external dependencies.
- Additional standing duty: run **Spec normalization** across `.kiro/specs/` to keep requirements/design/tasks aligned with current architecture, repository paths, and implementation reality.

## Spec Normalization Trigger
- Trigger keywords (Chinese/English): `spec规范化`, `规范化spec`, `spec统一`, `文档统一`, `架构对齐`, `spec audit`, `spec normalize`, `spec consistency`.
- On trigger, execute normalization workflow by default (without waiting for extra instruction):
  - Build a `spec -> architecture -> code` drift matrix.
  - Fix stack drift (prefer Python-first core unless explicitly approved otherwise).
  - Fix invalid/outdated file paths in spec docs.
  - Fix requirement structure drift against `.kiro/SPEC_DOCUMENTATION_STANDARD.md`.
  - Update `.kiro/specs/SPEC_TASKS_SCAN.md` checkpoint/status to factual state.

## Must-Read Rules (.mdc)
- Read `.cursor/rules/owlclaw_core.mdc` first for global process and spec loop rules.
- Apply `.cursor/rules/owlclaw_principles.mdc` for coding constraints (AI-first decisions, no fake data, logging rules).
- Apply `.cursor/rules/owlclaw_development.mdc` for workflow, Poetry usage, and commit discipline.
- Apply `.cursor/rules/owlclaw_architecture.mdc` for package boundaries and integration isolation.
- Apply `.cursor/rules/owlclaw_testing.mdc` for test structure and coverage expectations.
- Apply `.cursor/rules/owlclaw_spec_standards.mdc` when creating/updating specs under `.kiro/specs/`.
- Apply `.cursor/rules/owlclaw_database.mdc` for DB-related changes.

## Multi-Agent Coordination (Git Worktree)
- **Must-read**: `docs/WORKTREE_GUIDE.md` — full coordination guide for all AI agents.
- **Task assignments**: `.kiro/WORKTREE_ASSIGNMENTS.md` — which specs/modules are assigned to which worktree. Read before starting work.
- Isolation model: each AI tool works in its own Git worktree (physically separate directory, shared `.git`).
  - `D:\AI\owlclaw\` (branch `main`): Cursor / human — interactive dev, merge operations.
  - `D:\AI\owlclaw-review\` (branch `review-work`): Codex-CLI — spec audit, code review, doc fixes.
  - `D:\AI\owlclaw-codex\` (branch `codex-work`): Codex-CLI — feature implementation, tests.
  - `D:\AI\owlclaw-codex-gpt\` (branch `codex-gpt-work`): Codex-CLI — feature implementation, tests.
- Before starting work: confirm which worktree you are in (`git worktree list`).
- Work only in your own worktree; commit to your own branch.
- Two coding worktrees must work on **different** specs/modules to minimize merge conflicts.
- Merging into `main` is done by human or Cursor; recommended order: review → codex → codex-gpt.
- Before each work round: sync with `git merge main` in your worktree.
- No file-level claim mechanism needed — worktree isolation replaces `AGENT_WORK_CLAIMS.md`.

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
