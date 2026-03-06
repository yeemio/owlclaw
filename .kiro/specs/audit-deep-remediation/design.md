# audit-deep-remediation — 设计

> **对应需求**: `.kiro/specs/audit-deep-remediation/requirements.md`
> **审计报告**: `docs/review/DEEP_AUDIT_REPORT.md`

---

## 1. 总体策略

- **P1**：实现级修复 + 文档，带测试或可执行验收。
- **Low**：共 12 项，按推荐顺序实现，不改变对外 API 契约；优先解耦与可维护性。

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
