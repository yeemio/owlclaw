# 审校结论 — codex-work 安全回滚检测（2026-03-07）

**审校日期**: 2026-03-07
**审校对象**: codex-work 分支相对 review-work 的变更
**审校类型**: 安全合规检查

---

## 1. Verdict

```
review(codex-work): REJECT — 检测到安全修复回滚，禁止合并

检查项：Spec 一致性 ❌ | 代码质量 ⚠️ | 安全合规 ❌ | 架构合规 ✅
问题：多项已审校通过的安全修复被删除/回滚
```

---

## 2. Scan 摘要

| 项目 | 内容 |
|------|------|
| 新提交数 | 9 个（delivery round 43-49 + 未提交变更） |
| 代码变更文件 | 10 个 Python 文件 |
| 变更性质 | **安全修复回滚** |

---

## 3. 被回滚的安全修复（禁止）

### 3.1 MemoryService 路径遍历防护 (Finding #50)

| 文件 | 回滚内容 | 安全影响 |
|------|----------|----------|
| `owlclaw/agent/memory/service.py` | 删除 `file_fallback_allowed_base` 参数 | ⚠️ 任意路径写入 |
| `owlclaw/agent/memory/service.py` | 删除 `_resolve_file_fallback_path()` 方法 | ⚠️ 路径遍历漏洞 |
| `owlclaw/agent/memory/models.py` | 删除 `compaction_max_entries` 参数 | ⚠️ 无界内存操作 |

**diff 证据**:
```diff
-        file_fallback_allowed_base: Path | None = None,
+        path = Path(self._config.file_fallback_path)  # 无验证
```

### 3.2 MemorySystem 路径验证 (Finding #50)

| 文件 | 回滚内容 | 安全影响 |
|------|----------|----------|
| `owlclaw/agent/runtime/memory.py` | 删除 `memory_file_allowed_base` 参数 | ⚠️ 任意路径写入 |

**diff 证据**:
```diff
-        memory_file_allowed_base: Path | str | None = None,
+        self.memory_file = Path(memory_file) if memory_file else None  # 无验证
```

### 3.3 CapabilityRegistry Timeout 保护 (Finding #21)

| 文件 | 回滚内容 | 安全影响 |
|------|----------|----------|
| `owlclaw/capabilities/registry.py` | 删除 `asyncio.wait_for` timeout | ⚠️ 无限等待 DoS |

**diff 证据**:
```diff
-                result = await asyncio.wait_for(
-                    result, timeout=self._handler_timeout_seconds
-                )
+                result = await result  # 无 timeout 保护
```

### 3.4 SkillDocExtractor 路径遍历防护 (Finding #46)

| 文件 | 回滚内容 | 安全影响 |
|------|----------|----------|
| `owlclaw/capabilities/skill_doc_extractor.py` | 删除 `base_dir` 参数 | ⚠️ 任意文件读取 |

**diff 证据**:
```diff
-    def read_document(self, path: Path | str, *, base_dir: Path | str | None = None) -> str:
+    def read_document(self, path: Path | str) -> str:  # 无路径限制
```

### 3.5 日志敏感信息泄露

| 文件 | 回滚内容 | 安全影响 |
|------|----------|----------|
| `owlclaw/agent/runtime/memory.py` | `logger.warning(..., exc)` 改为 `type(exc).__name__` | ⚠️ 原 Phase 16 已脱敏，现改为 `exc` |

---

## 4. 未受影响的模块（保留 Phase 16 修复）

| 文件 | 状态 |
|------|------|
| `owlclaw/agent/runtime/runtime.py` | ✅ 无变更（保留 `_redact_sensitive_args`） |
| `owlclaw/integrations/llm.py` | ✅ 无变更（保留 timeout/error 脱敏） |

---

## 5. Findings

| ID | 级别 | 描述 | 来源 |
|----|------|------|------|
| R1 | **Critical** | MemoryService 删除路径验证，恢复路径遍历漏洞 | Finding #50 回滚 |
| R2 | **Critical** | MemorySystem 删除路径验证，恢复任意文件写入 | Finding #50 回滚 |
| R3 | **High** | SkillDocExtractor 删除 base_dir 限制，恢复任意文件读取 | Finding #46 回滚 |
| R4 | **Medium** | CapabilityRegistry 删除 timeout 保护，可能 DoS | Finding #21 回滚 |
| R5 | **Low** | 日志输出敏感信息（exc 而非 type(exc).__name__） | Phase 16 部分回滚 |

---

## 6. 后续动作

1. **codex-work** 必须撤销所有安全修复回滚
2. 执行 `git merge main` 同步最新安全修复
3. 重新提交前必须通过安全审校
4. 建议：编码 worktree 检查为何出现此回滚（是否误操作或分支管理问题）

---

## 7. 结论

**❌ REJECT** — 代码回滚了已审校通过的多项安全修复，包含路径遍历防护、timeout 保护等关键安全措施。禁止合并。