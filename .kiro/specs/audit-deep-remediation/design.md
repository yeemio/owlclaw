# audit-deep-remediation — 设计

> **对应需求**: `.kiro/specs/audit-deep-remediation/requirements.md`
> **审计报告**: `docs/review/DEEP_AUDIT_REPORT.md`

---

## 1. 总体策略

- **P1**：实现级修复 + 文档，带测试或可执行验收。
- **Low**：共 27 项，按推荐顺序实现，不改变对外 API 契约；优先先封闭信任边界，再做韧性与可维护性修复。

---

## 2. P1-1：Skill 环境变量安全边界

### 2.1 方案
- **前缀策略**：仅当 key 以 `OWLCLAW_SKILL_` 开头时才写入 `os.environ`；否则忽略（并可选 debug 日志）。
- **可选扩展**：运行时配置中支持 `skill_env_allowlist: list[str]`，允许的 key 即使无前缀也可注入；若同时存在前缀与 allowlist，满足其一即可。
- **实现位置**：`owlclaw/agent/runtime/runtime.py` 中 `_inject_skill_env_for_run`；读取 skill 的 `owlclaw_config.env`，过滤后再 `os.environ[key] = value`。

### 2.2 接口
- 无新增对外 API；行为变更仅影响「哪些 env 被注入」。

---

## 3. P1-2：tenant_id 文档与可选加固

### 3.1 文档
- 在 `docs/` 或 Console 相关文档中新增/更新「多租户与 tenant_id」小节：
  - 当前行为：`tenant_id` 来自请求头 `x-owlclaw-tenant`，无服务端校验。
  - 适用场景：自托管、tenant 作为非安全标签（如命名空间）。
  - 多租户部署：必须从认证上下文（session/JWT/API key scope）推导 tenant_id，不可信任客户端 header。
- 可选在 `owlclaw/web/api/deps.py` 的 docstring 或模块注释中引用上述文档。

### 3.2 可选实现
- 若存在「请求上下文」或「认证中间件」可提供「当前用户的 tenant_id」：`get_tenant_id` 优先从该上下文读取；缺失时再回退到 header 或 "default"。
- 若无统一认证层，本 spec 仅交付文档，实现留待后续 spec。

---

## 4. Low-3：Runtime 缓存 LRU

### 4.1 方案
- 将 `_visible_tools_cache` 与 skills 上下文缓存从「普通 dict + 手动 pop 逐出」改为「最大容量 + LRU 逐出」。
- 实现方式：使用 `cachetools.LRUCache`（若已依赖）或自维护「dict + 访问顺序」（如 collections.OrderedDict 按访问移动）。

### 4.2 位置
- `owlclaw/agent/runtime/runtime.py`：两处缓存构造与逐出逻辑。

---

## 5. Low-4：Heartbeat 与 Ledger 解耦

### 5.1 契约
- **Ledger**：新增公开方法，例如 `get_readonly_session_factory()`，返回只读用 session 工厂。内部复用现有 `_session_factory`，不对外暴露私有属性。
- **HeartbeatChecker**：构造时接收「只读 session 工厂」（由 Ledger 的上述方法或上层注入）；不再使用 `getattr(self._ledger, "_session_factory", None)`。

### 5.2 依赖顺序
- 先实现 Ledger 的公开 API；再在 Heartbeat 中改为使用该 API。Ledger 与 Heartbeat 分属不同 worktree 时，先合并 Ledger 变更再改 Heartbeat。

---

## 6. Low-5：LLM 失败错误脱敏

### 6.1 方案
- 在 `runtime.py` 中，当 LLM 调用抛异常并需要向对话追加「助手消息」时，不直接使用 `str(exc)`。
- 使用固定文案（如 "LLM call failed."）或从 exc 的 type 生成简短安全描述。

### 6.2 位置
- `owlclaw/agent/runtime/runtime.py`：约 527–531 行附近，异常处理分支。

---

## 7. Low-6：db/engine 异常映射收窄

### 7.1 方案
- 在 `create_engine` 中：`ConfigurationError` 继续直接抛出；仅将「连接/认证」相关异常（如 SQLAlchemy OperationalError、InterfaceError）映射为现有 DatabaseConnectionError / DatabaseAuthError；其他异常保留原类型或包装为通用 EngineError。

### 7.2 位置
- `owlclaw/db/engine.py`：`create_engine` 及其异常处理分支。

---

## 8. 跨 Worktree 边界

