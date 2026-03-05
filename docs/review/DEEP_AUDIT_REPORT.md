# OwlClaw Comprehensive Audit Report — 2026-03-05

> **Audit Scope**: Core Logic, Lifecycle+Integrations, I/O Boundaries, Data+Security (critical paths)
> **Auditor**: Deep Codebase Audit (4-dimension, 3-pass, taint-trace)
> **Duration**: Single session
> **Codebase Size**: ~2900 lines (runtime+heartbeat+context+config), + engine, ledger, web/ws, bindings, sanitizer
> **Methodology**: Deep Codebase Audit (4-dimension, 3-pass, taint-trace)

---

## Executive Summary

**Total Findings**: 11 (Phase 1: 6; Phase 2: +2 Low; Phase 3: +3 Low)
- P0/High: 0
- P1/Medium: 2
- Low: 9

**Overall Assessment**: **SHIP WITH CONDITIONS**

- No P0. Two P1 issues: (1) skill-declared env vars written to process `os.environ` without allowlist; (2) Console WebSocket/API tenant_id is client-controlled with no server-side membership check. Both have clear mitigations.
- Low findings: cache eviction policy, heartbeat coupling to Ledger private attr, exception message in LLM context, engine exception mapping.

**Top 3 Systemic Issues**:
1. **Trust boundary at tenant_id** — Console and WS take `x-owlclaw-tenant` from client; in multi-tenant deployments this must be replaced or validated by auth/session.
2. **Skill env injection into process** — Skills can set arbitrary `os.environ` keys during run; need allowlist or prefix (e.g. `OWLCLAW_SKILL_`) to prevent abuse.
3. **Configuration propagation** — Model/defaults are well-wired; no broken propagation found in audited paths; `.env` loading in `owlclaw start` was added and works.

---

## Audit Dimensions

| # | Dimension | Files Audited | Lines Read | Findings | Method |
|---|-----------|---------------|------------|----------|--------|
| 1 | Core Logic | runtime.py, heartbeat.py, context.py, config.py | ~2900 | 3 | Structure + Logic + Data flow |
| 2 | Lifecycle + Integrations | engine.py, llm.py (facade), ledger.py (partial) | ~450 | 1 | Error paths, timeouts, cleanup |
| 3 | I/O Boundaries | ws.py, deps.py | ~170 | 2 | Input validation, tenant source |
| 4 | Data + Security | ledger.py (model), sanitizer.py, sql_executor.py | ~350 | 0 (positive) | Parameterization, tenant in query |
| **Total** | | **10** | **~3870** | **6** | |

---

## Findings

### P0 / High — Must Fix Before Release

(No P0 findings.)

### P1 / Medium — Important Defect

| # | Category | Issue | Location | Root Cause (5 Whys) | Fix | Spec |
|---|----------|-------|----------|---------------------|-----|------|
| 1 | B.Security | Skill-declared `owlclaw_config.env` keys are written to `os.environ` for the run with no allowlist or prefix. A malicious or misconfigured skill could set e.g. `PATH`, `PYTHONPATH`, or `OWLCLAW_DATABASE_URL`, affecting subprocesses or the same process. | `owlclaw/agent/runtime/runtime.py:1245-1263` (_inject_skill_env_for_run) | Skills were designed to inject env for handler use; no threat model for which keys are safe. Allowlist/namespace was not in scope at design time. | Restrict to keys with prefix `OWLCLAW_SKILL_` or to an explicit allowlist in runtime config (e.g. `skill_env_allowlist: ["MY_API_KEY"]`). Reject or ignore any key not in allowlist/prefix. | (new spec or design doc) |
| 2 | B.Security | Console WebSocket and REST API derive `tenant_id` from header `x-owlclaw-tenant` with no server-side validation. Client can send any tenant_id and receive overview/triggers/ledger for that tenant. | `owlclaw/web/api/deps.py:66-71` (get_tenant_id), `owlclaw/web/api/ws.py:141` | API was built for self-hosted/single-tenant first; tenant_id used as label. Multi-tenant membership check was not implemented. | For multi-tenant deployments: derive tenant_id from authenticated session or JWT claim; ignore or override client-supplied header. Document that current behavior is acceptable only when tenant_id is a non-security label (e.g. self-hosted). | (new spec or design doc) |

### Low — Improvement

