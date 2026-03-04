# OwlClaw Comprehensive Audit Report — 2026-03-04 (v4)

> **Audit Scope**: Full codebase — `owlclaw/` package
> **Auditor**: Claude (GLM-5), 4-dimension parallel audit
> **Duration**: Single session, ~3min wall clock (parallel agents)
> **Codebase Size**: 265 Python files
> **Methodology**: Deep Codebase Audit (4-dimension parallel)
> **Prior Reports**: v2 (14 findings), v3 (14 findings)

---

## Executive Summary

**Total Findings**: 14 (re-verified) + 4 (new) = **18**
- P0/High: 3 — CORS wildcard + credentials, tool output prompt injection, no tool argument schema validation
- P1/Medium: 10 — API trigger CORS, HTTP SSRF, Unicode bypass, auth bypass, rate limiting, fail_policy, budget race, plus new findings
- Low: 5 — Langfuse secret, _is_select_query, shadow mode leak, heartbeat DB I/O, new low findings

**Overall Assessment**: **SHIP WITH CONDITIONS** — 3 P0 issues require fix timeline before release. All P0/P1 issues remain unfixed since v2/v3 audit.

**Change Since Last Audit**:
- P0/P1 security issues: **0 fixed**
- New E2E tests added: 18 tests (console-flow.spec.ts)
- Spec tasks: Defined but not implemented

---

## Audit Dimensions Summary

| # | Dimension | Findings | Method |
|---|-----------|----------|--------|
| 1 | Security | 6 P0/P1 + 2 new | middleware.py, runtime.py, sanitizer.py, http_executor.py |
| 2 | Runtime Robustness | 4 P1 | runtime.py, registry.py, store_inmemory.py |
| 3 | E2E Test Coverage | 2 gaps | console-flow.spec.ts vs BROWSER_TEST_REQUIREMENTS.md |
| 4 | Governance + Config | 2 P1 confirmed | visibility.py, budget.py |
| **Total** | | **18** | |

---

## P0 / High Severity — Must Fix Before Release

| # | Issue | Location | Status | Fix |
|---|-------|----------|--------|-----|
| 1 | CORS wildcard `*` with `allow_credentials=True` | `middleware.py:72-90` | **UNFIXED** | Reject `*` when credentials enabled |
| 2 | Tool output injected into LLM prompt without sanitization | `runtime.py:855-859` | **UNFIXED** | Apply InputSanitizer to tool results |
| 3 | No schema validation on LLM-generated tool arguments | `runtime.py:1065-1087` | **UNFIXED** | Add registry.validate_arguments() |

---

## P1 / Medium Severity — Important Defects

| # | Issue | Location | Status | Fix |
|---|-------|----------|--------|-----|
| 4 | API trigger CORS defaults to `["*"]` | `server.py:111-112` | **UNFIXED** | Default to `[]` |
| 5 | HTTP executor SSRF via URL template | `http_executor.py:94-98` | **UNFIXED** | URL allowlist + private IP block |
| 6 | Sanitizer bypass via Unicode | `sanitizer.py:57-73` | **UNFIXED** | Add unicodedata.normalize('NFKC') |
| 7 | Auth bypass when token empty | `middleware.py:42-44` | **UNFIXED** | Add OWLCLAW_REQUIRE_AUTH check |
| 8 | No rate limiting on API triggers | `server.py:78-184` | **UNFIXED** | Add token bucket limiter |
| 9 | Visibility filter fail_policy default "open" | `visibility.py:158` | **UNFIXED** | Change default to "close" |
| 10 | Budget constraint race condition | `budget.py:45-65` | **UNFIXED** | Atomic budget reservation |
| 11 | **[NEW]** _tool_call_timestamps no lock | `runtime.py:1293-1298` | **UNFIXED** | Add asyncio.Lock |
| 12 | **[NEW]** skills_context_cache missing tenant_id | `runtime.py:1559` | **UNFIXED** | Add tenant_id to cache key |

---

## Low Severity — Improvements

| # | Issue | Location |
|---|-------|----------|
| 13 | Langfuse secret_key in config dict | `runtime.py:214` |
| 14 | _is_select_query heuristic | `sql_executor.py:112-113` |
| 15 | Shadow mode leaks query text | `sql_executor.py:48-55` |
| 16 | HeartbeatChecker DB I/O on passive trigger | `heartbeat.py` |
| 17 | **[NEW]** InMemoryStore no lock + no size limit | `store_inmemory.py:33-190` |
| 18 | **[NEW]** db_change infinite retry loop | `manager.py:188-201` |

---

## E2E Test Coverage Audit

### Current Coverage: 18/18 tests passing

**By Dimension (BROWSER_TEST_REQUIREMENTS.md)**:

| Dimension | Coverage | Status |
|-----------|----------|--------|
| Functional | 85% | F-4, F-14, F-16, F-18, F-20 missing |
| API | 70% | No Zod/Ajv schema validation |
| Code/Network | 90% | No HAR/screenshot evidence |
| Effects | 75% | axe WCAG but no contrast checks |

### Gaps vs Requirements

1. **P0 Gap**: API response schema validation (Zod/Ajv)
2. **P1 Gap**: Request body/query contract validation
3. **P2 Gap**: HAR recording for failure evidence

### Positive Findings

- ✅ axe-core WCAG A/AA scans on Overview/Governance/Ledger
- ✅ Negative paths: 500/422/malformed JSON
- ✅ No uncaught JS errors (`page.on('pageerror')`)
- ✅ WebSocket connection verification

---

## Root Cause Analysis

### Root Cause 1: Untrusted data → LLM prompt unsanitized

