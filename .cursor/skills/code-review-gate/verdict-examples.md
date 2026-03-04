# Verdict Examples — Real-World Review Decisions

> These examples show the reasoning behind each verdict type.
> Study the thought process, not just the format.

---

## Example 1: Clean APPROVE

**Context**: Coding agent implemented config-propagation-fix Task 1-3.
Changes: `owlclaw/config/models.py` (new validation), `owlclaw/app.py`
(propagation fix), 2 new test files.

```
review(config-propagation-fix): APPROVE — config chain validated end-to-end

Dimensions: Spec ✅ | Quality ✅ | Tests ✅ | Architecture ✅ | Security ✅ | Cross-spec ✅
Notes:
- Nit: `_validate_model_name` regex could be documented in docstring
- Good: end-to-end test traces config from `configure()` to `litellm.acompletion()`
```

**Why APPROVE**: All dimensions pass. The nit is a style suggestion, not a
blocking issue. The implementation matches the spec, tests cover the critical
path, and the architecture is respected.

---

## Example 2: FIX_NEEDED — Missing Tests

**Context**: Coding agent implemented security-hardening Task 4 (webhook auth).
Changes: `owlclaw/triggers/webhook/http/app.py` (auth middleware added),
no test changes.

```
review(security-hardening): FIX_NEEDED — webhook auth implemented but untested

Dimensions: Spec ✅ | Quality ✅ | Tests ❌ | Architecture ✅ | Security ✅ | Cross-spec ✅
Issues:
1. [P1] No tests for new `WebhookAuthMiddleware` in `webhook/http/app.py:45-89`.
   Need at minimum:
   - test_webhook_auth_valid_signature() — happy path
   - test_webhook_auth_invalid_signature() — returns 401
   - test_webhook_auth_missing_header() — returns 401
   - test_webhook_auth_replay_attack() — timestamp too old, returns 401
2. [Low] `verify_signature()` at line 67 catches bare `Exception` — should
   catch `ValueError` and `hmac.InvalidSignature` specifically.
Action: Add test file `tests/unit/triggers/webhook/test_auth.py` with the
4 test cases above. Fix exception type in verify_signature().
```

**Why FIX_NEEDED (not REJECT)**: The implementation itself looks correct and
matches the spec. The issue is missing tests, which is a P1 (important but
not a security/data risk). The feedback is specific enough that the coding
agent can fix it without guessing.

---

## Example 3: FIX_NEEDED — Contract Drift

**Context**: Backend agent changed the error response format from
`{"error": "message"}` to `{"error": {"code": "ERR_001", "message": "..."}}`
but the frontend agent's code still expects the old format.

```
review(console-backend-api): FIX_NEEDED — error response envelope changed without frontend sync

Dimensions: Spec ⚠️ | Quality ✅ | Tests ✅ | Architecture ✅ | Security ✅ | Cross-spec ❌
Issues:
1. [P0] Error response shape changed at `web/api/routes.py:23` from
   `{"error": str}` to `{"error": {"code": str, "message": str}}`.
   Frontend `useApi.ts:45` destructures `response.error` as string.
   This will cause runtime TypeError in the frontend.
   Fix: Either revert the backend change, or coordinate with frontend
   agent to update `useApi.ts` error handling.
2. [P1] The new error schema is not documented in the OpenAPI spec at
   `docs/api/openapi.yaml`. The contract file must be updated first
   (contract-first rule).
Action: Update OpenAPI spec with new error schema. Coordinate with
frontend agent via shared mailbox. Do not merge until frontend is updated.
Cross-spec impact: console-frontend must update error handling.
```

**Why FIX_NEEDED (not REJECT)**: The code itself is well-written, but it
breaks the contract with the frontend. This is a P0 cross-spec issue, but
it's fixable by coordinating the change. If the backend agent had made this
change without any plan to update the frontend, it would be REJECT.

---

## Example 4: REJECT — Architecture Violation