| # | Category | Issue | Location | Fix |
|---|----------|-------|----------|-----|
| 3 | C.Robustness | Visible-tools and skills-context caches use simple dict with max 64 entries; eviction is `pop(next(iter(cache)))` (arbitrary). Under high churn, useful entries may be evicted first. | `owlclaw/agent/runtime/runtime.py:1224, 1281` | Use LRU (e.g. `functools.lru_cache` or a small LRU dict) so least-recently-used is evicted. |
| 4 | D.Architecture | HeartbeatChecker resolves session factory via `getattr(self._ledger, "_session_factory", None)`, coupling to Ledger’s private attribute. | `owlclaw/agent/runtime/heartbeat.py:311-317` | Expose a formal interface on Ledger (e.g. `get_readonly_session_factory()`) or pass session_factory in HeartbeatChecker config so Heartbeat does not depend on Ledger internals. |
| 5 | C.Robustness | When LLM call fails, exception message is appended to conversation as assistant content (`str(exc)`). If an exception ever contained sensitive data (e.g. from a provider), it could leak into the next LLM call. | `owlclaw/agent/runtime/runtime.py:527-531` | Sanitize or truncate the error string before appending (e.g. generic "LLM call failed" or allowlist known safe messages). |
| 6 | C.Robustness | In `db/engine.py`, `create_engine` maps any non-ConfigurationError exception to `_map_connection_exception` (Connection/Auth). Other failures (e.g. TypeError from create_async_engine) would be reported as connection error. | `owlclaw/db/engine.py:128-131` | Re-raise ConfigurationError; map only connection/auth-like exceptions (e.g. OperationalError, InterfaceError); re-raise others with original type or wrap in a generic EngineError. |
| 7 | C.Robustness | DefaultCapabilitiesProvider does not catch ConfigurationError in _collect_capability_stats; GET /capabilities can 500 when DB not configured (ledger/triggers return empty). | `owlclaw/web/providers/capabilities.py:84-98` | Wrap get_engine/session in try/except ConfigurationError; return empty stats so list_capabilities returns items with zero stats. |
| 8 | D.Architecture | health_status() reads db_change_manager._states and api_trigger_server._configs (private attributes). | `owlclaw/app.py:1099-1100` | Prefer public API or document coupling; or expose read-only properties. |
| 9 | C.Robustness | Ledger._background_writer on generic Exception does not flush current batch to DB or fallback; records can be lost. | `owlclaw/governance/ledger.py:329-332` | On Exception, flush current batch to fallback before continuing. |
| 10 | C.Robustness | Ledger._write_queue unbounded; sustained load can grow memory. | `owlclaw/governance/ledger.py:135` | Bounded queue and/or backpressure; document limit. |
| 11 | C.Robustness | Webhook raw_body_bytes.decode("utf-8") can raise; non-UTF-8 body returns 500. | `owlclaw/triggers/webhook/http/app.py:167` | Catch UnicodeDecodeError; return 400 with clear message. |

---

## Root Cause Analysis

### Root Cause 1: Tenant identity is client-controlled at API boundary

**Description**: Console and WebSocket APIs trust the `x-owlclaw-tenant` header. There is no server-side binding of tenant to authenticated identity.

**Why it exists**:
1. Console was designed for self-hosted / single-tenant first.
2. Tenant_id was treated as a label for filtering, not as an authorization scope.
3. No auth middleware was in place to attach tenant to session/JWT.
4. Multi-tenant SaaS was not in the initial threat model.
5. Process gap: no security review checklist for “who can see which tenant’s data.”

**Manifestations**:
| Finding # | Symptom | Location |
|-----------|---------|----------|
| 2 | Client can choose tenant_id and get that tenant’s overview/triggers/ledger | `deps.py:66-71`, `ws.py:141` |

**Systemic Fix**: For any multi-tenant deployment, derive tenant_id only from authenticated context (session, JWT claim, or API key scope). Document that current behavior is acceptable only when tenant is a non-security label.

### Root Cause 2: Skill env injection has no safety boundary

**Description**: Skills can declare arbitrary env vars that are written to the process environment during a run. There is no allowlist or prefix.

**Why it exists**:
1. Feature allowed skills to pass config (e.g. API keys) to handlers.
2. Implementation used `os.environ[key] = value` for simplicity.
3. No threat model for malicious or typo’d keys (e.g. PATH, OWLCLAW_*).
4. Design assumed trusted skill authors.
5. Process gap: no “untrusted input” treatment for skill-declared env.

**Manifestations**:
| Finding # | Symptom | Location |
|-----------|---------|----------|
| 1 | Any key from skill `owlclaw_config.env` is applied to process env | `runtime.py:1245-1263` |

