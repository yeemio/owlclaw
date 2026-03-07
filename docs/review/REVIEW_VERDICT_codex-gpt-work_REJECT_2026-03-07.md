# 审校结论 — codex-gpt-work 安全回滚检测（2026-03-07）

**审校日期**: 2026-03-07
**审校对象**: codex-gpt-work 分支相对 review-work 的变更
**审校类型**: 安全合规检查

---

## 1. Verdict

```
review(codex-gpt-work): REJECT — 检测到安全修复回滚，禁止合并

检查项：Spec 一致性 ❌ | 代码质量 ⚠️ | 安全合规 ❌ | 架构合规 ✅
问题：多项已审校通过的安全修复被删除/回滚
```

---

## 2. Scan 摘要

| 项目 | 内容 |
|------|------|
| 新提交数 | 1 个（Phase 16 delivery 文档） |
| 代码变更文件 | 2 个核心 Python 文件 |
| 变更性质 | **安全修复回滚** |

---

## 3. 被回滚的安全修复（禁止）

### 3.1 Observation 工具参数脱敏 (Finding #48)

| 文件 | 回滚内容 | 安全影响 |
|------|----------|----------|
| `owlclaw/agent/runtime/runtime.py` | 删除 `_SENSITIVE_ARG_SUBSTRINGS` 常量 | ⚠️ 敏感信息泄露 |
| `owlclaw/agent/runtime/runtime.py` | 删除 `_redact_sensitive_args()` 方法 | ⚠️ 密码/token 明文记录到 Langfuse |
| `owlclaw/agent/runtime/runtime.py` | `_observe_tool` 不再使用 `safe_payload` | ⚠️ 观测系统记录敏感参数 |

**diff 证据**:
```diff
-    _SENSITIVE_ARG_SUBSTRINGS = ("password", "api_key", "token", "secret", "credential", "auth")
-
-    @staticmethod
-    def _redact_sensitive_args(args: dict[str, Any]) -> dict[str, Any]:
-        ...
-        safe_payload = dict(payload)
-        if "arguments" in safe_payload and isinstance(safe_payload["arguments"], dict):
-            safe_payload["arguments"] = cls._redact_sensitive_args(safe_payload["arguments"])
+    def _observe_tool(trace: Any | None, name: str, payload: dict[str, Any]) -> Any | None:
+        return span_fn(name=name, input=payload)  # 直接传递原始 payload
```

### 3.2 LLM 错误消息脱敏 (Finding #49)

| 文件 | 回滚内容 | 安全影响 |
|------|----------|----------|
| `owlclaw/integrations/llm.py` | `error_message` 从 `"LLM call failed"` 改为 `str(exc)` | ⚠️ 错误详情泄露到 Langfuse |

**diff 证据**:
```diff
-                        "error_message": "LLM call failed",
+                        "error_message": str(exc),  # 泄露完整异常信息
```

### 3.3 aembedding Timeout 保护 (Finding #52)

| 文件 | 回滚内容 | 安全影响 |
|------|----------|----------|
| `owlclaw/integrations/llm.py` | 删除 `timeout_seconds` 参数 | ⚠️ 无限等待 DoS |

**diff 证据**:
```diff
-async def aembedding(*, timeout_seconds: float | None = 60.0, **kwargs: Any) -> Any:
-    coro = litellm.aembedding(**kwargs)
-    if timeout_seconds is not None and timeout_seconds > 0:
-        return await asyncio.wait_for(coro, timeout=timeout_seconds)
+async def aembedding(**kwargs: Any) -> Any:
+    return await litellm.aembedding(**kwargs)  # 无 timeout
```

### 3.4 LLMClient Timeout 保护 (Finding #55)

| 文件 | 回滚内容 | 安全影响 |
|------|----------|----------|
| `owlclaw/integrations/llm.py` | 删除 `_call_with_fallback` 的 `timeout_seconds` | ⚠️ 无限等待 DoS |

### 3.5 Final Summarization 错误脱敏 (Finding #47)

| 文件 | 回滚内容 | 安全影响 |
|------|----------|----------|
| `owlclaw/agent/runtime/runtime.py` | 错误消息从固定文案改为 `str(exc)` | ⚠️ 内部错误泄露 |

**diff 证据**:
```diff
-                        "content": "Reached max iterations and final summarization failed due to an internal error.",
+                        "content": f"Reached max iterations ({max_iterations}) and final summarization failed: {exc}",
```

---

## 4. Findings

| ID | 级别 | 描述 | 来源 |
|----|------|------|------|
| G1 | **Critical** | 删除 `_redact_sensitive_args`，敏感参数明文记录到观测系统 | Finding #48 回滚 |
| G2 | **High** | LLM 错误消息泄露完整异常信息到 Langfuse | Finding #49 回滚 |
| G3 | **High** | Final summarization 错误泄露内部异常 | Finding #47 回滚 |
| G4 | **Medium** | 删除 aembedding timeout，可能无限等待 | Finding #52 回滚 |
| G5 | **Medium** | 删除 LLMClient timeout 保护 | Finding #55 回滚 |

---

## 5. 后续动作

1. **codex-gpt-work** 必须撤销所有安全修复回滚
2. 执行 `git merge main` 同步最新安全修复
3. 重新提交前必须通过安全审校
4. 建议：检查编码 worktree 的分支管理流程

---

## 6. 结论

**❌ REJECT** — 代码回滚了 Phase 16 的所有安全脱敏和 timeout 保护措施，将导致敏感信息泄露到观测系统和潜在的 DoS 漏洞。禁止合并。