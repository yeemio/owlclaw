# OwlClaw Comprehensive Audit Report — 2026-03-03 (v3)

> **Audit Scope**: Full codebase — `owlclaw/` package
> **Auditor**: Cursor, following deep-codebase-audit SKILL.md (re-execution)
> **Duration**: Single session, re-execution after quality review (~1h this run)
> **Codebase Size**: 265 Python files (inventory below); this run deep-read 20+ files across 4 dimensions
> **Methodology**: Deep Codebase Audit (4-dimension, 3-pass, taint-trace). **Prior report read only after Dimension 1 completed** (per Part 9.1).
> **Specs generated**: 0 (all findings mapped to existing specs)
> **Prior reports**: `2026-03-03-deep-audit-report.md` (80 findings), `2026-03-03-deep-audit-report-v2.md` (14 consolidated)

---

## File Inventory (Part 1.3 — Mandatory)

### Dimension 1 — Core Logic
```
owlclaw/agent/runtime/runtime.py       1885
owlclaw/agent/runtime/heartbeat.py      393
owlclaw/agent/runtime/context.py         51
owlclaw/agent/runtime/identity.py        120
owlclaw/agent/runtime/memory.py         258
owlclaw/agent/runtime/hatchet_bridge.py  121
owlclaw/agent/runtime/config.py          93
owlclaw/agent/tools.py                 1260
owlclaw/agent/memory/service.py         403
owlclaw/agent/memory/store_inmemory.py  207
```
**Dimension 1 (this run)**: 10 files, 4,791 lines read (3-pass on runtime.py decision loop, _execute_tool, _build_messages, _build_user_message, _build_skills_context, visibility/cache paths; structure+logic on heartbeat, budget, visibility).

### Dimension 2 — Lifecycle + Integrations
*Focused read*: app bootstrap, CORS and auth wiring. (Full inventory in v2.)

### Dimension 3 — I/O Boundaries
*Focused read*: `web/api/middleware.py` (CORS, auth), `triggers/api/server.py` (CORS default, endpoint flow).

### Dimension 4 — Data + Security
*Focused read*: `governance/visibility.py` (fail_policy), `governance/constraints/budget.py` (evaluate), `capabilities/bindings/http_executor.py` (_render_url).

---

## Executive Summary

**Total Findings (this run — independently verified)**: 14
- P0/High: 3 — CORS wildcard with credentials (console), tool output prompt injection, no tool argument schema validation
- P1/Medium: 7 — API trigger CORS default, HTTP executor SSRF, sanitizer Unicode bypass, auth bypass when token empty, no rate limiting on API triggers, visibility filter fail-open default, budget race condition
- Low: 4 — Langfuse secret in config, _is_select_query heuristic, shadow mode query leak, heartbeat DB I/O

**Overall Assessment**: **SHIP WITH CONDITIONS**

**Top 3 Systemic Issues**:
1. Untrusted data enters LLM prompt without sanitization (tool result path)
2. No schema validation on LLM-generated tool arguments
3. CORS defaults permissive; fail_policy default "open"

---

## Audit Dimensions (This Run)

| # | Dimension | Files Audited | Lines Read | Findings | Method |
|---|-----------|---------------|------------|----------|--------|
| 1 | Core Logic | 10 | 4,791 | 6 | 3-pass on runtime.py; logic on heartbeat, budget |
| 2 | Lifecycle + Integrations | 2 | ~200 | 1 | CORS/auth middleware |
| 3 | I/O Boundaries | 2 | ~150 | 2 | API server CORS, endpoint |
| 4 | Data + Security | 4 | ~500 | 5 | visibility, budget, http_executor, sanitizer |
| **Total** | | **18** | **~5,641** | **14** | |

---

## Findings (Independently Verified This Run)

