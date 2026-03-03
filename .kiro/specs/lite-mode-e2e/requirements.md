# lite-mode-e2e — Lite Mode 端到端体验修复

> **来源**: 2026-03-03 真实用户视角深度体验测试
> **优先级**: P0（产品核心承诺不成立，阻断新用户上手）
> **预计工时**: 3-5 天

---

## 背景

2026-03-03 以真实用户视角从零体验 OwlClaw，发现 Lite Mode 的端到端体验链路**从设计上断裂**：

1. 文档承诺"10 分钟、零外部依赖看到 Agent 决策"
2. 实际体验：`app.run()` 启动后 3 分钟零输出、零日志；强制触发决策循环时报 OpenAI API Key 错误
3. `--once` 模式只是直接调 handler 函数，不走 Agent 决策循环
4. 用户跑完 Quick Start 后的感受：**"这跟我自己写个 if/else 有什么区别？"**

**核心问题**：用户在 Lite Mode 下**完全无法体验到 OwlClaw 的核心价值——Agent 读取 SKILL.md 自主决策**。

---

## 功能需求

### REQ-F1：mock LLM 必须拦截 Runtime 决策循环的 LLM 调用

- **现状**：Runtime `_call_llm_completion()` 调用 `llm_integration.acompletion()`（模块级门面函数），该函数直接调 `litellm.acompletion()` 不检查 mock_mode。mock_mode 只在 `LLMIntegration.complete()` 类方法中生效。
- **问题**：两套 LLM 调用路径完全脱节，Lite Mode 配置的 mock_mode 对决策循环无效
- **修复**：`acompletion()` 门面函数必须检查全局 mock_mode 配置；或 Runtime 改用 `LLMIntegration.complete()` 路径
- **验收**：
  - Lite Mode 下 `trigger_event("heartbeat", payload={"has_events": True})` 不报 API Key 错误
  - mock LLM 返回包含 function_calls 的响应，触发 handler 执行
  - 现有 LLM 集成测试继续通过

### REQ-F2：Lite Mode 下 `app.run()` 的 heartbeat 必须能触发 Agent 决策

- **现状**：HeartbeatChecker 所有事件源（database/schedule/webhook/queue/external_api）在无 DB/Hatchet 时全部返回 False → Agent 永远 skip
- **问题**：`app.run()` 在 Lite Mode 下是死循环，Agent 永远不决策
- **修复策略**（二选一，设计阶段决定）：
  - **方案 A**：Lite Mode 下禁用 HeartbeatChecker（`heartbeat_checker=None`），heartbeat 触发直接进入决策循环
  - **方案 B**：Lite Mode 下自动注入 `has_events: True` 到 heartbeat payload
- **验收**：
  - `app.run()` 启动后，第一个 heartbeat 周期内 Agent 执行决策循环并输出结果
  - 非 Lite Mode（生产模式）行为不变

### REQ-F3：`app.run()` 必须有可见的启动和运行日志

- **现状**：`logging.getLogger(__name__)` 但没有配置 handler，Python 默认静默丢弃
- **修复**：`app.run()` 和 `OwlClaw.lite()` 在入口处配置 `logging.basicConfig` 或等效机制
- **验收**：
  - 用户运行 `python app.py` 后立即看到启动日志（agent 名称、模式、skills 数量、heartbeat 间隔）
  - heartbeat 每次触发时输出一行日志（即使 skip 也要说明原因）
  - 日志格式简洁可读（时间 + 级别 + 消息）

### REQ-F4：`--once` 模式必须走 Agent 决策循环

- **现状**：`run_once()` 直接调 `registry.invoke_handler()`，绕过 Runtime 的 `trigger_event()` → `_decision_loop()`
- **问题**：用户以为看到了 AI 决策，实际只是函数调用
- **修复**：`--once` 模式应调用 `runtime.trigger_event()` 并展示完整决策过程（LLM 思考 → tool call → handler 执行 → 结果）
- **验收**：
  - `python app.py --once` 输出包含 Agent 决策过程（不只是 handler 返回值）
  - 输出中可见 Agent 选择了哪个 capability、为什么选择
  - mock LLM 的 function_calls 能正确触发对应 handler

