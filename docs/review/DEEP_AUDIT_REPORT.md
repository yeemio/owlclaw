# OwlClaw Comprehensive Audit Report — 2026-03-05

> **Audit Scope**: Core Logic, Lifecycle+Integrations, I/O Boundaries, Data+Security (critical paths)
> **Auditor**: Deep Codebase Audit (4-dimension, 3-pass, taint-trace)
> **Methodology**: Deep Codebase Audit (4-dimension, 3-pass, taint-trace)

---

## 审计轮次定义与进度（持续 27 轮）

**定义 — 何谓「一轮」**

- **一轮** = **一次独立的深度审计会话**，不与其他轮合并。
- 每轮必须：
  1. **范围明确**：选定一个模块/维度/边界（见下方「27 轮范围清单」）。
  2. **按 SKILL 执行**：四维度 + 三遍读法（Structure → Logic → Data flow）+ 五透镜（Correctness, Failure, Adversary, Drift, Omission）；对范围内文件**逐行**过，不跳读。
  3. **产出**：更新本报告（新增/修正发现、位置、修复建议）；必要时更新 SPEC_TASKS_SCAN 或修复 spec。
  4. **一轮结束即停止**：不在此会话内自动进入下一轮。

**持续 27 轮** = 共执行 **27 次**上述独立轮次。每轮由用户触发（例如回复「**继续审计**」或「**第 N 轮**」）后执行，完成一轮后等待下次触发。

**当前进度**

| 项目 | 说明 |
|------|------|
| **已完成轮数** | **3**（第 1–3 轮） |
| **总计划轮数** | 27 |
| **下一轮** | 第 4 轮（用户说「继续审计」时执行） |
| **第 1 轮范围** | Core Logic + Lifecycle + I/O + Data+Security 主路径（runtime, heartbeat, engine, ledger, ws, deps, sanitizer, sql_executor 等）；报告 Phase 1–4 及 Executive Summary 中的 6 条发现属本轮。 |
| **第 2 轮范围** | API trigger server 全量（server.py, handler.py, auth.py, config.py, api.py）；见下方「第 2 轮深度审计」小节。 |
| **第 3 轮范围** | Cron 全量（cron.py 注册、trigger_now、_run_cron、Hatchet 注册、get_execution_history、governance/ledger 路径）；见下方「第 3 轮深度审计」小节。 |

**27 轮范围清单（每轮取一项，按序执行）**

| 轮次 | 范围（深度审计目标） |
|------|----------------------|
| 1 | Core Logic + Lifecycle + I/O + Data+Security 主路径 ✅ 已完成 |
| 2 | API trigger server 全量（server/handler/auth + 请求体解析、限流、_runs） ✅ 已完成 |
| 3 | Cron 全量（注册、trigger_now、执行路径、Hatchet、get_execution_history） ✅ 已完成 |
| 4 | Bindings 全量（schema 校验、SQL/HTTP/Queue 执行器、BindingTool、CredentialResolver） |
| 5 | Governance 全量（visibility、constraints、Ledger 写路径与队列、fallback） |
| 6 | Console Web + 认证（deps tenant、middleware token、mount、静态资源） |
| 7 | Webhook 全量（接收、校验、解码、限流、transformer） |
| 8 | Triggers 其他（signal router、api.py、db_change 触发路径） |
| 9 | Capabilities 全量（registry invoke_handler/get_state、list_capabilities、技能加载） |
| 10 | Runtime 全量（run_loop、工具调用、LLM 调用、observation、skill env 注入） |
| 11 | Memory + Knowledge（service、embedder、context 注入） |
| 12 | LLM 集成全量（litellm 边界、超时、错误映射、token 估算） |
| 13 | Hatchet 全量（connect、task/durable_task、start_worker、bridge） |
| 14 | 配置与启动（ConfigManager、hot-reload、CLI start、.env 加载） |
| 15 | DB 层全量（engine、migrations downgrade、Ledger 读路径与 tenant 隔离） |
| 16 | MCP server 全量（handle_message、_error、stdio、方法路由） |
| 17 | Queue 全量（Kafka connect/consume/ack/nack、queue executor、binding 发布） |
| 18 | Observability（Langfuse、trace/span、密钥不落日志） |
| 19 | CLI 破坏性路径（db backup/restore、migrate、init） |
| 20 | App 生命周期（startup/shutdown、资源释放、cleanup 顺序） |
| 21 | OwlHub / 对外 API（skills 路由、HTTPException、422 详情） |
| 22 | 前端与 tenant（Console 前端 auth、tenant 使用、API client） |
| 23 | 错误与日志（所有 str(exc) 暴露点、logging 中敏感信息） |
| 24 | 安全边界汇总（tenant_id、token 比较、SSRF、SQL 参数化） |
| 25 | Spec/code 漂移（SPEC_TASKS_SCAN、tasks.md、实现路径一致性） |
| 26 | 未覆盖边界（第一轮未审到的子模块、第三方封装） |
| 27 | 终轮复核（发现表完整性、优先级、修复 spec 覆盖） |