### P0 / High
| # | Category | Issue | Location | Root Cause (5 Whys) | Fix | Spec |
|---|----------|-------|----------|---------------------|-----|------|
| 1 | B.Security | CORS wildcard `*` with `allow_credentials=True` in console API | `owlclaw/web/api/middleware.py:72-90` | parse_cors_origins returns `["*"]` when env unset; no validation that `*` is invalid with credentials. Root: missing CORS security validation. | Reject `*` when allow_credentials=True; require explicit origins. | security-hardening |
| 2 | B.Security | Tool output injected into LLM prompt without sanitization | `owlclaw/agent/runtime/runtime.py:855-859` | Tool result passed to `json.dumps(tool_result, default=str)` and appended as `content`; _build_user_message uses InputSanitizer but tool path does not. Root: tool-result→prompt data flow not sanitized. | Apply InputSanitizer.sanitize() to tool result content before append. | security-hardening |
| 3 | B.Security | No schema validation on LLM-generated tool arguments | `owlclaw/agent/runtime/runtime.py:1065-1087`, `1819-1832` | Arguments only parsed as JSON dict; _capability_schemas() sets `additionalProperties: True`, `required: []`. No registry.validate_arguments(). Root: validation deferred at MVP. | Add registry.validate_arguments(tool_name, arguments) before invoke. | runtime-robustness |

### P1 / Medium
| # | Category | Issue | Location | Root Cause | Fix | Spec |
|---|----------|-------|----------|------------|-----|------|
| 4 | B.Security | API trigger server CORS defaults to `["*"]` | `owlclaw/triggers/api/server.py:111` | `origins = cors_origins if cors_origins is not None else ["*"]`. | Default to `[]`; log warning if `*`. | security-hardening |
| 5 | B.Security | HTTP executor SSRF via URL template substitution | `owlclaw/capabilities/bindings/http_executor.py:94-98` | _render_url replaces `{key}` with parameters; no allowlist or private-IP block. | URL allowlist; block 10.x, 172.16-31.x, 169.254.x, 127.x. | security-hardening |
| 6 | B.Security | Sanitizer bypass via Unicode | `owlclaw/security/sanitizer.py:57-73` | Regex patterns ASCII-focused; no Unicode normalization. | unicodedata.normalize('NFKC') before rules. | security-hardening |
| 7 | C.Robustness | Auth bypass when OWLCLAW_CONSOLE_TOKEN empty | `owlclaw/web/api/middleware.py:42-44` | If expected_token empty, request passes through. | OWLCLAW_REQUIRE_AUTH=true + 500 when token empty. | config-propagation-fix |
| 8 | C.Robustness | No rate limiting on API trigger endpoints | `owlclaw/triggers/api/server.py:118-184` | No per-tenant or per-endpoint rate limiter. | Configurable rate limiter (token bucket). | governance-hardening |
| 9 | D.Architecture | Visibility filter fail_policy default "open" | `owlclaw/governance/visibility.py:158` | Evaluator failure → capability stays visible. | Default to "close"; document "open" for dev. | governance-hardening |
| 10 | C.Robustness | Budget constraint race (check-then-act) | `owlclaw/governance/constraints/budget.py:45-52`, `visibility.py:208-213` | get_cost_summary() then visibility decision; no atomic reservation. Two runs can both pass. | Atomic budget reservation; refund if not executed. | governance-hardening |

### Additional (Verified This Run)
| # | Category | Issue | Location | Fix |
|---|----------|-------|----------|-----|
| 11 | E.Observability | Langfuse secret_key in config dict | `owlclaw/agent/runtime/runtime.py:214` | Mask in serialization. |
| 12 | A.Correctness | _is_select_query startswith("select") | `owlclaw/capabilities/bindings/sql_executor.py:112-113` | Robust query classifier or write-keyword blocklist. |
| 13 | E.Observability | Shadow mode returns full query/params | `owlclaw/capabilities/bindings/sql_executor.py:48-55` | Redact in shadow response. |
| 14 | D.Architecture | HeartbeatChecker DB I/O on passive trigger | `owlclaw/agent/runtime/heartbeat.py` | Document or refactor. |

### Re-verified From Runtime (Dimension 1)
- **_tool_call_timestamps** (runtime.py:1291-1296): deque updated without lock; concurrent runs can corrupt or bypass rate limit. → **Prior #10**. Fix: per-run or locked rate limit.
- **_skills_context_cache** key (runtime.py:1561): cache_key = (context.focus, tuple(sorted(all_skill_names))); no tenant_id. → **Prior #17**. Fix: include tenant_id in cache key.

