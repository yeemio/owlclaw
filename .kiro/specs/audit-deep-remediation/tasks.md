# audit-deep-remediation — 任务清单

> **Authority**: `docs/review/DEEP_AUDIT_REPORT.md` + `docs/review/DEEP_AUDIT_EXECUTION_CHECKLIST.md` + `.kiro/specs/audit-deep-remediation/requirements.md` + design.md

---

## Phase 15 已完成项（15/15）

### codex-work 负责

| # | Task | 验收 | 状态 |
|---|------|------|------|
| 1 | **P1-1** 在 `runtime.py` 的 `_inject_skill_env_for_run` 中仅注入 key 以 `OWLCLAW_SKILL_` 开头的 env；其余忽略并打 debug 日志 | 修改后运行带 env 的 skill，非前缀 key 不进入 os.environ；有单测或集成断言 | [x] |
| 2 | **Low-3** 将 `_visible_tools_cache` 与 skills 上下文缓存改为 LRU（如 cachetools.LRUCache 或 OrderedDict 按访问） | 缓存满时逐出最近最少使用项；现有缓存相关测试通过 | [x] |
| 3 | **Low-5** 在 LLM 异常分支中不再向消息追加 `str(exc)`，改为固定文案或安全简短描述 | grep 确认无 `str(exc)` 进 assistant content；异常路径有测试 | [x] |
| 4 | **Low-4a** 在 Ledger 上暴露 `get_readonly_session_factory()`（或等价）公开 API，内部复用现有 _session_factory | 方法存在且可返回只读用 session 工厂；不暴露 _session_factory | [x] |
| 11 | **Low-8** 在 `app.py` 的 `health_status()` 中避免直接读 `_states`/`_configs`：改为 manager/server 的公开 API 或只读属性，或文档明确该耦合 | 无私有属性访问或文档注明；health 相关测试通过 | [x] |
| 12 | **Low-9** 在 Ledger._background_writer 的 except Exception 分支中，将当前 batch 写入 fallback 再继续循环，避免丢失已出队记录 | 异常路径有单测或集成验证；batch 不丢 | [x] |
| 13 | **Low-10** Ledger._write_queue 设 maxsize 或实现背压（put 超时/丢弃策略），并文档化上限 | 队列有界或文档明确；压力测试可选 | [x] |
| 15 | **Low-12** 在 Console API TokenAuthMiddleware 中用 hmac.compare_digest 做 token 常量时间比较 | grep 确认无直接 !=/== 比较 token；有单测或手验 | [x] |

### codex-gpt-work 负责

| # | Task | 验收 | 状态 |
|---|------|------|------|
| 5 | **P1-2** 在 docs 中新增/更新「Console 多租户与 tenant_id」：当前行为、适用场景、多租户须从认证推导 | 文档存在且包含上述三点 | [x] |
| 6 | **Low-4b** 在 HeartbeatChecker 中改为使用 Ledger 的 `get_readonly_session_factory()`，移除对 `_session_factory` 的 getattr | grep 确认 heartbeat 无 _session_factory；heartbeat 相关测试通过 | [x] |
| 7 | **Low-6** 在 `db/engine.py` 的 `create_engine` 中收窄异常映射：仅连接/认证类映射为 Database*Error；其余保留或 EngineError | 非连接类异常不再被误报为连接错误；有单测或集成验证 | [x] |
| 10 | **Low-7** 在 `web/providers/capabilities.py` 的 `_collect_capability_stats` 中捕获 ConfigurationError，无 DB 时返回空 stats（与 ledger/triggers 一致，GET /capabilities 不 500） | 无 DB 时 GET /capabilities 返回 200 + items（零统计）；有单测或手验 | [x] |
| 14 | **Low-11** 在 webhook receive_webhook 中对 raw_body_bytes.decode("utf-8") 做 try/except UnicodeDecodeError，返回 400 及明确提示 | 非 UTF-8 body 返回 400 而非 500；有单测或手验 | [x] |
| 16 | **Low-13** 在 VisibilityFilter evaluator 路径增加 timeout 或明确文档边界，避免单个 evaluator 长时间阻塞 capability 过滤 | 有测试、手验或文档结论；不会无限等待单个 evaluator | [x] |
| 17 | **Low-14** 收敛 Hatchet Windows SIGQUIT 兼容逻辑的作用域，避免全局 `signal` 模块副作用 | 代码或文档说明明确；Windows 兼容逻辑边界清晰 | [x] |

---

## 可选（同一 spec 内可后做）

| # | Task | 验收 | 状态 |
|---|------|------|------|
| 8 | P1-1 扩展：支持运行时 `skill_env_allowlist` 配置，允许无前缀的 key | 配置项生效且文档或注释说明 | [ ] |
| 9 | P1-2 实现：deps.get_tenant_id 从请求上下文/认证读取 tenant（若已有 auth 中间件） | 有则实现并测试；无则跳过 | [ ] |

---

## 执行顺序建议

1. Phase 15 首轮收口已完成：D1-D14 + P1-2 共 15/15 已通过审校并合入主线。
2. 后续若继续深度审计修复，优先从 D15-D29 批次开始，再处理 D30-D44 backlog。
3. 统筹阶段根据共享文件边界重新分配下一批，不复用本轮已完成的“待审”顺序。

---

## Backlog 审校结果（D15-D29，2026-03-06 审校完成）

> 来源：`docs/review/DEEP_AUDIT_REPORT.md` 第 4-6 轮扩展项。审校确认所有发现均为有效代码问题。

