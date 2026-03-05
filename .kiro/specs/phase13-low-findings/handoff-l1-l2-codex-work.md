# Phase 13 Handoff (codex-work): L1 + L2

> Scope: `phase13-low-findings` Task 1.1 / 1.2  
> Owner: `codex-work`  
> Prepared by: `codex-gpt-work` (read-only audit handoff)  
> Date: 2026-03-05

---

## L1 — Langfuse Secret 输出脱敏（Finding #11）

### 当前风险点（代码位置）
- `owlclaw/agent/runtime/runtime.py:241-242`
  - `_langfuse_init_error = str(exc)`
  - `logger.warning("Langfuse init failed: %s", exc)`
- `owlclaw/integrations/llm.py:467-468`
  - `logger.warning("Langfuse init failed: %s", e)`
  - `_langfuse_init_error = str(e)`

### 风险说明
- 异常字符串可能包含 `public_key/secret_key` 或带凭据 URL。
- 目前日志与内部状态字段都可能保留明文异常文本。

### 建议实现（最小改动）
1. 在 `runtime.py` 和 `llm.py` 增加统一的 `_safe_error_message()`（或复用 `integrations/langfuse.py` 同等逻辑）。
2. 规则：
   - 替换 `public_key`、`secret_key`、常见 token 片段（如 `sk-...`）为 `[REDACTED]`。
   - `_langfuse_init_error` 只保存脱敏后文本。
   - `logger.warning(...)` 只打印脱敏后文本。
3. 保持现有行为语义不变（仅安全输出变化）。

### 建议测试
- 新增/补强：
  - `tests/unit/integrations/test_llm.py`
  - `tests/unit/agent/test_runtime.py`
- 断言：
  - 触发 Langfuse 初始化异常，异常消息包含假密钥。
  - 日志与 `_langfuse_init_error` 不包含原始密钥。
  - 日志仍包含可定位错误信息（非空、可读）。

---

## L2 — SQL 只读判定加固（Finding #12）

### 当前风险点（代码位置）
- `owlclaw/capabilities/bindings/sql_executor.py:119`
  - `_is_select_query()` 仅 `query.lstrip().lower().startswith("select")`
- `owlclaw/capabilities/bindings/sql_executor.py:44`
  - `read_only` 仅依赖上述启发式布尔值

### 风险说明
- 对注释前缀、多语句、混淆大小写、边缘语句容错不足。
- `read_only=True` 期望应为 fail-close，目前判定过于宽松。

### 建议实现（最小改动）
1. 在 `sql_executor.py` 增加 SQL 规范化函数（去前导注释/空白，统一大小写）。
2. 明确拒绝多语句（含 `;`）与可疑写操作关键字（`insert/update/delete/drop/alter/create/truncate/grant/revoke` 等）。
3. 判定不确定时按非只读处理（fail-close）。
4. 保持参数化机制与现有 `read_only` 主流程不变。

### 建议测试
- 扩展 `tests/unit/capabilities/test_bindings_sql_executor.py`：
  - 合法样例：
    - `SELECT ...`
    - `/* comment */ SELECT ...`
    - 大小写混合 `SeLeCt ...`
  - 拒绝样例：
    - `SELECT ...; UPDATE ...`
    - `-- comment\nUPDATE ...`
    - `WITH ... DELETE ...`
  - `read_only=True` 下上述拒绝样例应抛 `PermissionError` 或等价拒绝异常。

---

## 推荐验收命令

```powershell
poetry run pytest `
  tests/unit/integrations/test_llm.py `
  tests/unit/agent/test_runtime.py `
  tests/unit/capabilities/test_bindings_sql_executor.py -q
```

---

## 交付口径（回写文档）

- `.kiro/specs/phase13-low-findings/tasks.md`
  - 勾选 `1.1.1` `1.1.2` `1.2.1` `1.2.2`
- `.kiro/specs/SPEC_TASKS_SCAN.md`
  - 勾选 `L1` `L2`
  - `phase13-low-findings` 状态更新为 `12/12`（若 L3/L4 已在本分支完成并审校通过）
