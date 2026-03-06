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
<<<<<<< HEAD

---

## codex-gpt-work 负责

| # | Task | 验收 | 状态 |
|---|------|------|------|
| 5 | **P1-2** 在 docs 中新增/更新「Console 多租户与 tenant_id」：当前行为、适用场景、多租户须从认证推导 | 文档存在且包含上述三点 | [x] |
| 6 | **Low-4b** 在 HeartbeatChecker 中改为使用 Ledger 的 `get_readonly_session_factory()`，移除对 `_session_factory` 的 getattr | grep 确认 heartbeat 无 _session_factory；heartbeat 相关测试通过 | [x] |
| 7 | **Low-6** 在 `db/engine.py` 的 `create_engine` 中收窄异常映射：仅连接/认证类映射为 Database*Error；其余保留或 EngineError | 非连接类异常不再被误报为连接错误；有单测或集成验证 | [x] |
| 10 | **Low-7** 在 `web/providers/capabilities.py` 的 `_collect_capability_stats` 中捕获 ConfigurationError，无 DB 时返回空 stats（与 ledger/triggers 一致，GET /capabilities 不 500） | 无 DB 时 GET /capabilities 返回 200 + items（零统计）；有单测或手验 | [x] |

---

## codex-work 负责（续）

| # | Task | 验收 | 状态 |
|---|------|------|------|
=======
>>>>>>> main
| 11 | **Low-8** 在 `app.py` 的 `health_status()` 中避免直接读 `_states`/`_configs`：改为 manager/server 的公开 API 或只读属性，或文档明确该耦合 | 无私有属性访问或文档注明；health 相关测试通过 | [x] |
| 12 | **Low-9** 在 Ledger._background_writer 的 except Exception 分支中，将当前 batch 写入 fallback 再继续循环，避免丢失已出队记录 | 异常路径有单测或集成验证；batch 不丢 | [x] |
| 13 | **Low-10** Ledger._write_queue 设 maxsize 或实现背压（put 超时/丢弃策略），并文档化上限 | 队列有界或文档明确；压力测试可选 | [x] |
| 15 | **Low-12** 在 Console API TokenAuthMiddleware 中用 hmac.compare_digest 做 token 常量时间比较 | grep 确认无直接 !=/== 比较 token；有单测或手验 | [x] |

### codex-gpt-work 负责