**Systemic Fix**: Only allow keys that match an allowlist or a dedicated prefix (e.g. `OWLCLAW_SKILL_`). Reject or ignore others and optionally log.

---

## Architecture Compliance Assessment

| Quality Attribute | Architectural Decision | Implementation Status | Verdict |
|-------------------|------------------------|------------------------|---------|
| Security | Governance visibility filter; ledger records; input sanitization | Visibility filter used for tools; ledger has tenant_id; user message and tool result sanitized; SQL binding parameterized | PARTIAL (tenant_id client-controlled; skill env unconstrained) |
| Robustness | Timeouts on LLM and run; heartbeat DB timeout; connection pool | asyncio.wait_for on LLM and run; heartbeat uses wait_for on DB query; pool_timeout on engine | PASS |
| Modifiability | Integrations isolated (llm, hatchet, db); single LLM facade | LLM calls go through integrations/llm; db through engine/session; Ledger queue-based | PASS |

---

## Data Flow Audit Results

| # | Flow | Source | Validation | Transformation | Sink | Verdict |
|---|------|--------|------------|----------------|------|---------|
| 1 | User/trigger payload → user message | context.payload, context.trigger | trigger_event validates event_name, tenant_id, payload type; _build_user_message sanitizes with InputSanitizer | json.dumps(payload); sanitize | LLM messages | SAFE (sanitized) |
| 2 | Tool result → LLM message | registry.invoke_handler / builtin result | _sanitize_tool_result (InputSanitizer) | json.dumps; sanitize | messages (tool role) | SAFE |
| 3 | Tenant for Console/WS | Header x-owlclaw-tenant | None (only strip) | get_tenant_id returns header or "default" | overview/triggers/ledger providers | UNSAFE — finding #2 |
| 4 | SQL binding parameters | parameters dict from LLM/tool | _build_bound_parameters; query uses :param only; _has_string_interpolation rejects % or f-string | Parameter binding | session.execute(text(query), bound_parameters) | SAFE (parameterized) |
| 5 | Skill env → process | skill.owlclaw_config.env | None (only key non-empty) | os.environ[key] = str(raw_value) | Process env | UNSAFE — finding #1 |

---

## Cross-Reference with Existing Specs

| Existing Spec | Overlap | Resolution |
|---------------|---------|------------|
| (none identified) | — | Findings are new; no duplicate in current specs. |

---

## Recommended Fix Order

| Order | Item | Severity | Rationale |
|-------|------|----------|------------|
| 1 | Restrict skill env keys (allowlist or OWLCLAW_SKILL_ prefix) | P1 | Reduces risk of malicious or misconfigured skills affecting process. |
| 2 | Document tenant_id as client-controlled and add guidance for multi-tenant (derive from auth) | P1 | Clarifies when current behavior is acceptable; unblocks multi-tenant design. |
| 3 | LRU for runtime caches (visible_tools, skills_context) | Low | Better cache behavior under churn. |
| 4 | Ledger session_factory access (formal API or config injection) | Low | Reduces coupling and fragility. |
| 5 | Sanitize/truncate LLM error message before appending to conversation | Low | Defense in depth if any provider ever leaks data in exceptions. |
| 6 | Engine create_engine exception mapping (narrow to connection/auth) | Low | Clearer error reporting. |
| 7 | Capabilities provider ConfigurationError handling (align with ledger/triggers) | Low | GET /capabilities no 500 when DB not configured. |
| 8 | health_status() avoid private _states/_configs (public API or doc) | Low | Reduce coupling to manager/server internals. |
| 9 | Ledger _background_writer flush batch to fallback on Exception | Low | Avoid losing in-memory batch on unexpected error. |
| 10 | Ledger _write_queue bounded or backpressure | Low | Cap memory under sustained load. |
| 11 | Webhook decode UTF-8 with 400 on invalid encoding | Low | Predictable 400 instead of 500. |

---

## Audit Completeness Checklist

- [x] Critical files in each dimension were read (3-pass method)
- [x] External data flows (tenant_id, payload, tool result, skill env, SQL params) were traced to sink
- [x] Error paths (timeout, exception in LLM/tool/ledger) were checked
- [x] Configuration (model, timeout, heartbeat config) was traced where used
- [x] Every finding has a root cause and concrete fix
- [x] Findings deduplicated and categorized
- [x] Specs generated for fix domains — audit-deep-remediation created and assigned
- [x] Recommended fix order established
- [x] Executive summary matches findings

---

