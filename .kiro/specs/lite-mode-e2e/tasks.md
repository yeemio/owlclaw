# lite-mode-e2e — 任务清单

> **来源**: `design.md` D1~D8
> **验收标准**: 每个 Task 的验收项全部通过才可打勾

---

## Task 0：Spec 文档与契约 ✅

- [x] 0.1 编写 requirements.md ✅
- [x] 0.2 编写 design.md ✅
- [x] 0.3 编写 tasks.md ✅
- [x] 0.4 更新 SPEC_TASKS_SCAN.md 功能清单 ✅

---

## Task 1：统一 LLM 调用路径（D1，REQ-F1）

> **文件**: `owlclaw/integrations/llm.py`、`owlclaw/app.py`

- [x] 1.1 在 `llm.py` 中新增模块级 `_mock_config` 全局状态和 `configure_mock()` 函数
- [x] 1.2 修改 `acompletion()` 门面函数：检查 `_mock_config`，非 None 时返回 mock 响应
- [x] 1.3 mock 响应构造：返回与 litellm 兼容的 response 对象（含 `choices[0].message.tool_calls`）
- [x] 1.4 `OwlClaw.lite()` 中调用 `configure_mock(mock_responses)` 设置全局 mock
- [x] 1.5 `OwlClaw.stop()` 中调用 `configure_mock(None)` 清除 mock（测试隔离）
- [x] 1.6 单元测试：验证 `acompletion()` 在 mock_mode 下返回正确格式的 function_calls
- [x] 1.7 单元测试：验证 `configure_mock(None)` 后 `acompletion()` 恢复真实调用路径
- [x] 1.8 集成测试：Lite Mode 下 `runtime.trigger_event()` 不报 API Key 错误

**验收**：
- `acompletion()` 在 mock_mode 下返回包含 tool_calls 的 litellm 兼容响应
- 现有 LLM 集成测试全部通过
- `configure_mock(None)` 后行为恢复正常

---

## Task 2：Lite Mode Heartbeat 直通（D2，REQ-F2）

> **文件**: `owlclaw/agent/runtime/runtime.py`、`owlclaw/app.py`

- [x] 2.1 修改 `runtime.run()` 方法：当 `_heartbeat_checker` 为 None 或 disabled 时，跳过 `check_events()` 直接进入 `_decision_loop`
- [x] 2.2 `OwlClaw.lite()` 配置中设置 heartbeat_checker 为 disabled
- [x] 2.3 单元测试：Lite Mode 下 heartbeat 触发直接进入决策循环
- [x] 2.4 单元测试：生产模式下 heartbeat 仍走 check_events() 逻辑

**验收**：
- Lite Mode 下 `app.run()` 第一个 heartbeat 周期内 Agent 执行决策循环
- 非 Lite Mode 行为不变

---

## Task 3：自动配置日志（D3，REQ-F3）

> **文件**: `owlclaw/app.py`

- [x] 3.1 新增 `_ensure_logging()` 方法：root logger 无 handler 时配置 basicConfig
- [x] 3.2 在 `run()` 和 `lite()` 入口调用 `_ensure_logging()`
- [x] 3.3 heartbeat 每次触发输出日志（是否有事件、是否进入决策）
- [x] 3.4 单元测试：验证日志配置不覆盖用户自定义 handler
- [x] 3.5 单元测试：验证 Lite Mode 下 `app.run()` 产生可见日志

**验收**：
- `python app.py` 启动后立即看到启动日志
- heartbeat 每次触发输出一行日志
- 用户已配置 logging 时不被覆盖

---

## Task 4：`--once` 走决策循环（D4，REQ-F4）

> **文件**: `owlclaw/app.py`

- [x] 4.1 重写 `run_once()` 方法：调用 `runtime.trigger_event()` 而非直接调 handler
- [x] 4.2 添加结构化输出：展示 Agent 决策过程（LLM 选择 → tool call → handler 结果）
- [x] 4.3 单元测试：`run_once()` 触发完整决策循环
- [x] 4.4 单元测试：`run_once()` 输出包含 Agent 决策信息

**验收**：
- `run_once()` 走 `runtime.trigger_event()` → `_decision_loop()` 完整路径
- 输出中可见 Agent 选择了哪个 capability

---

## Task 5：延迟导入 pgvector（D6，REQ-F6）