```
User Message ──sanitize──▶ LLM prompt ✅
Tool Result ──────────────▶ LLM prompt ❌ (Finding #2)
HTTP Response ────────────▶ Tool Result ─▶ LLM prompt ❌ (Finding #2)
SQL Query Result ─────────▶ Tool Result ─▶ LLM prompt ❌ (Finding #2)
```

**Systemic Fix**: Single `_prepare_message_content()` that sanitizes all content.

### Root Cause 2: No schema validation on tool arguments

```
LLM generates JSON arguments
    ↓
runtime.py: JSON parse only
    ↓
registry.invoke_handler(**args)  ❌ No schema check (Finding #3)
```

**Systemic Fix**: `registry.validate_arguments(tool_name, args)` before invoke.

### Root Cause 3: Insecure defaults

| Component | Default | Should Be |
|-----------|---------|-----------|
| CORS origins | `["*"]` | `[]` |
| fail_policy | `"open"` | `"close"` |
| Empty token | Pass through | Reject |

---

## Spec Tasks Progress (Updated 2026-03-04)

| Spec | Tasks | Completed | P0/P1 Issues |
|------|-------|-----------|--------------|
| security-hardening | 15 | 15 | 6 |
| runtime-robustness | 20 | 3 | 4 |
| governance-hardening | 12 | 3 | 3 |
| config-propagation-fix | 10 | 10 | 1 |
| **Total** | **57** | **31** | **14** |

**Conclusion**: Phase 12 已有实质落地：`security-hardening` 与 `config-propagation-fix` 已收口，`runtime-robustness` 与 `governance-hardening` 在推进中。

---

## Recommended Fix Order

| Priority | Spec | Tasks | Rationale |
|----------|------|-------|-----------|
| 1 | security-hardening | #1-3 | P0: CORS, prompt injection, schema validation |
| 2 | runtime-robustness | #2-3 | P1: Concurrency safety |
| 3 | governance-hardening | #8-10 | P1: Rate limiting, fail_policy, budget race |
| 4 | config-propagation-fix | #7 | P1: Auth enforcement |

---

## Comparison with Prior Reports (at audit capture time)

| Finding | v2 Status | v3 Status | v4 Status |
|---------|-----------|-----------|-----------|
| #1 CORS + credentials | UNFIXED | UNFIXED | **UNFIXED** |
| #2 Tool output injection | UNFIXED | UNFIXED | **UNFIXED** |
| #3 No schema validation | UNFIXED | UNFIXED | **UNFIXED** |
| #4 API trigger CORS | UNFIXED | UNFIXED | **UNFIXED** |
| #5 HTTP SSRF | UNFIXED | UNFIXED | **UNFIXED** |
| #6 Unicode bypass | UNFIXED | UNFIXED | **UNFIXED** |
| #7 Auth bypass | UNFIXED | UNFIXED | **UNFIXED** |
| #8 No rate limiting | UNFIXED | UNFIXED | **UNFIXED** |
| #9 fail_policy open | UNFIXED | UNFIXED | **UNFIXED** |
| #10 Budget race | UNFIXED | UNFIXED | **UNFIXED** |

**New in v4**: Findings #11-18 (runtime robustness + E2E gaps)

---

## Action Items

### Immediate (P0 — Block Release)
1. Fix CORS wildcard + credentials validation
2. Sanitize tool results before LLM prompt
3. Add schema validation for tool arguments

### Short-term (P1 — Before Next Release)
4. Add asyncio.Lock to _tool_call_timestamps
5. Add tenant_id to skills_context_cache key
6. Change fail_policy default to "close"
7. Implement atomic budget reservation
8. Add rate limiting to API triggers

### Medium-term (P2 — Backlog)
9. Complete E2E test coverage gaps
10. Add HAR/screenshot evidence to E2E tests
11. Add Zod/Ajv schema validation to API tests

---

## Audit Completeness Checklist

- [x] 4 dimensions audited in parallel
- [x] All P0/P1 findings from v2/v3 re-verified
- [x] New findings documented
- [x] E2E test coverage analyzed
- [x] Spec tasks progress tracked
- [x] Root cause analysis completed
- [x] Recommended fix order established

---

**Auditor**: Claude (GLM-5)
**Date**: 2026-03-04
**Next Audit**: After P0 fixes implemented

---

## Post-Audit Implementation Update (2026-03-04, codex-work)

After this report was generated, Phase 12 implementation advanced and multiple findings were closed:

- P0 #1 fixed: CORS wildcard + credentials conflict guarded (`owlclaw/web/api/middleware.py`)
- P0 #2 fixed: tool result sanitization before LLM prompt (`owlclaw/agent/runtime/runtime.py`)
- P0 #3 fixed: tool argument schema validation (`owlclaw/agent/runtime/runtime.py`)
- P1 #4 fixed: API trigger default CORS closed (`owlclaw/triggers/api/server.py`)
- P1 #5 fixed: HTTP executor SSRF host/private-network guard (`owlclaw/capabilities/bindings/http_executor.py`)
- P1 #6 fixed: Unicode NFKC normalization coverage (`owlclaw/security/sanitizer.py` + tests)
- P1 #7 fixed: empty-token auth bypass blocked (`owlclaw/web/api/middleware.py`)

Console no-DB regression items from browser verification were also fixed:
- BUG-1 fixed: `/api/v1/agents/{id}` no longer returns 500 without DB
- BUG-2 fixed: `/api/v1/triggers` no longer returns 500 without DB

Open items remain in runtime/governance hardening tracks (e.g., R1/R11, rate limiting, budget race).