### REQ-F5：Quick Start 示例必须展示 AI 决策过程

- **现状**：handler 是 if/else 硬编码，用户无法理解 OwlClaw 与普通函数调用的区别
- **修复**：重写 Quick Start 示例和文档，让用户看到：
  1. Agent 读取 SKILL.md 理解业务规则
  2. Agent 通过 LLM function calling 选择调用哪个 handler
  3. handler 执行后 Agent 汇总决策结果
- **验收**：
  - Quick Start 输出中可见 Agent 的"思考过程"（mock LLM 的 content + function_calls）
  - 文档更新说明 Lite Mode 的 mock LLM 行为

### REQ-F6：`import owlclaw` 不应因可选依赖缺失而崩溃

- **现状**：`store_inmemory.py` 无条件 `from owlclaw.agent.memory.store_pgvector import time_decay`，pgvector 不在基础依赖中
- **修复**：延迟导入或将 `time_decay` 提取到不依赖 pgvector 的公共模块
- **验收**：
  - 无 pgvector 环境下 `import owlclaw` 成功
  - `OwlClaw.lite()` 正常工作
  - pgvector 安装后 `store_pgvector` 正常工作

### REQ-F7：`owlclaw ledger query` 支持 in-memory ledger

- **现状**：CLI 直接 `get_engine()` 连 DB，不支持 in-memory 后端
- **修复**：Lite Mode 下 ledger query 从 in-memory ledger 读取；或提供 `--in-memory` 标志
- **验收**：
  - Lite Mode 运行 Agent 后，`owlclaw ledger query` 能显示执行记录
  - 无 DB 时不崩溃，给出友好提示

### REQ-F8：无 DB 时 API 端点优雅降级

- **现状**：`/api/v1/agents` 无 DB 时返回 500
- **修复**：依赖 DB 的端点在 DB 未配置时返回空结果 + 提示信息，不返回 500
- **验收**：
  - `/api/v1/agents` 无 DB 时返回 `{"items": [], "message": "Database not configured"}`
  - Console 前端能优雅显示空状态

---

### REQ-F9：`app.configure()` 的 model 配置必须传递到 Runtime

- **现状**：`create_agent_runtime()` 不传 `model` 参数给 `AgentRuntime` 构造函数，Runtime 默认 `gpt-4o-mini`
- **问题**：用户配置 `app.configure(integrations={"llm": {"model": "deepseek/deepseek-chat"}})` 无效
- **修复**：`create_agent_runtime()` 从 `self._config` 读取 `integrations.llm.model` 并传递给 Runtime
- **验收**：
  - `app.configure(model="deepseek/deepseek-chat")` 后 `runtime.model == "deepseek/deepseek-chat"`
  - litellm 日志显示正确的 provider

### REQ-F10：Router 不应静默覆盖用户配置的 model

- **现状**：Router `select_model()` 对未配置的 task_type 返回默认 model（`gpt-4o-mini`），覆盖用户在 configure 中指定的 model
- **问题**：用户以为配了 DeepSeek，实际调的是 OpenAI
- **修复**：Router 对未配置的 task_type 返回 None（不覆盖），让 Runtime 使用自己的 model
- **验收**：
  - 无显式路由规则时，Runtime 使用 `self.model`
  - 有显式路由规则时，Router 选择的 model 优先

---

## 非功能需求

- 修复不得引入新的外部依赖
- 修复不得改变生产模式（非 Lite Mode）的行为
- 所有现有 1817 个单元测试必须继续通过
- Quick Start 文档（`docs/QUICK_START.md`）必须同步更新
