# Delivery — Phase 16 audit-deep-remediation-followup (codex-gpt-work)

> **Worktree**: owlclaw-codex-gpt  
> **Branch**: codex-gpt-work  
> **Scope**: DEEP_AUDIT_REPORT.md #45, #46, #50, #51, #53, #54  
> **Date**: 2026-03-07

---

## 交付摘要

| Finding | 描述 | 修改路径 | 验收 |
|---------|------|----------|------|
| #45 | CapabilityRegistry.get_state 异步 state provider timeout | `owlclaw/capabilities/registry.py` | get_state 使用 `asyncio.wait_for(result, timeout=self._handler_timeout_seconds)`；单测 `test_get_state_async_provider_timeout` 通过 |
| #46 | SkillDocExtractor.read_document path 限制在 base_dir 下 | `owlclaw/capabilities/skill_doc_extractor.py` | `read_document(path, *, base_dir=None)` 增加 base_dir 校验，path 须在 base_dir 内；单测 `test_skill_doc_extractor_read_document_base_dir_*` 通过 |
| #50 | MemoryService file_fallback_path 校验 | `owlclaw/agent/memory/service.py` | `_resolve_file_fallback_path(raw, *, allowed_base)` 确保 path 在 allowed_base 下；构造时传入 `file_fallback_allowed_base` |
| #51 | compact 单次加载上限（compaction_max_entries） | `owlclaw/agent/memory/service.py` + `models.py` | `compact()` 使用 `limit=cap`（config.compaction_max_entries），默认 10_000、上限 100_000；单测通过 |
| #53 | MemorySystem memory_file 路径校验 | `owlclaw/agent/runtime/memory.py` | `memory_file_allowed_base` 构造参数，path 须在 base 下；单测 `test_long_term_*` / `test_memory_file_*` 覆盖 |
| #54 | _index_entry 日志脱敏（不 log str(exc)） | `owlclaw/agent/runtime/memory.py` | `_index_entry` except 分支仅 log `type(exc).__name__`，不暴露 str(exc) |

---

## 提交范围

- **main..HEAD**: 见 `git log main..codex-gpt-work --oneline`
- **关键 commit**:
  - `e8766ea9` fix(capabilities): #45 get_state timeout; #46 SkillDocExtractor path under base_dir
  - `9e426687` fix(memory): #50 file_fallback_path validation; #51 compact cap; #53 memory_file base; #54 index log sanitize

---

## 测试结果

- **registry + memory 相关**: `pytest tests/unit/test_registry.py tests/unit/agent/memory/test_memory_service.py tests/unit/agent/test_runtime_memory.py` → **54 passed**
- **skill_doc_extractor**: `tests/unit/capabilities/test_skill_doc_extractor.py` 含 #46 的 base_dir 用例，通过
- **全量**: `pytest tests/` 有 1 失败 — `test_http_binding_executor_integration_chain`（HTTP binding allowed_hosts，非本批修改范围，属 codex-work D15 相关集成环境）

---

## 审校建议

1. Spec 一致性：与 `docs/review/DEEP_AUDIT_REPORT.md` #45/#46/#50/#51/#53/#54 描述对照。
2. 代码质量：类型注解、绝对导入、无 TODO、logger 使用 type(exc).__name__ 等。
3. 架构：未触碰 codex-work 独占路径（config/models.py、security/、webhook 等）。

---

**状态**: 交付完成，待 review-work 审校合并。