| # | Task | 验收 | 状态 |
|---|------|------|------|
<<<<<<< HEAD
| 14 | **Low-11** 在 webhook receive_webhook 中对 raw_body_bytes.decode("utf-8") 做 try/except UnicodeDecodeError，返回 400 及明确提示 | 非 UTF-8 body 返回 400 而非 500；有单测或手验 | [x] |
| 16 | **Low-13** 在 VisibilityFilter evaluator 路径增加 timeout 或明确文档边界，避免单个 evaluator 长时间阻塞 capability 过滤 | 有测试、手验或文档结论；不会无限等待单个 evaluator | [x] |
| 17 | **Low-14** 收敛 Hatchet Windows SIGQUIT 兼容逻辑的作用域，避免全局 `signal` 模块副作用 | 代码或文档说明明确；Windows 兼容逻辑边界清晰 | [x] |
| 20 | **Low-17** 在 API trigger 请求读取路径按实际读取体积强制 body 大小上限，不再只信任 `Content-Length` | 超限请求在省略/伪造 header 时仍被拒绝；有测试 | [x] |
| 21 | **Low-18** 在 API trigger 写 ledger 失败记录时复用安全错误消息，不持久化原始 `str(exc)` | grep 确认失败路径无原始异常写入 ledger；有测试 | [x] |
| 22 | **Low-19** 在 API trigger `AuthProvider` 中用 `hmac.compare_digest` 做 key/token 常量时间比较 | grep 确认无直接 token 比较；有测试或手验 | [x] |
| 23 | **Low-20** 在 cron `get_execution_history` 中避免向调用方返回未脱敏的 ledger 错误信息 | 输出已 redacted 或由上游写入统一脱敏；有测试 | [x] |
| 25 | **Low-22** 为 API trigger `_runs` 增加 maxsize/LRU/TTL 清理，避免异步结果缓存无限增长 | 压测或单测证明缓存不再无界增长 | [x] |
| 28 | **Low-25** 在 `KafkaQueueAdapter.connect()` 中增加可配置连接超时 | broker 不可达时不会无限阻塞；有测试或集成验证 | [x] |
| 29 | **Low-26** 为 API rate limiter `_states` 增加 TTL/maxsize/LRU，避免 tenant/endpoint 组合无限累积 | 长时间运行下限流状态不再无界增长；有测试 | [x] |
| 30 | **Low-27** 在 `APIKeyAuthProvider` 中移除 key 前 6 位 identity 暴露，改为 hash 或 opaque id | ledger/log/payload 中不再出现 key 前缀；有测试或手验 | [x] |
| 31 | **Low-28** 将 CronMetrics 的 duration/delay/cost samples 改为有界容器 | 长时运行内存不再随样本无限增长；有测试 | [x] |
| 32 | **Low-29** 在 cron 执行历史对外暴露路径中绑定 tenant 到认证上下文，或至少文档化其与 P1-2 同类 trust boundary | 不再信任客户端传入 tenant_id；有实现或文档结论 | [x] |
=======
| 5 | **P1-2** 在 docs 中新增/更新「Console 多租户与 tenant_id」：当前行为、适用场景、多租户须从认证推导 | 文档存在且包含上述三点 | [x] |
| 6 | **Low-4b** 在 HeartbeatChecker 中改为使用 Ledger 的 `get_readonly_session_factory()`，移除对 `_session_factory` 的 getattr | grep 确认 heartbeat 无 _session_factory；heartbeat 相关测试通过 | [x] |
| 7 | **Low-6** 在 `db/engine.py` 的 `create_engine` 中收窄异常映射：仅连接/认证类映射为 Database*Error；其余保留或 EngineError | 非连接类异常不再被误报为连接错误；有单测或集成验证 | [x] |
| 10 | **Low-7** 在 `web/providers/capabilities.py` 的 `_collect_capability_stats` 中捕获 ConfigurationError，无 DB 时返回空 stats（与 ledger/triggers 一致，GET /capabilities 不 500） | 无 DB 时 GET /capabilities 返回 200 + items（零统计）；有单测或手验 | [x] |
| 14 | **Low-11** 在 webhook receive_webhook 中对 raw_body_bytes.decode("utf-8") 做 try/except UnicodeDecodeError，返回 400 及明确提示 | 非 UTF-8 body 返回 400 而非 500；有单测或手验 | [x] |
| 16 | **Low-13** 在 VisibilityFilter evaluator 路径增加 timeout 或明确文档边界，避免单个 evaluator 长时间阻塞 capability 过滤 | 有测试、手验或文档结论；不会无限等待单个 evaluator | [x] |
| 17 | **Low-14** 收敛 Hatchet Windows SIGQUIT 兼容逻辑的作用域，避免全局 `signal` 模块副作用 | 代码或文档说明明确；Windows 兼容逻辑边界清晰 | [x] |
>>>>>>> main

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

## Backlog（D15-D29，待统筹分配）

> 来源：`docs/review/DEEP_AUDIT_REPORT.md` 第 4-6 轮扩展项。已从本轮 15/15 收口中拆出，作为下一批 backlog。

| 报告# | 简述 | 位置 | 验收要点 |
|-------|------|------|----------|
| #15 | Console API token 常量时间比较 | `web/api/middleware.py` | `hmac.compare_digest` |
| #18 | HTTP binding 空 `allowed_hosts` 安全边界 | `capabilities/bindings/http_executor.py` | SSRF 边界明确且可审计 |
| #19 | BindingTool ledger 错误脱敏 | `capabilities/bindings/tool.py` | 不持久化原始 `str(exc)` |
| #20 | API trigger body 读取上限按实际字节强制 | `triggers/api/server.py` | 绕过 `Content-Length` 也会拒绝 |
| #21 | API trigger ledger 错误脱敏 | `triggers/api/server.py` | 不写原始异常 |
| #22 | API trigger 认证常量时间比较 | `triggers/api/auth.py` | `hmac.compare_digest` |
| #23 | Cron/API/MCP/OwlHub/Signal/Governance 对外错误脱敏 | `triggers/cron.py` 等 | 客户端不见原始异常 |
| #24 | grpc binding schema fail-fast | `capabilities/bindings/schema.py` | 配置不再“合法但不可运行” |
| #25 | API trigger `_runs` 与 Kafka connect timeout | `triggers/api/server.py` / `integrations/queue_adapters/kafka.py` | 有界缓存 / 连接不会无限阻塞 |
| #26 | API rate limiter `_states` 有界化 | `triggers/api/server.py` | TTL/maxsize/LRU |
| #27 | API key identity 脱敏 | `triggers/api/auth.py` | 不暴露 key 前缀 |
| #28 | CronMetrics samples 有界化 | `triggers/cron.py` | 样本容器有界 |
| #29 | Cron 历史 tenant 绑定认证上下文 | `triggers/cron.py` | 不再信任客户端 tenant_id |

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
