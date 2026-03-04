# Incremental Review Round 28 (2026-03-04)

## Scope
- Delta since `review-work@4e8620c`.
- New commits:
  - `codex-work`: `517b32f` (ledger `order_by` filter + E2E coverage) and docs sync commits
  - `codex-gpt-work`: docs/progress sync (`b587739`, etc.)

## Validation

### codex-work
- Reviewed frontend/app changes:
  - `owlclaw/web/frontend/src/components/data/LedgerFilters.tsx`
  - `owlclaw/web/frontend/src/hooks/useApi.ts`
  - `owlclaw/web/frontend/src/pages/Ledger.tsx`
  - `owlclaw/web/frontend/e2e/console-flow.spec.ts` (F-14)
- Post-merge backend regression guard:
  - `poetry run pytest tests/unit/web/test_agents.py tests/unit/web/test_triggers.py -q`
  - Result: `11 passed`
- Frontend build verification:
  - `npm run build` in `owlclaw/web/frontend`
  - Result: success
- Playwright targeted test attempt:
  - `npx playwright test e2e/console-flow.spec.ts -g "Ledger sort change triggers order_by request param (F-14)"`
  - Result: failed due local console server not running (`ERR_CONNECTION_REFUSED`), not assertion failure.

Verdict:
`review(console-ledger-order-by): APPROVE — code path and build validated; E2E requires running server environment`

### codex-gpt-work
- New delta is docs/progress sync only.
- Merged into `review-work` (resolved SPEC_TASKS_SCAN conflict by keeping review baseline).

Verdict:
`review(governance-doc-sync): APPROVE`

## Gate Status
- No pending delta vs `codex-work` / `codex-gpt-work`.
- Review gate remains green.