| 任务 | 主要路径 | 分配 worktree |
|------|----------|---------------|
| P1-1, Low-3, Low-5 | runtime.py | codex-work |
| Low-4 Ledger 部分 | governance/ledger.py | codex-work |
| P1-2 | docs + 可选 deps.py | codex-gpt-work |
| Low-4 Heartbeat 部分 | heartbeat.py | codex-gpt-work |
| Low-6 | db/engine.py | codex-gpt-work |
| Low-7（Phase 2） | web/providers/capabilities.py | codex-gpt-work |
| Low-8（Phase 2） | app.py（health_status） | codex-work |
| Low-9（Phase 3） | governance/ledger.py（_background_writer） | codex-work |
| Low-10（Phase 3） | governance/ledger.py（_write_queue） | codex-work |
| Low-11（Phase 3） | triggers/webhook/http/app.py | codex-gpt-work |
| Low-12（Phase 4） | web/api/middleware.py（TokenAuthMiddleware） | codex-work |
| Low-13（Phase 4） | governance/visibility.py | codex-gpt-work |
| Low-14（Phase 4） | integrations/hatchet.py | codex-gpt-work |
| Low-15（Phase 5） | capabilities/bindings/http_executor.py | codex-work |
| Low-16（Phase 6） | capabilities/bindings/tool.py | codex-work |
| Low-17（Phase 7） | triggers/api/server.py（body limit） | codex-gpt-work |
| Low-18（Phase 7） | triggers/api/server.py（ledger error sanitize） | codex-gpt-work |
| Low-19（Phase 7） | triggers/api/auth.py | codex-gpt-work |
| Low-20（Phase 8） | triggers/cron.py | codex-gpt-work |
| Low-21（Phase 9） | capabilities/registry.py | codex-work |
| Low-22（Phase 24） | triggers/api/server.py（_runs eviction/TTL） | codex-gpt-work |
| Low-23（Phase 25） | mcp/server.py + owlhub/api/routes/skills.py + triggers/signal/api.py + governance/proxy.py | codex-work |
| Low-24（Second Pass） | capabilities/bindings/schema.py（grpc validation） | codex-work |
| Low-25（Second Pass） | integrations/queue_adapters/kafka.py | codex-work |
| Low-26（Round 2） | triggers/api/server.py（rate limiter `_states`） | codex-gpt-work |
| Low-27（Round 2） | triggers/api/auth.py（opaque identity） | codex-gpt-work |
| Low-28（Round 3） | triggers/cron.py（bounded samples） | codex-gpt-work |
| Low-29（Round 3） | triggers/cron.py（tenant bound to auth context） | codex-gpt-work |

Ledger 与 Heartbeat 需顺序实现：Ledger API 先合并，再在 codex-gpt-work 改 Heartbeat。

---

## 9. Low-12（Phase 4）：Console API token 常量时间比较

### 9.1 方案
- 在 `owlclaw/web/api/middleware.py` 中，将 token 校验由 `provided_token != expected_token` / `api_token_header == expected_token` 改为 `hmac.compare_digest(provided_token, expected_token)`（或等价常量时间比较）。
- 确保 `provided_token` 与 `expected_token` 均为 bytes 或 str 且类型一致；若从 header 读取为 str，expected 也为 str 即可。

### 9.2 位置
- `owlclaw/web/api/middleware.py`：TokenAuthMiddleware 内两处比较（约 79、95 行附近）。

---

## 10. Low-13（Phase 4）：VisibilityFilter evaluator 超时保护

### 10.1 方案
- 在 `owlclaw/governance/visibility.py` 中，为单个 evaluator 执行增加可选 timeout。
- 可采用 `asyncio.wait_for` 包裹 evaluator，超时后按保守策略处理，并记录 debug/warning 日志。
- 若当前架构不适合直接加 timeout，至少在文档中明确该风险和适用边界。

### 10.2 位置
- `owlclaw/governance/visibility.py`：`filter_capabilities` / evaluator 聚合路径。

---

## 11. Low-14（Phase 4）：Hatchet Windows SIGQUIT 作用域

### 11.1 方案
- 收敛 `signal.SIGQUIT = signal.SIGTERM` 的影响范围，避免修改全局 `signal` 模块状态后影响其他代码路径。
- 可选方案：
  - worker wrapper 内做局部兼容映射；
  - 仅在 worker 子进程入口设置；
  - 若暂不改实现，则在文档中明确 Windows 上的该行为与边界。

### 11.2 位置
- `owlclaw/integrations/hatchet.py`：`start_worker()`。

---

## 12. Low-15（Phase 5）：HTTP binding SSRF 边界

### 12.1 方案
- 在 `owlclaw/capabilities/bindings/http_executor.py` 中明确 `allowed_hosts` 为空时的安全语义。
- 倾向实现为 fail-closed：生产配置要求非空 allowlist；若保持兼容，则至少在验证与文档中明确“空 allowlist 允许任意公网 host”，并记录 SSRF 风险。

### 12.2 位置
- `owlclaw/capabilities/bindings/http_executor.py`：`_validate_outbound_url()` 及相关配置校验路径。

