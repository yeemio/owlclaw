# Incremental Review Round 20 (2026-03-04)

## Scope
- Delta since `review-work@d37a91f`.
- Branches checked:
  - `codex-work`: new commit `833df9a` (+ orchestration/docs sync commits)
  - `codex-gpt-work`: new commit `7ce83a9` (+ sync merges/docs)

## Validation

### codex-work
- Reviewed `owlclaw/web/api/middleware.py` + tests.
- Verified on coding branch:
  - `poetry run pytest tests/unit/web/test_middleware.py -q`
  - Result: `8 passed`
- Merged approved delta into `review-work`:
  - `git merge --no-ff codex-work`
- Post-merge verification in `review-work`:
  - `poetry run pytest tests/unit/web/test_middleware.py -q`
  - Result: `8 passed`

Verdict:
`review(web-auth-config): APPROVE — optional strict auth configuration works as intended`

### codex-gpt-work
- Reviewed incremental governance/API changes (`7ce83a9`) and their tests.
- Verified on coding branch:
  - `poetry run pytest tests/unit/governance/test_constraints_budget.py tests/unit/governance/test_visibility.py tests/unit/triggers/test_api.py tests/unit/test_config_models.py -q`
  - Result: `51 passed`
- Re-checked previously blocked issue:
  - `_resolve_ssl_connect_args(" ")` still returns `{}` (no `ConfigurationError`).

Verdict:
`review(governance-hardening): FIX_NEEDED — prior ssl_mode blocker remains unresolved`

## Findings
1. [P1] Existing blocker still open in `codex-gpt-work`.
   - File: `owlclaw/db/engine.py`
   - Behavior: explicit whitespace `ssl_mode` is treated as empty/unset.
   - Expected by review gate: explicit invalid input should raise `ConfigurationError` (unset behavior can remain unchanged).

## Gate Status
- `codex-work`: approved and merged into `review-work`.
- `codex-gpt-work`: still blocked until ssl_mode input validation is fixed at runtime level.