| 报告# | 简述 | 位置 | 审校状态 |
|-------|------|------|----------|
| #15 | HTTP binding 空 `allowed_hosts` SSRF 边界 | `capabilities/bindings/http_executor.py:193-199` | ✅ 有效 - 允许任意公网 URL |
| #16 | BindingTool ledger 错误脱敏 | `capabilities/bindings/tool.py:113` | ✅ 有效 - `error_message=str(exc)` 未脱敏 |
| #17 | API trigger body 读取上限按实际字节强制 | `triggers/api/server.py:186-189` | ✅ 有效 - 只检查 Content-Length header |
| #18 | API trigger ledger 错误脱敏 | `triggers/api/server.py:364` | ✅ 有效 - `str(exc)` 未脱敏 |
| #19 | API trigger 认证常量时间比较 | `triggers/api/auth.py:37,53` | ✅ 有效 - 使用 `in` 非常量时间 |
| #20 | Cron get_execution_history 错误脱敏 | `triggers/cron.py:1319` | ⚠️ 依赖 Ledger 写入时脱敏（#16/#18 修复后自动解决） |
| #21 | CapabilityRegistry 异常包装脱敏 | `capabilities/registry.py:171-174,288-290` | ✅ 有效 - `RuntimeError(f”...{e}”)` 未脱敏 |
| #22 | API trigger `_runs` 有界化 | `triggers/api/server.py:149,360` | ✅ 有效 - 无界字典无 TTL |
| #23 | 客户端可见错误响应脱敏 | 多文件 | ✅ 有效 - MCP/OwlHub/Signal/Governance 均有 `str(exc)` 暴露 |
| #24 | grpc binding schema fail-fast | `capabilities/bindings/schema.py:117` | ✅ 有效 - 无专门验证逻辑 |
| #25 | Kafka connect timeout | `integrations/queue_adapters/kafka.py:46-67` | ✅ 有效 - 无 timeout 保护 |
| #26 | API rate limiter `_states` 有界化 | `triggers/api/server.py:90` | ✅ 有效 - 无界字典无 TTL |
| #27 | API key identity 脱敏 | `triggers/api/auth.py:38` | ✅ 有效 - `api_key:{key[:6]}` 暴露前缀 |
| #28 | CronMetrics samples 有界化 | `triggers/cron.py:620-622` | ✅ 有效 - 无界列表（但 `_recent_executions` 已用 deque maxlen=50） |
| #29 | Cron 历史 tenant 绑定认证上下文 | `triggers/cron.py:1258-1320` | ⚠️ 依赖认证中间件（同 #2 信任边界问题） |

**D25 已完成**（codex-work）：`KafkaQueueAdapter` 增加 `connect_timeout` 参数，`connect()` 内对 `consumer.start()` / `producer.start()` 使用 `asyncio.wait_for`，超时抛出 `TimeoutError` 并记录日志；单测见 `test_queue_kafka_adapter_connect_timeout_*`。

**D15 已完成**（codex-work）：HTTP binding 空 `allowed_hosts` 已 fail-closed（执行时拒绝 + `validate_config` 校验非空）；单测 `test_http_executor_empty_allowed_hosts_rejected`、`test_http_executor_validate_config_rejects_empty_allowed_hosts`。

**D16 已完成**（codex-work）：BindingTool 写入 ledger 使用 `_safe_ledger_error_message`，不持久化原始 `str(exc)`；单测见 `test_binding_tool_records_error_then_reraises`（含 D16 断言）。

---

## Backlog（报告 #35-#44，待统筹分配）

> 来源：`docs/review/DEEP_AUDIT_REPORT.md` 第 7-8 轮及 Recommended Fix Order。当前轮审校收口后再切批分配。

| 报告# | 简述 | 位置 | 验收要点 |
|-------|------|------|----------|
| #35 | Webhook admin token 常量时间比较 | `triggers/webhook/http/app.py` require_admin_token | `hmac.compare_digest` |
| #36 | Webhook log_request 敏感 header 脱敏后再入 event.data | `http/app.py` build_event data=headers | 落库前 redact authorization/x-signature/x-admin-token |
| #37 | GET /events 鉴权或 tenant 绑定 | `http/app.py` GET /events | 需 admin 或与 /endpoints 同鉴权；多租户时 tenant 从认证来 |
| #38 | endpoint_id 非 UUID 时返回 404 而非 500 | `manager.py` get_endpoint；app 入口 | 校验格式或 catch ValueError -> 404 |
| #39 | Webhook GovernanceClient/ExecutionTrigger 对外不暴露 `str(exc)` | `governance.py:90`；`execution.py:85,98` | 脱敏或通用文案（对齐 #16/#23） |
| #40 | Webhook 限流器与 idempotency 字典有界或 TTL | `http/app.py` `_RateLimiter`；`execution.py` `_idempotency` | 有界或 TTL/清理策略 |
| #41 | Idempotency key 按 tenant_id+endpoint_id 隔离 | `execution.py` key 使用处；app 传入 | 键含 tenant+endpoint 前缀或 hash |
| #42 | SignalRouter.dispatch 不向 result.message 写 `str(exc)` | `triggers/signal/router.py:72` | 脱敏或通用文案（对齐 #23） |
| #43 | DBChangeTriggerManager._dlq_events 有界或定期清理 | `triggers/db_change/manager.py` `_dlq_events` | `deque(maxlen)` 或 purge |
| #44 | `_move_to_dlq` 的 error 字段脱敏 | `triggers/db_change/manager.py:207` | 不存原始 `str(exc)`（对齐 #16/#23） |
