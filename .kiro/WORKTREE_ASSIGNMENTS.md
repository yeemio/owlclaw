# Worktree 任务分配

> **角色**: 多 Worktree 并行开发的任务分配唯一真源  
> **更新者**: 人工（或 Cursor 辅助）  
> **最后更新**: 2026-02-23

---

## 规则

1. **AI Agent 启动时必须读取本文件**，确认自己所在 worktree 的当前任务分配
2. **只做分配给自己的 spec/模块**，不越界
3. **任务分配由人工更新**，AI Agent 不得自行修改本文件
4. **两个编码 worktree 的 spec 不得重叠**，避免合并冲突
5. 分配变更后，人工通知各 worktree 同步（`git merge main`）

---

## 当前分配

### owlclaw-review（审校）

| 字段 | 值 |
|------|---|
| 目录 | `D:\AI\owlclaw-review\` |
| 分支 | `review-work` |
| 角色 | 审校：spec 对齐、code review、文档修正 |

**当前任务**：

- [ ] Spec 规范化审计：检查所有进行中 spec 的 requirements/design/tasks 与架构文档、代码实现的一致性
- [ ] SPEC_TASKS_SCAN 状态校准：核实各 spec 的 (checked/total) 是否与 tasks.md 实际勾选一致
- [ ] 代码质量审查：检查已实现模块的类型注解、错误处理、测试覆盖

**范围限制**：全仓库只读审查 + 轻量修正（文档、注释、类型注解）。不做功能实现。

---

### owlclaw-codex（编码 1）

| 字段 | 值 |
|------|---|
| 目录 | `D:\AI\owlclaw-codex\` |
| 分支 | `codex-work` |
| 角色 | 编码：功能实现 + 测试 |

**当前分配的 spec**：

| Spec | 进度 | 涉及路径 |
|------|------|---------|
| database-core | 24/30 | `owlclaw/db/**`, `tests/unit/test_db*.py`, `migrations/` |
| cli-db | 17/53 | `owlclaw/cli/db*.py`, `tests/unit/test_cli_db*.py` |

**禁止触碰**（分配给编码 2 的路径）：

- `owlclaw/security/**`
- `owlclaw/integrations/llm/**`
- `owlclaw/config/**`

---

### owlclaw-codex-gpt（编码 2）

| 字段 | 值 |
|------|---|
| 目录 | `D:\AI\owlclaw-codex-gpt\` |
| 分支 | `codex-gpt-work` |
| 角色 | 编码：功能实现 + 测试 |

**当前分配的 spec**：

| Spec | 进度 | 涉及路径 |
|------|------|---------|
| security | 27/44 | `owlclaw/security/**`, `tests/unit/security/**` |
| integrations-llm | 127/128 | `owlclaw/integrations/llm/**`, `tests/unit/integrations/llm/**` |
| configuration | 0/12 | `owlclaw/config/**`, `tests/unit/test_config*.py` |

**禁止触碰**（分配给编码 1 的路径）：

- `owlclaw/db/**`
- `owlclaw/cli/db*.py`
- `migrations/`

---

## 分配历史

| 日期 | 变更 | 原因 |
|------|------|------|
| 2026-02-23 | 初始分配 | 建立 4 worktree 并行架构 |

---

## 下一轮待分配（人工决定后填入上方）

以下 spec 尚未分配到任何编码 worktree，等当前批次完成后按优先级分配：

**Phase 1 剩余**（优先）：
- agent-runtime (19/105)
- agent-tools (46/139)
- governance (130/173)
- triggers-cron (39/92)
- integrations-hatchet (138/147)
- capabilities-skills (107/108)
- skill-templates (92/149)

**Phase 2**（次优先）：
- triggers-webhook, triggers-queue, triggers-db-change, triggers-api, triggers-signal
- integrations-langfuse, integrations-langchain
- cli-scan, owlhub, mcp-server, examples

**Phase 3**（后续）：
- cli-migrate, release, ci-setup, e2e-validation