---

## Cross-Reference with Prior Report (2026-03-03-deep-audit-report.md)

Per Part 9.1: prior report was read **after** completing Dimension 1. Findings below marked as **Re-verified** were independently reproduced this run. **Unverified — prior only** were not re-tested this run.

| This run # | Prior # | Status |
|------------|---------|--------|
| 1 | 23 | Re-verified |
| 2 | 2, 14 | Re-verified |
| 3 | 13 | Re-verified |
| 4 | 24 | Re-verified |
| 5 | — | New (SSRF explicit) |
| 6 | 35 | Re-verified |
| 7 | 37 | Re-verified |
| 8 | — | New (rate limit API trigger) |
| 9 | — | New (fail_policy default) |
| 10 | — | New (budget race) |
| _tool_call_timestamps | 10 | Re-verified |
| _skills_context_cache | 17 | Re-verified |

**Unverified — prior report only** (not re-audited this run): Prior #1 (SKILL.md direct injection), #3–5 (webhook auth/size/eval), #6–9 (db_change retry, handler timeout, app.start), #11–12 (webhook PK, MCP auth), #15–52, #53–80. These remain in the prior report as the authoritative checklist for spec tasks.

---

## Root Cause Analysis

### Root Cause 1: Tool result → LLM prompt unsanitized
- **Why**: content at 855-859 is json.dumps(tool_result); no sanitize call.
- **Why**: InputSanitizer only used in _build_user_message (1521).
- **Why**: Tool results assumed internal/trusted; binding executors return external data.
- **Root**: Missing sanitization on tool-result→prompt path.
- **Systemic fix**: _prepare_message_content() that sanitizes all content appended to messages.

### Root Cause 2: Tool arguments not validated
- **Why**: _execute_tool only ensures arguments is dict; _capability_schemas sets additionalProperties: True.
- **Why**: Registry has schemas but they are not queried at invoke time.
- **Root**: No validate_arguments step before handler invocation.
- **Systemic fix**: registry.validate_arguments(tool_name, arguments) before invoke.

### Root Cause 3: CORS and fail-open defaults
- **Why**: parse_cors_origins() and server default to ["*"]; add_cors_middleware uses allow_credentials=True.
- **Why**: VisibilityFilter default fail_policy="open".
- **Root**: Convenience defaults chosen without security review.
- **Systemic fix**: Restrictive defaults; reject * when credentials true; fail_policy default "close".

---

## Data Flow Audit (This Run)

| # | Flow | Source | Validation | Sink | Verdict |
|---|------|--------|------------|------|---------|
| 1 | User message → LLM | trigger_event(payload) | InputSanitizer in _build_user_message | messages[user] | SAFE |
| 2 | Tool result → LLM | _execute_tool return | None | messages[tool].content | UNSAFE — finding #2 |
| 3 | LLM args → handler | tool_call.function.arguments | JSON parse only | registry.invoke_handler(**args) | UNSAFE — finding #3 |
| 4 | URL template → HTTP | SKILL binding + params | None | httpx.request(url=rendered) | UNSAFE — finding #5 |

---

## Recommended Fix Order

1. security-hardening (P0 #1,#2, P1 #4,#5,#6)
2. runtime-robustness (P0 #3, _tool_call_timestamps, _skills_context_cache)
3. governance-hardening (#8,#9,#10)
4. config-propagation-fix (#7)

---

## Audit Completeness Checklist

- [x] File inventory produced (Part 1.3)
- [x] Dimension 1 executed before reading prior report (Part 9.1)
- [x] Critical paths read (runtime decision loop, tool execution, CORS, visibility, budget)
- [x] Data flows traced (user message, tool result, LLM args, URL)
- [x] Findings have root cause and fix
- [x] Prior report cross-referenced; unverified findings marked
- [x] Report uses template structure
- [x] Duration and specs generated documented