---

## 13. Low-16（Phase 6）：BindingTool ledger 错误信息脱敏

### 13.1 方案
- 在 `owlclaw/capabilities/bindings/tool.py` 中，为 ledger 记录失败结果时统一使用安全错误消息构造函数。
- 若未来 API trigger / cron 也需共享同一策略，可抽成 ledger 错误消息 sanitizer，避免不同入口出现不同脱敏规则。

### 13.2 位置
- `owlclaw/capabilities/bindings/tool.py`：失败路径 `_record_ledger(...)` 调用点。

---

## 14. Low-17 / Low-18 / Low-19 / Low-20（Phase 7-8）：API trigger 与 Cron 收口

### 14.1 方案
- `Low-17`：在 `owlclaw/triggers/api/server.py` 读取 body 时执行长度上限检查，不再仅信任 `Content-Length`。
- `Low-18`：API trigger 写 ledger 时复用统一安全错误消息，不持久化原始 `str(exc)`。
- `Low-19`：`owlclaw/triggers/api/auth.py` 中 token/key 比较改为 `hmac.compare_digest`。
- `Low-20`：`owlclaw/triggers/cron.py` 输出执行历史时，依赖已脱敏 ledger 写入，必要时二次 redaction。

### 14.2 位置
- `owlclaw/triggers/api/server.py`
- `owlclaw/triggers/api/auth.py`
- `owlclaw/triggers/cron.py`

---

## 15. Low-21（Phase 9）：CapabilityRegistry 异常包装脱敏

### 15.1 方案
- `CapabilityRegistry.invoke_handler()` 与 `get_state()` 不再直接把原始异常字符串拼进 `RuntimeError`。
- 改为通用安全文案，必要时仅保留异常类型名，并通过日志记录详细原因。

### 15.2 位置
- `owlclaw/capabilities/registry.py`：`invoke_handler()`、`get_state()`。

---

## 16. Low-22（Phase 24）：API trigger `_runs` 有界化

### 16.1 方案
- 在 `owlclaw/triggers/api/server.py` 中，为异步运行结果缓存 `_runs` 增加 `maxsize` + 淘汰策略，或引入 TTL 清理。
- 倾向与现有 D17/D18 同 worktree 一并处理，复用 API trigger 测试与配置入口。

### 16.2 位置
- `owlclaw/triggers/api/server.py`：`_runs` 初始化、写入、读取与清理路径。

---

## 17. Low-23（Phase 25）：客户端可见错误信息脱敏

### 17.1 方案
- 对外错误响应统一通过安全错误消息 helper 输出，不直接透传 `str(exc)`。
- 详细异常仅进入 structlog；HTTP/RPC/MCP 响应只返回类型级或通用文案。

### 17.2 位置
- `owlclaw/mcp/server.py`
- `owlhub/api/routes/skills.py`
- `owlclaw/triggers/signal/api.py`
- `owlclaw/governance/proxy.py`

---

## 18. Low-24（Second Pass）：grpc binding schema 校验

### 18.1 方案
- 在 `owlclaw/capabilities/bindings/schema.py` 中为 `grpc` 分支补齐 schema 必填项与验证。
- 若当前 grpc 仅为占位能力，则在 schema 与文档中显式 fail-fast，避免生成“合法但不可运行”的配置。

### 18.2 位置
- `owlclaw/capabilities/bindings/schema.py`：`validate_binding_config()` / `parse_binding_config()`。

---

## 19. Low-25（Second Pass）：Kafka connect 超时

### 19.1 方案
- 在 `owlclaw/integrations/queue_adapters/kafka.py` 的 producer/consumer 启动流程外包一层可配置 timeout。
- 失败时抛出明确连接超时异常并记录日志，避免启动流程无限悬挂。

### 19.2 位置
- `owlclaw/integrations/queue_adapters/kafka.py`：`connect()`。

---

## 20. Low-26 / Low-27（第 2 轮）：API limiter 与 identity 脱敏

### 20.1 方案
- `Low-26`：为 `_TokenBucketLimiter._states` 增加 TTL 或有界淘汰策略。
- `Low-27`：`APIKeyAuthProvider` 使用 hash 或 opaque identity，不再泄露 key 前缀。

### 20.2 位置
- `owlclaw/triggers/api/server.py`
- `owlclaw/triggers/api/auth.py`

---

## 21. Low-28 / Low-29（第 3 轮）：Cron 样本与 tenant trust boundary

### 21.1 方案
- `Low-28`：将 CronMetrics 采样容器改为有界集合。
- `Low-29`：当 `get_execution_history()` 面向客户端暴露时，tenant_id 需与认证上下文绑定；至少先文档化为与 P1-2 同类边界。

### 21.2 位置
- `owlclaw/triggers/cron.py`
