# lite-mode-e2e — 设计文档

> **来源**: `requirements.md` REQ-F1 ~ REQ-F10
> **架构约束**: 修复不改变生产模式行为；不新增外部依赖

---

## 一、问题根因分析

### 1.1 LLM 调用路径脱节（REQ-F1）

```
Runtime._call_llm_completion()
  → llm_integration.acompletion(**kwargs)     # 模块级门面
    → litellm.acompletion(**kwargs)           # 直接调真实 LLM ❌

LLMClient.complete()                          # 类方法
  → if self.config.mock_mode: return mock     # mock 逻辑在这里 ✅
  → litellm.acompletion(**kwargs)
```

Runtime 用的是模块级 `acompletion()`，不经过 `LLMClient.complete()`。

### 1.2 Heartbeat 死循环（REQ-F2）

```
app.run() → _heartbeat_loop() → runtime.trigger_event("heartbeat")
  → runtime.run() → heartbeat_checker.check_events()
    → _check_source("database") → 无 DB → False
    → _check_source("schedule") → 无 Hatchet → False
    → 所有源 False → skip decision loop → 永远不决策
```

### 1.3 日志静默（REQ-F3）

`owlclaw/app.py` 用 `logger = logging.getLogger(__name__)` 但不配置 handler。Python 默认 `lastResort` handler 只输出 WARNING+，INFO 级别的启动日志全部丢弃。

### 1.4 `--once` 绕过决策（REQ-F4）

`run_once()` 直接 `registry.invoke_handler()`，不走 `runtime.trigger_event()` → `_decision_loop()`。

---

## 二、设计方案

### D1：统一 LLM 调用路径（REQ-F1）

**方案**：在模块级 `acompletion()` 中加入 mock_mode 检查。

**修改文件**：`owlclaw/integrations/llm.py`

```python
# 模块级全局状态
_mock_config: dict[str, Any] | None = None

def configure_mock(mock_responses: dict[str, Any] | None) -> None:
    """Set/clear global mock mode for the acompletion facade."""
    global _mock_config
    _mock_config = mock_responses

async def acompletion(**kwargs: Any) -> Any:
    if _mock_config is not None:
        return _build_mock_response(_mock_config, kwargs)
    # ... existing litellm call
```

**触发点**：`OwlClaw.lite()` 调用 `configure_mock(mock_responses)` 设置全局 mock。

**mock 响应格式**：返回与 litellm 兼容的 response 对象，包含 `choices[0].message.tool_calls`，使 Runtime 的 `_decision_loop` 能正确解析 function_calls。

**关键约束**：
- `configure_mock(None)` 清除 mock（用于测试隔离）
- 生产模式不调用 `configure_mock()`，行为不变
- mock 响应必须包含 function_calls 以触发 handler

### D2：Lite Mode Heartbeat 直通（REQ-F2）

**方案**：Lite Mode 下 `HeartbeatChecker` 设为 disabled（`_enabled=False`），同时修改 `runtime.run()` 的逻辑：当 heartbeat_checker 为 disabled 时，heartbeat 触发直接进入决策循环。

**修改文件**：
- `owlclaw/agent/runtime/runtime.py`：`run()` 方法中，当 `_heartbeat_checker` 为 None 或 disabled 时，跳过 `check_events()` 直接进入 `_decision_loop`
- `owlclaw/app.py`：`lite()` 中设置 heartbeat_checker 为 disabled

**逻辑**：
```python
# runtime.run() 中
if self._heartbeat_checker is None or not self._heartbeat_checker.enabled:
    # Lite Mode or no checker: always enter decision loop
    await self._decision_loop(...)
else:
    has_events = await self._heartbeat_checker.check_events(tenant_id)
    if has_events:
        await self._decision_loop(...)
```

### D3：自动配置日志（REQ-F3）

**方案**：在 `OwlClaw.run()` 和 `OwlClaw.lite()` 入口处调用 `_ensure_logging()`。

**修改文件**：`owlclaw/app.py`

```python
def _ensure_logging(self) -> None:
    """Configure logging if no handlers exist on the root logger."""
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
```

