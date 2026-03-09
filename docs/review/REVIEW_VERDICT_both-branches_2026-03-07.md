# 审校结论 — codex-work / codex-gpt-work 安全回滚（2026-03-07 Round 4）

**审校日期**: 2026-03-07
**审校对象**: codex-work（本地 `784c68e6`）、codex-gpt-work（本地 `6c81fed2`）
**审校类型**: 安全修复回滚检测

---

## 1. Verdict 汇总

| 分支 | 结果 | 安全回滚数 | 级别 |
|------|------|------------|------|
| codex-work | ❌ **REJECT** | 2 | High |
| codex-gpt-work | ❌ **REJECT** | 5 | Critical |

---

## 2. codex-work 安全回滚

### 2.1 Finding W1 — 路径遍历防护删除

**文件**: `owlclaw/agent/memory/service.py`

**删除内容**:
```diff
-    @staticmethod
-    def _resolve_file_fallback_path(raw: str, *, allowed_base: Path) -> Path:
-        """Resolve file_fallback_path and ensure it is under allowed_base (Finding #50)."""
-        path = Path(raw).expanduser().resolve()
-        try:
-            path.relative_to(allowed_base)
-        except ValueError:
-            raise ValueError(
-                f"file_fallback_path must be under allowed directory: {path} not under {allowed_base}"
-            ) from None
-        return path
```

**风险**: 路径遍历漏洞可被利用写入任意文件

### 2.2 Finding W2 — State Provider 超时保护删除

**文件**: `owlclaw/capabilities/registry.py`

**删除内容**:
```diff
-                result = await asyncio.wait_for(
-                    result, timeout=self._handler_timeout_seconds
-                )
+                result = await result
```

**风险**: State provider 无超时保护，可能导致资源耗尽

### 2.3 安全修复保留

| 文件 | 修复 | 状态 |
|------|------|------|
| `runtime.py` | `_redact_sensitive_args` | ✅ 保留 |
| `runtime.py` | `safe_payload` | ✅ 保留 |
| `llm.py` | `timeout_seconds` | ✅ 保留 |
| `llm.py` | `"LLM call failed"` | ✅ 保留 |

---

## 3. codex-gpt-work 安全回滚（已确认）

| ID | 级别 | 问题 | 文件 |
|----|------|------|------|
| F1 | Critical | 删除 `_redact_sensitive_args()` | `runtime.py` |
| F2 | Critical | `_observe_tool` 不使用 `safe_payload` | `runtime.py` |
| F3 | Critical | 错误消息泄露 `str(exc)` | `llm.py` |
| F4 | High | `aembedding()` 无超时保护 | `llm.py` |
| F5 | High | `LLMClient.complete()` 无超时保护 | `llm.py` |

---

## 4. Findings 总表

| ID | 分支 | 级别 | 描述 | 文件 |
|----|------|------|------|------|
| W1 | codex-work | **High** | 删除 `_resolve_file_fallback_path()`，路径遍历漏洞 | `memory/service.py` |
| W2 | codex-work | **Medium** | 删除 State provider 超时保护 | `registry.py` |
| F1 | codex-gpt-work | **Critical** | 删除 `_redact_sensitive_args()` | `runtime.py` |
| F2 | codex-gpt-work | **Critical** | `_observe_tool` 不使用 `safe_payload` | `runtime.py` |
| F3 | codex-gpt-work | **Critical** | 错误消息泄露 | `llm.py` |
| F4 | codex-gpt-work | **High** | `aembedding()` 无超时保护 | `llm.py` |
| F5 | codex-gpt-work | **High** | `LLMClient.complete()` 无超时保护 | `llm.py` |

---

## 5. Verdict

```
review(codex-work): REJECT — 安全修复部分回滚

检查项：代码变更 ❌ | 安全覆盖 ❌（W1/W2）
问题：memory/service.py 删除路径验证，registry.py 删除超时保护

---

review(codex-gpt-work): REJECT — 安全修复完全回滚

检查项：代码变更 ❌ | 安全覆盖 ❌（F1-F5）
问题：runtime.py/llm.py 安全修复全部删除
```

---

## 6. 后续动作

两个编码分支均需：
1. 执行 `git merge review-work` 恢复安全修复
2. 重新请求审校

### 验证清单

- [ ] `_resolve_file_fallback_path` 存在于 `memory/service.py`
- [ ] `file_fallback_allowed_base` 参数存在于 `MemoryService.__init__`
- [ ] `asyncio.wait_for` 存在于 `registry.py`
- [ ] `_redact_sensitive_args` 存在于 `runtime.py`
- [ ] `timeout_seconds` 参数存在于 `llm.py`