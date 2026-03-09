# 审校结论 — codex-work / codex-gpt-work 安全回滚检测（2026-03-07 Round 2）

**审校日期**: 2026-03-07
**审校对象**: codex-work、codex-gpt-work 分支最新提交
**审校类型**: 安全回滚检测

---

## 1. Scan 摘要

| 分支 | 相对 review-work 变更 | 提交类型 | 代码变更 |
|------|----------------------|----------|----------|
| codex-work | 删除 1469 行代码 | 大规模回滚 | **严重：安全修复被删除** |
| codex-gpt-work | 与 codex-work 相同 | 大规模回滚 | **严重：安全修复被删除** |

---

## 2. 安全回滚清单

### 2.1 codex-work 回滚（Phase 16 #47/#48/#49/#52/#55）

| 文件 | 回滚内容 | 原修复 | 风险级别 |
|------|----------|--------|----------|
| `runtime.py` | 删除 `_redact_sensitive_args()` | Observation 工具参数脱敏 | **Critical** |
| `runtime.py` | `_observe_tool` 不使用 `safe_payload` | 敏感数据发送到 Langfuse | **Critical** |
| `memory/service.py` | 删除 `_resolve_file_fallback_path()` | 路径遍历防护 (#50) | **High** |
| `memory/service.py` | 删除 `file_fallback_allowed_base` 参数 | 路径验证 | **High** |
| `registry.py` | 删除 `asyncio.wait_for` timeout | State provider 超时保护 | **Medium** |
| `config.py` | 删除 `skill_env_allowlist` 配置 | 环境变量安全 | **Medium** |

### 2.2 codex-gpt-work 回滚（Phase 16 #45/#46/#50/#51/#53/#54）

| 文件 | 回滚内容 | 原修复 | 风险级别 |
|------|----------|--------|----------|
| `llm.py` | `aembedding()` 删除 `timeout_seconds` | 嵌入 API 超时保护 | **High** |
| `llm.py` | `LLMClient.complete()` 删除 `timeout_seconds` | LLM 调用超时保护 | **High** |
| `llm.py` | `error_message` 改为 `str(exc)` | 错误信息泄露敏感数据 | **Critical** |
| `llm.py` | trace output 改为 `str(e)` | Langfuse trace 泄露错误 | **Critical** |

---

## 3. 代码证据

### 3.1 runtime.py 安全函数删除

```diff
-    _SENSITIVE_ARG_SUBSTRINGS = ("password", "api_key", "token", "secret", "credential", "auth")
-
     @staticmethod
-    def _redact_sensitive_args(args: dict[str, Any]) -> dict[str, Any]:
-        """Redact values for keys that look sensitive before sending to observability."""
-        ...
```

### 3.2 llm.py 错误信息泄露

```diff
-                        "error_message": "LLM call failed",
+                        "error_message": str(exc),
```

### 3.3 memory/service.py 路径验证删除

```diff
-    @staticmethod
-    def _resolve_file_fallback_path(raw: str, *, allowed_base: Path) -> Path:
-        """Resolve file_fallback_path and ensure it is under allowed_base (Finding #50)."""
-        ...
```

### 3.4 registry.py 超时保护删除

```diff
-                result = await asyncio.wait_for(
-                    result, timeout=self._handler_timeout_seconds
-                )
+                result = await result
```

---

## 4. Verdict

```
review(codex-work/codex-gpt-work): REJECT — 安全修复回滚检测

检查项：代码变更 ❌（回滚安全修复）| 测试 ❌（删除测试）| 安全覆盖 ❌（严重回滚）

问题：
1. codex-work 回滚 Phase 16 #47/#48/#49/#52/#55 全部安全修复
2. codex-gpt-work 回滚 Phase 16 #45/#46/#50/#51/#53/#54 全部安全修复
3. 删除 1469 行代码，包括安全测试
4. 删除 workflow_* 脚本文件

风险：
- 敏感数据（API key, password, token）泄露到 Langfuse observability
- 错误信息泄露 LLM 调用详情
- 路径遍历漏洞可被利用
- 无超时保护可能导致资源耗尽

行动：编码分支必须重新合并 review-work，恢复安全修复
```

---

## 5. 新 Findings

| ID | 级别 | 描述 | 文件 | 建议 |
|----|------|------|------|------|
| R1 | **Critical** | Observation 工具参数未脱敏，敏感数据发送到 Langfuse | `runtime.py:319` | 恢复 `_redact_sensitive_args` |
| R2 | **Critical** | 错误消息使用 `str(exc)` 泄露 LLM 调用详情 | `llm.py:232` | 恢复 `"LLM call failed"` |
| R3 | **Critical** | Langfuse trace output 使用 `str(e)` 泄露错误 | `llm.py:712` | 恢复 `"LLM call failed"` |
| R4 | **High** | 路径遍历防护删除 | `memory/service.py` | 恢复 `_resolve_file_fallback_path` |
| R5 | **High** | 嵌入 API 无超时保护 | `llm.py:aembedding` | 恢复 `timeout_seconds` 参数 |
| R6 | **High** | LLM 调用无超时保护 | `llm.py:LLMClient` | 恢复 `timeout_seconds` 参数 |
| R7 | **Medium** | State provider 无超时保护 | `registry.py` | 恢复 `asyncio.wait_for` |
| R8 | **Medium** | 删除安全相关测试文件 | `tests/unit/*.py` | 恢复测试 |

---

## 6. 后续动作

1. **编码分支**：
   - 执行 `git merge review-work` 或 `git merge main`
   - 确认所有 Phase 16 安全修复已恢复
   - 运行测试验证

2. **验证清单**：
   - [ ] `_redact_sensitive_args` 存在于 `runtime.py`
   - [ ] `safe_payload` 在 `_observe_tool` 中使用
   - [ ] `timeout_seconds` 参数存在于 `llm.py`
   - [ ] `"LLM call failed"` 作为错误消息
   - [ ] `_resolve_file_fallback_path` 存在于 `memory/service.py`
   - [ ] `asyncio.wait_for` 存在于 `registry.py`

3. **review-work**：
   - 保持当前状态
   - 等待编码分支修复后重新提交