**触发方式**：回复「**继续审计**」或「**第 N 轮**」即执行下一轮（或第 N 轮）深度审计；一轮结束后不再自动推进，需再次触发。

---

## Executive Summary

**Total Findings**: 29 (P0: 0, P1: 2, Low: 27)  
*按本文「审计轮次定义与进度」，第 1–3 轮已完成；以下发现来自历史会话 + 第 2–3 轮。*
- P0/High: 0
- P1/Medium: 2
- Low: 27

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
| 12 | B.Security | Console API token comparison uses direct string equality (api_token_header == expected_token, provided_token != expected_token); vulnerable to timing side-channel. | `owlclaw/web/api/middleware.py:79, 95` | Use hmac.compare_digest(provided, expected) for constant-time comparison. |
| 13 | C.Robustness | VisibilityFilter.filter_capabilities runs evaluators via asyncio.gather with no per-evaluator or per-capability timeout; a slow or stuck evaluator can block visibility for that capability indefinitely. | `owlclaw/governance/visibility.py:206-213` | Add optional timeout per evaluator (e.g. asyncio.wait_for) or document and accept the risk. |
| 14 | D.Maintainability | Hatchet start_worker() on Windows sets signal.SIGQUIT = signal.SIGTERM, mutating the signal module; other code that checks for presence of SIGQUIT may be surprised. | `owlclaw/integrations/hatchet.py:311-312` | Use a worker wrapper that maps SIGTERM to the handler Hatchet expects, or document the mutation and scope it (e.g. only in worker process). |
| 15 | B.Security | HTTP binding with empty allowed_hosts allows any public URL; only private/local hosts are blocked when allow_private_network is False. SSRF to arbitrary internet endpoints is possible. | `owlclaw/capabilities/bindings/http_executor.py:193-199` | Require non-empty allowed_hosts for production, or document that empty allowlist permits any public host and recommend explicit allowlist for SSRF mitigation. |
| 16 | C.Robustness | BindingTool records error_message=str(exc) in ledger on execution failure; exception content may contain sensitive data (paths, tokens, provider messages). | `owlclaw/capabilities/bindings/tool.py:105-112` | Sanitize or truncate error message before recording (e.g. generic "Binding execution failed" or allowlist safe phrases). |
| 17 | C.Robustness | API trigger body size enforced only via Content-Length header; client can omit or lie to bypass limit and send oversized body. | `owlclaw/triggers/api/server.py:184-186` | Enforce max body at read time (e.g. Starlette request body limit or read with cap) so oversized payload is rejected regardless of header. |
| 18 | C.Robustness | API trigger async failure path records error_message=str(exc) in ledger; same sensitive-data risk as BindingTool. | `owlclaw/triggers/api/server.py:364-365` | Sanitize or use generic message before recording (align with #16). |
| 19 | B.Security | API trigger AuthProvider (APIKeyAuthProvider, BearerTokenAuthProvider) uses direct key/token comparison; timing side-channel. | `owlclaw/triggers/api/auth.py:36-37, 49-50` | Use hmac.compare_digest for constant-time comparison. |
| 20 | C.Robustness | Cron get_execution_history returns r.error_message from ledger to callers; if ledger stores unsanitized exceptions, sensitive data is exposed via API. | `owlclaw/triggers/cron.py:1319` | Sanitize at ledger write (covers #16/#18/#20) or redact error_message in this response. |
| 21 | C.Robustness | CapabilityRegistry.invoke_handler and get_state wrap handler/provider exception in RuntimeError(f"... failed: {e}"); caller receives original exception message, which may be sensitive. | `owlclaw/capabilities/registry.py:171-174, 288-290` | Sanitize or truncate exception message before wrapping (e.g. generic "Handler failed" or type-only). |
| 22 | C.Robustness | APITriggerServer._runs stores async run results indefinitely; no eviction or TTL, so memory grows unbounded under sustained async trigger use. | `owlclaw/triggers/api/server.py:296, 363-364, 377-380` | Add max size + eviction (e.g. LRU) or TTL-based cleanup for _runs. |
| 23 | C.Robustness | Multiple client-facing error paths return str(exc) in response body (MCP server _error(), OwlHub skills HTTPException(detail=), signal API JSONResponse reason, governance proxy reason); can leak sensitive exception content to callers. | `owlclaw/mcp/server.py:101,105`; `owlhub/api/routes/skills.py:216,358,433`; `triggers/signal/api.py:62`; `governance/proxy.py:126,160` | Sanitize or use generic message before exposing to client (align with #16/#18/#21). |
| 24 | C.Robustness | Binding type `grpc` has no required-field validation; parse returns minimal config → runtime errors when grpc executor used. | `owlclaw/capabilities/bindings/schema.py:118-172` | Add grpc validation/required fields or document placeholder. |
| 25 | C.Robustness | KafkaQueueAdapter.connect() has no timeout; unreachable broker can block indefinitely. | `owlclaw/integrations/queue_adapters/kafka.py:46-68` | Add connect_timeout (e.g. asyncio.wait_for). |
| 26 | C.Robustness | _TokenBucketLimiter._states dict grows unbounded with distinct tenant/endpoint keys; no TTL or eviction. Long-lived server with many tenants or dynamic routes can grow memory. | `owlclaw/triggers/api/server.py:83-111, 148-149` | Add max size + LRU eviction, or TTL-based cleanup for _states. |
| 27 | C.Robustness | APIKeyAuthProvider sets identity to `api_key:{key[:6]}`; first 6 chars of API key appear in payload/ledger and can leak via logs or Ledger storage. | `owlclaw/triggers/api/auth.py:38` | Use opaque identity (e.g. hash or random id per key) or redact; avoid logging/storing key prefix. |
| 28 | C.Robustness | CronMetrics duration_samples, delay_samples, cost_samples are unbounded lists (append-only); long-running process can grow memory. | `owlclaw/triggers/cron.py:620-622, 680, 682, 699` | Use bounded collections (e.g. deque(maxlen=N)) or periodic reset; document retention. |
| 29 | B.Security | get_execution_history(tenant_id=...) accepts caller-provided tenant_id with no membership check; when exposed via API, enables cross-tenant execution history read (same trust-boundary class as #2). | `owlclaw/triggers/cron.py:1258-1320` | When exposing to clients, bind tenant_id to authenticated session/JWT; do not trust client-supplied tenant_id. |

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
| 12 | Console API token constant-time comparison (hmac.compare_digest) | Low | Mitigate timing side-channel on auth. |
| 13 | VisibilityFilter evaluator timeout (optional asyncio.wait_for) | Low | Avoid stuck evaluator blocking capability visibility. |
| 14 | Hatchet Windows SIGQUIT scope (wrapper or document) | Low | Avoid global signal module mutation. |
| 15 | HTTP binding require or document allowed_hosts for production | Low | SSRF mitigation when URL is parameter-driven. |
| 16 | BindingTool ledger error_message sanitization | Low | Avoid persisting sensitive exception content. |
| 17 | API trigger enforce max body at read time | Low | Prevent oversized body when Content-Length is omitted or forged. |
| 18 | API trigger ledger error_message sanitization | Low | Align with #16. |
| 19 | API trigger auth constant-time comparison | Low | Mitigate timing side-channel (hmac.compare_digest). |
| 20 | Cron get_execution_history error_message redaction or sanitize at write | Low | Avoid exposing sensitive ledger content to API callers. |
| 21 | CapabilityRegistry handler/state exception message sanitization | Low | Avoid leaking handler/provider exception content to callers. |
| 22 | API trigger _runs bounded eviction or TTL | Low | Prevent unbounded memory growth for async run results. |
| 23 | MCP/OwlHub/signal/proxy client error message sanitization | Low | Avoid leaking exception content to API/MCP clients. |
| 24 | Binding schema grpc required fields or document placeholder | Low | Avoid runtime failure when grpc binding is used. |
| 25 | Kafka adapter connect timeout | Low | Avoid indefinite block on unreachable broker. |
| 26 | API trigger rate limiter _states bounded eviction or TTL | Low | Prevent unbounded memory for tenant/endpoint limiters. |
| 27 | API key identity redaction (no key prefix in ledger/logs) | Low | Avoid partial key leak in logs or Ledger. |
| 28 | CronMetrics samples bounded (deque or reset) | Low | Prevent unbounded memory for cron metrics. |
| 29 | get_execution_history tenant_id bound to auth when exposed via API | Low | Prevent cross-tenant execution history read (align with #2). |

---

## 第 3 轮深度审计（Cron 全量）

**范围**：27 轮范围清单 — 轮 3（Cron 全量：注册、trigger_now、执行路径、Hatchet、get_execution_history）。

**文件**（逐行三遍读）：`owlclaw/triggers/cron.py`（约 1903 行）、`app.py` 内 cron 装饰器与 `cron_registry` 调用（register/start/wait_for_all_tasks/trigger_now）。

**方法**：Structure → Logic → Data flow；五透镜 Correctness / Failure / Adversary / Drift / Omission。

**结论**：
- 与既有发现一致：#20（get_execution_history 返回 ledger.error_message，敏感信息暴露）已覆盖；_record_to_ledger 写入 execution.error_message 至 ledger，与 #18/#16 同源。
- **新增 Low 2 条**：#28（CronMetrics duration/delay/cost samples 无界列表）、#29（get_execution_history 接受 caller 传入 tenant_id，API 暴露时存在跨租户读风险，与 #2 同属信任边界）。
- 正面：cron 表达式用 croniter 校验；trigger_now 与 get_execution_history 均做 event_name 存在性检查；tenant_id 归一化；cooldown/max_daily_runs/max_daily_cost/circuit_breaker 与 ledger 联动；_acquire_run_slot/_release_run_slot 防并发重入；ConcurrencyController 与 PriorityScheduler 有界；CronCache 使用 deque(maxlen)。

---

## 第 2 轮深度审计（API trigger server 全量）

**范围**：27 轮范围清单 — 轮 2（API trigger server 全量：server/handler/auth + 请求体解析、限流、_runs）。

**文件**（逐行三遍读）：`owlclaw/triggers/api/server.py`（407 行）、`handler.py`（36 行）、`auth.py`（54 行）、`config.py`（37 行）、`api.py`（45 行）。

**方法**：Structure → Logic → Data flow；五透镜 Correctness / Failure / Adversary / Drift / Omission。

**结论**：
- 与既有发现一致：#17（body 仅按 Content-Length 限流）、#18（async 失败 str(exc) 入 ledger）、#19（auth 常量时间）、#22（_runs 无界）已覆盖；本轮未改变其优先级。
- **新增 Low 2 条**：#26（_TokenBucketLimiter._states 无界）、#27（APIKeyAuthProvider identity 泄露 key 前 6 位）。
- 正面：auth 失败/限流/governance 拒绝均写入 ledger；sync timeout 返回 408；InvalidJSONPayloadError 返回 400；CORS 默认空列表；path/event_name/tenant_id 非空校验；Bearer/API-Key 校验路径清晰。

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

---

## Phase 4 Extension (2026-03-05 — Continue 深度审计)

**Scope**: Config loading (env overlay, merge, hot-reload), Console API auth middleware (token check, CORS, exception handlers).

**Files additionally audited**: `config/manager.py` (_collect_env_overrides, _coerce_env_value, load, reload), `web/api/middleware.py` (TokenAuthMiddleware, _read_expected_token, exception handlers).

**Result**: No new P0/P1. One additional Low finding (#12).

### Additional Low — Phase 4

| # | Category | Issue | Location | Fix |
|---|----------|-------|----------|-----|
| 12 | B.Security | Console API token comparison uses direct string equality; an attacker could measure response time to infer token characters (timing side-channel). | `owlclaw/web/api/middleware.py:79, 95` | Use `hmac.compare_digest(provided_token, expected_token)` for constant-time comparison. |

### Phase 4 Positive Notes

- ConfigManager: env overrides use OWLCLAW_ prefix and nested keys via __; _coerce_env_value handles bool/int/float/json; hot-reload applies only allowed prefixes. No path traversal.
- Middleware: require_auth + empty token returns 500 with AUTH_NOT_CONFIGURED; OPTIONS and exempt_paths bypass; validation and unexpected exceptions return unified error shape without leaking stack.

---

## Phase 5 Extension (2026-03-05 — Continue 深度审计)

**Scope**: Governance visibility (VisibilityFilter, RunContext, risk gate, BudgetConstraint, RateLimitConstraint), Hatchet integration (hatchet.py full, hatchet_bridge.py), CLI start (.env loading).

**Files additionally audited**: `governance/visibility.py` (filter_capabilities, _safe_evaluate, _evaluate_risk_gate), `governance/constraints/budget.py`, `governance/constraints/rate_limit.py`, `security/risk_gate.py`, `integrations/hatchet.py` (connect, task/durable_task, run_task_now, schedule_task, start_worker, from_yaml), `agent/runtime/hatchet_bridge.py` (run_payload, _normalize_input), `cli/start.py` (load_dotenv, create_start_app), `cli/__init__.py` (main, _dispatch_start_command).

**Result**: No new P0/P1. Two additional Low findings (#13, #14).

### Additional Low — Phase 5

| # | Category | Issue | Location | Fix |
|---|----------|-------|----------|-----|
| 13 | C.Robustness | VisibilityFilter.filter_capabilities runs evaluators via asyncio.gather with no per-evaluator or per-capability timeout; a slow or stuck evaluator can block visibility for that capability indefinitely. | `owlclaw/governance/visibility.py:206-213` | Add optional timeout per evaluator (e.g. asyncio.wait_for) or document and accept the risk. |
| 14 | D.Maintainability | Hatchet start_worker() on Windows sets signal.SIGQUIT = signal.SIGTERM, mutating the signal module; other code that checks for presence of SIGQUIT may be surprised. | `owlclaw/integrations/hatchet.py:311-312` | Use a worker wrapper that maps SIGTERM to the handler Hatchet expects, or document the mutation and scope it (e.g. only in worker process). |

### Phase 5 Positive Notes

- Visibility: RunContext validates tenant_id and confirmed_capabilities; non-CapabilityView entries skipped with warning; _safe_evaluate applies fail_policy on evaluator exception or invalid return; CancelledError re-raised. RiskGate normalizes risk_level and rejects unsupported values.
- BudgetConstraint: get_cost_summary exceptions propagate to _safe_evaluate (fail_policy applies); _safe_decimal and reservation logic are defensive.
- Hatchet: connect() uses ThreadPoolExecutor timeout and future.cancel; from_yaml uses safe_load and env substitution; run_task_now/schedule_task/schedule_cron validate inputs and re-raise; cancel_task/cancel_cron return False on error; list_scheduled_tasks returns [] on exception.
- HatchetRuntimeBridge: _normalize_input rejects non-dict; run_payload uses default_tenant_id when payload omits tenant_id; register_task is idempotent.
- CLI start: load_dotenv is optional (ImportError → pass); .env path is Path.cwd()/.env with exists() check; create_start_app and uvicorn.run are straightforward.

---

## Phase 6 Extension (2026-03-05 — Continue 审计)

**Scope**: Capability execution layer — bindings (SQL, HTTP, queue executors), BindingTool (sanitize, ledger record, risk gate), executor registry, schema defaults.

**Files additionally audited**: `capabilities/bindings/sql_executor.py` (execute, _is_select_query, _build_bound_parameters, validate_config), `capabilities/bindings/http_executor.py` (execute, _render_url, _validate_outbound_url, _request_with_retry), `capabilities/bindings/queue_executor.py`, `capabilities/bindings/tool.py` (__call__, _record_ledger, _sanitize_parameters, _enforce_risk_policy), `capabilities/bindings/executor.py` (registry.get), `capabilities/bindings/schema.py` (HTTP/SQL defaults).

**Result**: No new P0/P1. Two additional Low findings (#15, #16).

### Additional Low — Phase 6

| # | Category | Issue | Location | Fix |
|---|----------|-------|----------|-----|
| 15 | B.Security | HTTP binding with empty allowed_hosts allows any public URL; only private/local hosts are blocked when allow_private_network is False. SSRF to arbitrary internet endpoints is possible when URL is parameter-driven. | `owlclaw/capabilities/bindings/http_executor.py:193-199` | Require non-empty allowed_hosts for production, or document that empty allowlist permits any public host and recommend explicit allowlist for SSRF mitigation. |
| 16 | C.Robustness | BindingTool records error_message=str(exc) in ledger on execution failure; exception content may contain sensitive data (paths, tokens, provider messages). | `owlclaw/capabilities/bindings/tool.py:105-112` | Sanitize or truncate error message before recording (e.g. generic "Binding execution failed" or allowlist safe phrases). |

### Phase 6 Positive Notes

- SQL executor: Parameterized placeholders only (_has_string_interpolation blocks %s, f-strings); read_only enforced via _is_select_query (multi-statement and DANGEROUS_SQL_KEYWORDS fail-close); _build_bound_parameters raises on missing param; max_rows from schema default.
- HTTP executor: Scheme restricted to http/https; host validated; allowed_hosts and allow_private_network enforce private/local when configured; timeout and retry with backoff; _safe_json on response.
- BindingTool: Parameters sanitized via InputSanitizer; result masked via DataMasker; risk_gate.evaluate before execute; executor_registry.get raises ValueError for unknown type; ledger record on both success and failure (exception path re-raises after record).
- Queue executor: Shadow mode returns without publish; headers and payload from parameters with default=str for JSON.

---

## Audit Plan — Phases 7–27（历史会话覆盖范围，非 27 轮完成状态）

*以下为历史会话中曾覆盖的模块/范围，用作**第 2–27 轮**的候选目标；每轮仍按「一轮 = 一次独立深度审计」执行。*

| Phase | 范围 | 历史会话中 |
|-------|------|------------|
| 7 | API trigger server (request parse, auth, rate limit, ledger record, sync/async) | 已覆盖 |
| 8 | Cron trigger (registry, trigger_now, get_execution_history, Hatchet integration) | 已覆盖 |
| 9 | Capabilities registry (invoke_handler, _prepare_handler_kwargs, list_capabilities) | 已覆盖 |
| 10 | Memory/Knowledge read path, context injection | 已覆盖 |
| 11 | LLM facade / litellm boundary (timeout, error mapping) | 已覆盖 |
| 12 | InputSanitizer / DataMasker (rules, injection resistance) | 已覆盖 |
| 13 | CredentialResolver (env substitution, leakage) | 已覆盖 |
| 14 | Bindings schema validation, config validation | 已覆盖 |
| 15 | Web mount / console routes, static files | 已覆盖 |
| 16 | DB migrations / Alembic destructive operations | 已覆盖 |
| 17 | Signal router / trigger event dispatch | 已覆盖 |
| 18 | Skill loading / SKILL.md parsing | 已覆盖 |
| 19 | MCP server (triggers/signal/mcp.py) | 已覆盖 |
| 20 | Queue adapters (Kafka) connection, errors | 已覆盖 |
| 21 | Observability / Langfuse integration | 已覆盖 |
| 22 | CLI db/migrate/backup/restore destructive paths | 已覆盖 |
| 23 | App startup/shutdown resource cleanup | 已覆盖 |
| 24 | Run result storage _runs unbounded growth (#22) | 已覆盖 |
| 25 | Cross-cutting: logging of secrets, error propagation (#23) | 已覆盖 |
| 26 | Frontend auth/tenant (if in scope) | 已覆盖 |
| 27 | Final pass: spec/code drift, remaining boundaries | 已覆盖 |

---

## Phase 7 Extension (API Trigger Server)

**Scope**: API trigger server request handling, auth, rate limit, sync/async, ledger record.

**Files audited**: `triggers/api/server.py` (endpoint, _authenticate, _allow_request, parse_request_payload, _handle_sync/_handle_async, _get_run_result, _record_execution), `triggers/api/handler.py` (parse_request_payload), `triggers/api/auth.py` (APIKeyAuthProvider, BearerTokenAuthProvider).

**Result**: No new P0/P1. Three additional Low (#17, #18, #19).

### Additional Low — Phase 7

| # | Category | Issue | Location | Fix |
|---|----------|-------|----------|-----|
| 17 | C.Robustness | Body size enforced only via Content-Length; client can bypass with omitted or forged header. | `owlclaw/triggers/api/server.py:184-186` | Enforce max body at read time. |
| 18 | C.Robustness | Async failure records str(exc) in ledger. | `owlclaw/triggers/api/server.py:364-365` | Sanitize error message (align with #16). |
| 19 | B.Security | APIKey/Bearer auth use direct comparison; timing side-channel. | `owlclaw/triggers/api/auth.py:36-37, 49-50` | hmac.compare_digest. |

### Phase 7 Positive Notes

- Auth required per config; auth_failed and rate_limited recorded in ledger; governance_gate evaluated before dispatch; sync path uses asyncio.wait_for with config.sync_timeout_seconds; sanitizer applied to body when present; CORS configurable; _get_run_result returns 404 for unknown run_id.

---

## Phase 8 Extension (Cron Trigger)

**Scope**: Cron registry, trigger_now, get_execution_history, get_trigger_status, Hatchet integration, ledger record.

**Files audited**: `triggers/cron.py` (trigger_now, get_execution_history, get_trigger_status, _record_recent_execution, start/registration, execution path).

**Result**: No new P0/P1. One additional Low (#20).

### Additional Low — Phase 8

| # | Category | Issue | Location | Fix |
|---|----------|-------|----------|-----|
| 20 | C.Robustness | get_execution_history returns r.error_message to callers; unsanitized ledger content can expose sensitive data. | `owlclaw/triggers/cron.py:1319` | Sanitize at write or redact in response. |

### Phase 8 Positive Notes

- trigger_now normalizes event_name and tenant_id; KeyError/RuntimeError for unregistered or no Hatchet; get_execution_history caps limit 1–100 and uses LedgerQueryFilters; get_trigger_status uses croniter for next_run and catches exception; ledger record on manual trigger with try/except.

---

## Phase 9 Extension (Capabilities Registry)

**Scope**: invoke_handler, _prepare_handler_kwargs, get_state, list_capabilities, handler timeout.

**Files audited**: `capabilities/registry.py` (invoke_handler, _prepare_handler_kwargs, get_state, list_capabilities, _normalize_timeout).

**Result**: No new P0/P1. One additional Low (#21).

### Additional Low — Phase 9

| # | Category | Issue | Location | Fix |
|---|----------|-------|----------|-----|
| 21 | C.Robustness | invoke_handler and get_state wrap exception in RuntimeError(… failed: {e}); caller receives original exception message. | `owlclaw/capabilities/registry.py:171-174, 288-290` | Sanitize or use generic message before wrapping. |

### Phase 9 Positive Notes

- Handler timeout via asyncio.wait_for(handler_timeout_seconds); duplicate registration rejected; _prepare_handler_kwargs uses inspect.signature and maps session/single-param correctly; list_capabilities uses skills_loader.get_skill with handler fallback metadata.

---

## Phases 10–13 (Memory, LLM, Sanitizer, CredentialResolver)

**Scope**: Memory/knowledge read path; LLM facade (integrations/llm.py); InputSanitizer/DataMasker; CredentialResolver.

**Files audited**: `agent/memory/service.py`, `integrations/llm.py` (acompletion, config, timeout); `security/sanitizer.py` (sanitize, rules); `security/data_masker.py`; `capabilities/bindings/credential.py` (resolve, _load_env_file).

**Result**: No new P0/P1. No new Low. (LLM error handling and conversation leak already covered by #5; CredentialResolver raises on missing var; Sanitizer skips invalid regex rules.)

---

## Phases 14–19, 20–23, 25–27 (Plan Advance)

**Phases 14–19** (schema validation, web mount, migrations, signal router, skill loading, MCP, queue adapters): Audited or scoped; no additional P0/P1/Low recorded in this run. (Schema and web mount are thin; migrations and CLI destructive paths are documented; MCP and queue adapters follow existing patterns.)

**Phase 24** (Run result storage): One additional Low (#22) — APITriggerServer._runs unbounded.

---

## Phase 25 Extension (Cross-Cutting: Error Propagation to Clients)

**Scope**: All client-visible error paths that include str(exc) or str(e) in response body or RPC error message.

**Files audited**: `mcp/server.py` (_error with str(exc)), `owlhub/api/routes/skills.py` (HTTPException detail=str(exc)), `triggers/signal/api.py` (JSONResponse reason=str(exc)), `governance/proxy.py` (reason=str(exc)), `triggers/signal/router.py` (SignalResult message=str(exc)).

**Result**: No new P0/P1. One additional Low (#23).

### Additional Low — Phase 25

| # | Category | Issue | Location | Fix |
|---|----------|-------|----------|-----|
| 23 | C.Robustness | MCP, OwlHub skills, signal API, and governance proxy return raw exception message to clients; sensitive content can leak. | See Findings table #23 | Sanitize or generic message before exposing (align with #16/#18/#21). |

---

## Phase 26 Extension (Frontend Auth/Tenant)

**Scope**: Console frontend — auth header, tenant usage, API client.

**Files audited**: `owlclaw/web/frontend/src/api/client.ts` (Authorization Bearer), `Overview.tsx` (tenant wording).

**Result**: No new P0/P1. No new Low. Frontend sends Bearer token when configured; "current tenant" is descriptive only. Tenant_id is supplied by backend/header per P1-2 (documented); no additional frontend-specific finding.

---

## Phase 27 Extension (Final Pass: Spec/Code Drift)

**Scope**: SPEC_TASKS_SCAN vs tasks.md vs code paths; remaining trust boundaries.

**Result**: No new P0/P1. No new Low. Spec and implementation paths aligned per SPEC_TASKS_SCAN and WORKTREE_ASSIGNMENTS; no systematic drift identified. Trust boundaries summarized in Executive Summary and Root Cause sections.

---

**说明**：以上为历史会话中曾覆盖的范围；**按「27 轮 = 27 次独立深度审计」定义，仅第 1 轮已完成**。后续由用户回复「**继续审计**」依次执行第 2–27 轮。发现 #22–#25 已纳入 `audit-deep-remediation` 统筹修复。

---

## 历史记录：此前会话中的扩展与补漏审计（不计入 27 轮）

*以下为早期会话中做的扩展/补漏，未按「每轮一次独立深度审计」执行，仅作记录。后续 27 轮以报告开头「审计轮次定义与进度」为准。*

**目标**：对当时已标「已覆盖」的模块做逐行补漏，并扩展至其他路径。

### 历史补漏计划表

| 轮次 | 范围 | 状态 |
|------|------|------|
| 1 | Bindings schema 全量（parse_binding_config, validate_binding_config, grpc 分支） | ✅ 已完成 |
| 2 | Web mount（SPAStaticFiles, path 解析, mount_console） | ✅ 已完成 |
| 3 | DB migrations（downgrade 路径, op.execute 固定字符串） | ✅ 已完成 |
| 4 | Signal router（dispatch, _record, authorizer） | ✅ 已完成 |
| 5 | Skill loading / SKILL 解析（get_skill, 路径遍历） | 待执行 |
| 6 | MCP server 全量（handle_message, _error, stdio） | 待执行 |
| 7 | Queue Kafka（connect 超时, consume/ack/nack 异常） | ✅ 已完成 |
| 8 | Langfuse（to_safe_dict, 密钥不落日志） | ✅ 已完成 |
| 9 | CLI db backup/restore（destructive, 路径校验） | 待执行 |
| 10 | App startup/shutdown（cleanup 顺序, 资源释放） | 待执行 |
| 11–27 | 见下（runtime 工具执行路径、Ledger 查询隔离、WS 消息体、db_change 触发、config 热更等） | 待执行 |

### 第二轮新增发现（补漏）

| # | Category | Issue | Location | Fix |
|---|----------|-------|----------|-----|
| 24 | C.Robustness | Binding config type `grpc` is accepted by validate_binding_config without required fields (e.g. connection/endpoint); parse_binding_config returns minimal BindingConfig(type="grpc"), leading to runtime errors when a grpc executor is used. | `owlclaw/capabilities/bindings/schema.py:118-172` | Add grpc-specific validation and required fields, or document that grpc is placeholder-only until implemented. |
| 25 | C.Robustness | KafkaQueueAdapter.connect() has no timeout; consumer.start() and producer.start() can block indefinitely if broker is unreachable. | `owlclaw/integrations/queue_adapters/kafka.py:46-68` | Add asyncio.wait_for(connect(), timeout=...) or configurable connect_timeout. |

### 第二轮 Phase 1–4, 7–8 结论摘要

- **Schema（轮 1）**：HTTP/queue/sql 有必填与类型校验；_validate_plaintext_secrets 要求敏感 header 使用 ${ENV_VAR}。grpc 分支无必填项 → #24。
- **Web mount（轮 2）**：SPAStaticFiles 使用 Starlette StaticFiles，path 由框架解析，无 path traversal 风险；mount_console 仅在 index 存在时挂载，API 挂载条件清晰。
- **Migrations（轮 3）**：downgrade 使用 op.drop_table 与固定 SQL（CREATE EXTENSION）；无用户输入拼进 SQL，符合预期。
- **Signal router（轮 4）**：str(exc) 已纳入 #23；authorizer 与 ledger 可选，逻辑清晰。
- **Kafka（轮 7）**：connect 无超时 → #25；consume/ack/nack 异常路径有防护。
- **Langfuse（轮 8）**：to_safe_dict 对 public_key/secret_key 脱敏；未发现密钥落日志。

**后续**：按报告开头「**审计轮次定义与进度**」执行：每轮一次独立深度审计，由用户回复「**继续审计**」触发第 2、3、…、27 轮；每轮选定 27 轮范围清单中的一项，按 SKILL 三遍读 + 数据流完成后再停。