> **文件**: `owlclaw/agent/memory/decay.py`（新增）、`store_inmemory.py`、`store_pgvector.py`

- [x] 5.1 新增 `owlclaw/agent/memory/decay.py`：提取 `time_decay()` 函数
- [x] 5.2 修改 `store_inmemory.py`：从 `decay` 模块导入 `time_decay`
- [x] 5.3 修改 `store_pgvector.py`：从 `decay` 模块导入 `time_decay`（保持向后兼容）
- [x] 5.4 单元测试：无 pgvector 环境下 `import owlclaw` 成功
- [x] 5.5 单元测试：`InMemoryStore` 正常工作

**验收**：
- 无 pgvector 环境下 `import owlclaw` 不报 ModuleNotFoundError
- `OwlClaw.lite()` 正常工作
- pgvector 安装后 `store_pgvector` 正常工作

---

## Task 6：Quick Start 示例与文档重写（D5，REQ-F5）

> **文件**: `examples/quick_start/app.py`、`docs/QUICK_START.md`

- [x] 6.1 重写 `examples/quick_start/app.py`：mock_responses 配置 function_calls
- [x] 6.2 更新 `docs/QUICK_START.md`：说明 mock LLM 行为、Agent 决策过程
- [x] 6.3 添加 Quick Start 输出示例到文档
- [x] 6.4 手动验收：按文档从零跑通，确认用户可见 Agent 决策过程

**验收**：
- Quick Start 输出中可见 Agent 的决策过程
- 文档准确描述 Lite Mode 行为

---

## Task 7：Ledger CLI 优雅降级（D7，REQ-F7）

> **文件**: `owlclaw/cli/ledger.py`

- [x] 7.1 `ledger query` 检测 DB 配置，无 DB 时输出友好提示（不崩溃）
- [x] 7.2 单元测试：无 DB 时 `ledger query` 返回提示而非异常

**验收**：
- 无 DB 时 `owlclaw ledger query` 输出提示信息，退出码 0
- 有 DB 时行为不变

---

## Task 8：API 端点优雅降级（D8，REQ-F8）

> **文件**: `owlclaw/web/api/` 相关端点

- [x] 8.1 API 依赖注入层检测 DB 状态，无 DB 时返回空结果 + 提示
- [x] 8.2 单元测试：无 DB 时 API 返回空结果而非 500

**验收**：
- `/api/v1/agents` 无 DB 时返回 `{"items": [], "message": "Database not configured"}`
- Console 前端能优雅显示空状态

---

## Task 9：Model 配置传递修复（D9，REQ-F9）

> **文件**: `owlclaw/app.py`

- [x] 9.1 `create_agent_runtime()` 从 `self._config` 读取 `integrations.llm.model` 并传递给 Runtime
- [x] 9.2 单元测试：`app.configure(model="deepseek/deepseek-chat")` 后 runtime.model 正确

**验收**：
- 用户配置的 model 正确传递到 Runtime

---

## Task 10：Router 默认行为修复（D10，REQ-F10）

> **文件**: `owlclaw/governance/visibility.py`

- [x] 10.1 Router `select_model()` 对未配置的 task_type 返回 None
- [x] 10.2 单元测试：无显式路由规则时 Runtime 使用 self.model

**验收**：
- 无路由规则时不覆盖用户配置的 model

---

## Task 11：全量回归与端到端验收

- [x] 11.1 全量 `poetry run pytest` 通过（`2062 passed, 35 skipped`）
- [x] 11.2 端到端验收：`OwlClaw.lite()` → `run_once()` → handler 执行 → 可见决策过程（`test_run_once_uses_runtime_trigger_event_and_returns_decision_info`）
- [x] 11.3 端到端验收：`app.run()` Lite Mode 下 Agent 周期性决策并输出日志（`test_lite_mode_heartbeat_trigger_runs_without_api_key` + heartbeat 日志回归）
- [x] 11.4 端到端验收：Console UI 在无 DB 时优雅显示（`test_agents_list_route_returns_empty_when_database_not_configured`）
- [x] 11.5 端到端验收：真实 LLM（DeepSeek）下完整决策循环（function calling → handler → 结果汇总，`test_real_openai_function_calling` 实模通过）

**验收**：
- 全部测试通过
- 用户从零跑通 Quick Start 体验到 Agent 决策
- 真实 LLM 下 Agent 正确选择并调用 handler