## Phase 2 Extension (2026-03-05 — Continue 深度审计)

**Scope**: App lifecycle, Console REST/providers, governance visibility, DB-no-config consistency.

**Files additionally audited**: `app.py` (start/stop/create_agent_runtime/health_status), `web/api/ledger.py`, `web/api/agents.py`, `web/api/governance.py`, `web/api/capabilities.py`, `web/providers/ledger.py`, `web/providers/agents.py`, `web/providers/capabilities.py`, `web/providers/governance.py`, `web/providers/overview.py`, `triggers/api/handler.py`, `governance/visibility.py` (RunContext, filter).

**Result**: No new P0/P1. Two additional Low findings (7–8).

### Additional Low — Phase 2

| # | Category | Issue | Location | Fix |
|---|----------|-------|----------|-----|
| 7 | C.Robustness | DefaultCapabilitiesProvider._collect_capability_stats (and thus list_capabilities) does not catch ConfigurationError when calling get_engine(). Console GET /capabilities can return 500 when DB is not configured, unlike /ledger and /triggers which return empty. | `owlclaw/web/providers/capabilities.py:84-98` (_collect_capability_stats) | Wrap get_engine() and session usage in try/except ConfigurationError; on catch return empty stats dict so list_capabilities returns items with zero stats. |
| 8 | D.Architecture | app.py health_status() reads db_change_manager._states and api_trigger_server._configs (private attributes). Fragile if those classes change internal structure. | `owlclaw/app.py:1099-1100` (health_status) | Prefer public API (e.g. registered_channels_count(), registered_endpoints_count()) or document the coupling; alternatively expose read-only properties on the manager/server. |

### Phase 2 Data Flow / Positive Notes

- Ledger get_record_detail and agents get_agent_detail both scope by tenant_id in WHERE; no cross-tenant leak by record_id/agent_id when tenant is trusted.
- Governance provider catches broad Exception in get_budget_trend / get_circuit_breaker_states and returns []; overview _collect_metrics catches Exception and returns zeros; agents API route catches ConfigurationError. Only capabilities provider lacked ConfigurationError handling.
- API trigger parse_request_payload normalizes body/query/path; InvalidJSONPayloadError raised for invalid JSON; no raw injection into runtime without sanitizer (sanitizer is configurable on APITriggerServer).

---

## Phase 3 Extension (2026-03-05 — Continue 深度审计)

**Scope**: Ledger write path (queue, background writer, fallback), Hatchet integration (connect/timeout), Webhook HTTP gateway (body size, encoding).

**Files additionally audited**: `governance/ledger.py` (record_execution, _background_writer, _flush_batch, _write_to_fallback_log, _write_queue), `integrations/hatchet.py` (connect, run_task_now, schedule_task), `triggers/webhook/http/app.py` (receive_webhook, body size, decode).

**Result**: No new P0/P1. Three additional Low findings (9–11).

### Additional Low — Phase 3

| # | Category | Issue | Location | Fix |
|---|----------|-------|----------|-----|
| 9 | C.Robustness | In Ledger._background_writer, when a generic Exception is caught (other than TimeoutError/CancelledError), the current batch is only logged; it is not flushed to DB or to fallback. Records already pulled from the queue can be lost. | `owlclaw/governance/ledger.py:329-332` | On Exception, flush current batch to fallback (or retry once) before continuing the loop, so no in-memory batch is dropped. |
| 10 | C.Robustness | Ledger._write_queue is asyncio.Queue() with no maxsize; under sustained high load the queue can grow unbounded and increase memory pressure. | `owlclaw/governance/ledger.py:135` | Consider a bounded queue (maxsize) and backpressure (e.g. put with timeout, or drop-oldest policy) and document the limit. |
| 11 | C.Robustness | Webhook receive_webhook uses raw_body_bytes.decode("utf-8") without try/except; non-UTF-8 request body causes UnicodeDecodeError and 500. | `owlclaw/triggers/webhook/http/app.py:167` | Catch UnicodeDecodeError and return 400 with a clear message (e.g. "Request body must be UTF-8"). |

### Phase 3 Positive Notes

- Ledger record_execution validates tenant_id, agent_id, run_id, capability_name, task_type and normalizes strings; input_params/output_result type-checked. _flush_batch retries with backoff and falls back to file on final failure.
- Hatchet connect() uses timeout and cancels future on timeout; run_task_now/schedule_task log and re-raise.
- Webhook enforces max_content_length_bytes (header and after body read); rate limiter and validator in place.
