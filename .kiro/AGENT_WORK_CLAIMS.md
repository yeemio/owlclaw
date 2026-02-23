# AGENT Work Claims

> Purpose: coordinate multi-agent parallel work and avoid file-level conflicts.
> Last updated: 2026-02-23

## Rules

1. Before starting any task, read this file and avoid paths claimed by other active agents.
2. If your task requires claimed files, coordinate first and wait until the claim is released.
3. Update your claim before code edits, and release it immediately after merge/hand-off.
4. Prefer claiming by module path, not whole repository.

## Active Claims

### Claim: codex-main-2026-02-23-a

- Owner: `codex-main` (this session)
- Status: `active`
- Goal: continue spec implementation on security module (infrastructure + data masking), excluding `cli-db` and `database-core`
- Specs in scope:
  - `security`
  - `skill-templates`
  - `integrations-langchain`
- Claimed paths:
  - `owlclaw/security/**`
  - `owlclaw/integrations/langchain/**`
  - `owlclaw/templates/skills/**`
  - `tests/unit/security/**`
  - `tests/unit/integrations/langchain/**`
  - `tests/unit/templates/skills/**`
  - `.kiro/specs/security/**`
  - `.kiro/specs/skill-templates/**`
  - `.kiro/specs/integrations-langchain/**`
  - `.kiro/specs/SPEC_TASKS_SCAN.md`
- Explicitly avoided paths:
  - `owlclaw/cli/db.py`
  - `owlclaw/cli/db_backup.py`
  - `owlclaw/db/**`
  - `.kiro/specs/cli-db/**`
  - `.kiro/specs/database-core/**`

## Claim Template

Copy and fill this section for each new agent:

### Claim: <agent-id>-<date>-<suffix>

- Owner: `<agent-name>`
- Status: `active | blocked | released`
- Goal: `<what you are doing>`
- Specs in scope:
  - `<spec-a>`
  - `<spec-b>`
- Claimed paths:
  - `<path/**>`
- Explicitly avoided paths:
  - `<path/**>`
