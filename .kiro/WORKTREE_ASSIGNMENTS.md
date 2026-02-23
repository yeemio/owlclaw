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

### owlclaw-review（审校 — 技术经理角色）

| 字段 | 值 |
|------|---|
| 目录 | `D:\AI\owlclaw-review\` |
| 分支 | `review-work` |
| 角色 | **技术经理**：代码终审 + 合并把关 + spec 对齐 + 质量守门 |

**职责定义**：

审校 worktree 是所有编码产出进入 main 的**最后一道关卡**。编码 worktree 的变更必须经过审校确认后才能合并。

**审校循环（Review Loop）**：

审校 worktree 运行独立的循环流程，触发词与 Spec 循环相同（`继续`、`自主推进` 等）：

```
1. Sync — git merge main，获取最新 main 状态
   ↓
2. Scan — 检查各编码分支是否有待审变更
   - git log main..codex-work --oneline
   - git log main..codex-gpt-work --oneline
   若无新变更 → 执行常规审校任务（见下方）→ 回 1
   ↓
3. Review — 对每个有变更的编码分支：
   a. 读取该分支的 commit log 和 diff（git diff main..codex-work）
   b. Spec 一致性：变更是否符合对应 spec 的 design.md 和 tasks.md
   c. 代码质量：类型注解、错误处理、命名规范、绝对导入
   d. 测试覆盖：新代码是否有对应测试、测试是否通过
   e. 架构合规：是否违反 owlclaw_architecture.mdc 的包边界和集成隔离
   f. 禁令检查：无 TODO/FIXME、无假数据、无硬编码业务规则
   ↓
4. Verdict — 对每个分支给出结论：
   - ✅ APPROVE：可以合并，在 commit message 中记录审校结论
   - 🔧 FIX_NEEDED：列出具体问题，在 review-work 分支上提交修正建议
     （或直接在 review-work 上修复轻量问题，合并时一并带入）
   - ❌ REJECT：严重问题（架构违规、数据安全），标记原因，等人工裁决
   ↓
5. Merge（仅 APPROVE 的分支）— 在 review worktree 中执行：
   - git merge codex-work（或 codex-gpt-work）
   - 运行 poetry run pytest 确认合并后测试通过
   - 若测试失败 → 回滚合并，标记 FIX_NEEDED
   - 若测试通过 → commit 合并结果
   ↓
6. Report — 更新 SPEC_TASKS_SCAN 的 Checkpoint，记录：
   - 本轮审校了哪些分支/spec
   - 审校结论（APPROVE/FIX_NEEDED/REJECT）
   - 合并状态
   ↓
7. Push to main — 将 review-work 的审校+合并结果推送到 main：
   - 切换到主 worktree 合并 review-work，或由人工执行
   - 通知各编码 worktree 同步：git merge main
```

**常规审校任务**（无编码分支变更时执行）：

- [ ] Spec 规范化审计：检查进行中 spec 的 requirements/design/tasks 与架构文档、代码实现的一致性
- [ ] SPEC_TASKS_SCAN 状态校准：核实各 spec 的 (checked/total) 是否与 tasks.md 实际勾选一致
- [ ] 代码质量审查：检查已实现模块的类型注解、错误处理、测试覆盖
- [ ] 架构漂移检测：代码实现是否偏离 docs/ARCHITECTURE_ANALYSIS.md

**权限**：全仓库读 + 轻量修正（文档、注释、类型注解、测试补全）。不做功能实现。可以在 review-work 分支上直接修复审校发现的轻量问题。

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