**关键约束**：
- 只在 root logger 无 handler 时配置（不覆盖用户自定义配置）
- Lite Mode 默认 INFO 级别
- heartbeat 每次触发输出一行日志（包含是否有事件、是否进入决策）

### D4：`--once` 走决策循环（REQ-F4）

**方案**：`run_once()` 改为调用 `runtime.trigger_event()` 而非直接调 handler。

**修改文件**：`owlclaw/app.py`

**逻辑**：
```python
async def run_once(self, task_type: str = "default", payload: dict | None = None):
    runtime = await self.start(...)
    result = await runtime.trigger_event(task_type, payload=payload or {})
    await self.stop()
    return result
```

**输出增强**：在 `run_once()` 中添加结构化输出，展示 Agent 决策过程。

### D5：Quick Start 示例重写（REQ-F5）

**修改文件**：
- `examples/quick_start/app.py`
- `docs/QUICK_START.md`
- `examples/quick_start/skills/inventory-check/SKILL.md`

**设计要点**：
- mock_responses 配置为包含 function_calls 的响应，触发 handler
- 输出中展示 Agent 的"思考过程"
- 文档说明 mock LLM 的行为和限制

### D6：延迟导入 pgvector 依赖（REQ-F6）

**方案**：将 `time_decay` 函数从 `store_pgvector.py` 提取到 `owlclaw/agent/memory/decay.py` 公共模块。

**修改文件**：
- 新增 `owlclaw/agent/memory/decay.py`：包含 `time_decay()` 函数
- `owlclaw/agent/memory/store_inmemory.py`：从 `decay` 导入
- `owlclaw/agent/memory/store_pgvector.py`：从 `decay` 导入

### D7：Ledger CLI 支持 in-memory（REQ-F7）

**方案**：`owlclaw ledger query` 检测当前是否有运行中的 OwlClaw 实例（通过 PID 文件或 API），若无则提示用户。

**简化方案**：Lite Mode 下 `ledger query` 提示"Lite Mode 使用 in-memory ledger，请通过 API 或 Console 查看"，不崩溃。

**修改文件**：`owlclaw/cli/ledger.py`

### D8：API 端点优雅降级（REQ-F8）

**方案**：在 API 依赖注入层检测 DB 状态，无 DB 时返回空结果 + 提示。

**修改文件**：`owlclaw/web/api/` 相关端点

### D9：Model 配置传递（REQ-F9）

**方案**：`create_agent_runtime()` 从 `self._config["integrations"]["llm"]["model"]` 读取 model 并传递。

**修改文件**：`owlclaw/app.py`

```python
def create_agent_runtime(self, ...):
    llm_cfg = self._config.get("integrations", {}).get("llm", {})
    model = llm_cfg.get("model", "gpt-4o-mini")
    return AgentRuntime(
        ...,
        model=model,
    )
```

### D10：Router 默认行为修复（REQ-F10）

**方案**：Router `select_model()` 对未配置的 task_type 返回 None，Runtime 保持 `self.model`。

**修改文件**：`owlclaw/governance/visibility.py`（Router 实现）

---

## 三、影响范围

| 模块 | 修改文件 | 风险 |
|------|---------|------|
| LLM 集成 | `owlclaw/integrations/llm.py` | 中（核心调用路径） |
| Agent Runtime | `owlclaw/agent/runtime/runtime.py` | 中（决策循环逻辑） |
| App 入口 | `owlclaw/app.py` | 低（新增日志配置） |
| Memory | `owlclaw/agent/memory/decay.py`（新增）、`store_inmemory.py`、`store_pgvector.py` | 低（纯重构） |
| CLI | `owlclaw/cli/ledger.py` | 低 |
| Web API | `owlclaw/web/api/*.py` | 低 |
| 示例 | `examples/quick_start/` | 低 |
| 文档 | `docs/QUICK_START.md` | 低 |

---

## 四、测试策略

1. **单元测试**：mock_mode 拦截、heartbeat 直通、日志配置、延迟导入
2. **集成测试**：Lite Mode 端到端（`OwlClaw.lite()` → `run_once()` → handler 执行 → ledger 记录）
3. **回归测试**：全量 `poetry run pytest` 确保现有 1817 个测试通过
4. **手动验收**：按 Quick Start 文档从零跑通，确认用户可见 Agent 决策过程
