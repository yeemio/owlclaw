# 审校结论 — codex-work / codex-gpt-work 安全回滚状态（2026-03-07 Round 5）

**审校日期**: 2026-03-07
**审校对象**: codex-work（本地 `22bdb9cb`）、codex-gpt-work（本地 `6c81fed2`）
**审校类型**: 安全修复回滚检测

---

## 1. Verdict 汇总

| 分支 | 结果 | 未修复 Findings |
|------|------|-----------------|
| codex-work | ❌ **REJECT** | W1 |
| codex-gpt-work | ❌ **REJECT** | F1-F5 |

---

## 2. codex-work 状态

### 2.1 已修复

| Finding | 状态 | 说明 |
|---------|------|------|
| W2 | ✅ 已修复 | Handler invocation 保留 `asyncio.wait_for` 超时保护 |

### 2.2 未修复

| Finding | 级别 | 问题 | 文件 |
|---------|------|------|------|
| **W1** | High | `memory/service.py` 缺少路径遍历防护 | `memory/service.py` |

**W1 详情**:
- 删除 `_resolve_file_fallback_path()` 方法
- 删除 `file_fallback_allowed_base` 参数
- `_append_file_fallback` 直接使用 `Path(self._config.file_fallback_path)` 无验证

### 2.3 代码证据

```diff
-    @staticmethod
-    def _resolve_file_fallback_path(raw: str, *, allowed_base: Path) -> Path:
-        """Resolve file_fallback_path and ensure it is under allowed_base (Finding #50)."""
-        path = Path(raw).expanduser().resolve()
-        try:
-            path.relative_to(allowed_base)
-        except ValueError:
-            raise ValueError(...)
-        return path
```

---

## 3. codex-gpt-work 状态

### 3.1 未修复 Findings

| ID | 级别 | 问题 | 文件 |
|----|------|------|------|
| F1 | Critical | 删除 `_redact_sensitive_args()` | `runtime.py` |
| F2 | Critical | `_observe_tool` 不使用 `safe_payload` | `runtime.py` |
| F3 | Critical | 错误消息泄露 `str(exc)` | `llm.py` |
| F4 | High | `aembedding()` 无超时保护 | `llm.py` |
| F5 | High | `LLMClient.complete()` 无超时保护 | `llm.py` |

---

## 4. Verdict

```
review(codex-work): REJECT — W1 未修复（路径遍历漏洞）

检查项：代码变更 ❌ | 安全覆盖 ❌（W1）
问题：memory/service.py 删除路径验证，可被利用写入任意文件

---

review(codex-gpt-work): REJECT — 安全修复完全回滚

检查项：代码变更 ❌ | 安全覆盖 ❌（F1-F5）
```

---

## 5. 后续动作

**codex-work**:
- 恢复 `memory/service.py` 中的 `_resolve_file_fallback_path()` 方法
- 恢复 `file_fallback_allowed_base` 参数
- 重新请求审校

**codex-gpt-work**:
- 执行 `git merge review-work` 恢复全部安全修复
- 重新请求审校