**Context**: Coding agent implemented a feature by directly calling the
LLM provider SDK instead of going through the integration layer.

```
review(runtime-robustness): REJECT — direct litellm bypass violates integration isolation

Dimensions: Spec ✅ | Quality ✅ | Tests ✅ | Architecture ❌ | Security ⚠️ | Cross-spec ✅
Critical issues:
1. [P0] `owlclaw/agent/runtime/runtime.py:234` calls `litellm.acompletion()`
   directly instead of through `owlclaw/integrations/llm.py`. This bypasses:
   - Cost tracking (Ledger doesn't record the call)
   - Model routing (governance router is skipped)
   - Observability (Langfuse trace is missing)
   - Rate limiting (no governance check)
   This is a fundamental architecture violation per ARCHITECTURE_ANALYSIS.md §4.2.
   All LLM calls MUST go through the integration facade.
Action: Requires re-implementation using `integrations.llm.acompletion()`.
This is not a simple fix — the entire call chain needs to be restructured
to pass through the governance layer.
Escalate to: orchestrator for spec design review.
```

**Why REJECT (not FIX_NEEDED)**: This isn't a minor issue that can be fixed
with a one-line change. The coding agent fundamentally misunderstood the
architecture. The implementation needs to be redesigned, not patched. Sending
it back with FIX_NEEDED would likely result in a surface-level fix that
doesn't address the root cause.

---

## Example 5: APPROVE with Self-Fix

**Context**: Coding agent implemented governance-hardening Task 7.
Good implementation, but missing a type annotation and has a typo in a docstring.

```
review(governance-hardening): APPROVE — session lifecycle hardened, minor fixes applied

Dimensions: Spec ✅ | Quality ✅ | Tests ✅ | Architecture ✅ | Security ✅ | Cross-spec ✅
Self-fixed on review-work:
- Added return type `-> AsyncGenerator[AsyncSession, None]` to `get_session()` at db/session.py:34
- Fixed typo "conneciton" → "connection" in docstring at db/engine.py:12
Notes: none
```

**Why APPROVE with self-fix**: The issues were trivial (< 2 minutes to fix)
and didn't require the coding agent to understand anything new. Sending it
back for a typo fix would waste a full review round.

---

## Example 6: Multi-Round FIX_NEEDED Tracking

**Round 1**:
```
review(console-web): FIX_NEEDED — frontend/backend API contract drift and error-shape mismatch

Issues:
A. [P0] ErrorResponse not unified — backend returns different shapes from different endpoints
B. [P1] WebSocket message types don't match between backend and frontend
C. [P1] Frontend useApi.ts hardcodes endpoint paths instead of using generated client
```

**Round 2**:
```
review(console-web): FIX_NEEDED — coverage gate fixed, contract drifts still block

Issues:
A. ✅ FIXED — ErrorResponse now unified across all endpoints
B. ⚠️ PARTIAL — WebSocket types aligned for 3/5 message types, 2 still drift
C. ❌ STILL PRESENT — useApi.ts still hardcodes paths
New: D. [P1] CORS config allows credentials with wildcard origin
```

**Round 3**:
```
review(console-web): FIX_NEEDED — spec completion marked ahead of unresolved blockers

Issues:
B. ✅ FIXED — all 5 WebSocket message types now aligned
C. ✅ FIXED — useApi.ts now uses generated client
D. ❌ STILL PRESENT — CORS wildcard + credentials
New: E. [P1] tasks.md marks Task 8 as [x] but the implementation is incomplete
```

**Round 4**:
```
review(console-web): APPROVE — contract drifts closed and validation gates pass

Dimensions: Spec ✅ | Quality ✅ | Tests ✅ | Architecture ✅ | Security ✅ | Cross-spec ✅
All previously identified issues resolved:
A. ✅ B. ✅ C. ✅ D. ✅ E. ✅
```

**Key lesson**: Each round independently verifies ALL issues, not just new
ones. Issue D persisted for 2 rounds — the reviewer didn't let it slide
just because other issues were being fixed.
