# WORKTREE_ASSIGNMENTS.md Template

Use this template when setting up multi-agent orchestration for a new project
or restructuring an existing assignment file.

---

```markdown
# Worktree 任务分配

> **角色**: 多 Worktree 并行开发的任务分配唯一真源
> **更新者**: 人工（或 Cursor 辅助）
> **最后更新**: [date]

---

## 规则

1. AI Agent 启动时必须读取本文件，确认自己所在 worktree 的当前任务分配
2. 只做分配给自己的 spec/模块，不越界
3. 任务分配由人工更新，AI Agent 不得自行修改本文件
4. 两个编码 worktree 的 spec 不得重叠，避免合并冲突
5. 分配变更后，人工通知各 worktree 同步（`git merge main`）
6. **零残留规则**：每轮工作结束时，必须 commit 所有变更，工作目录必须干净
7. **工作状态标记**：IDLE / WORKING / DONE
8. **契约先行规则**：多层并行开发必须先输出共享契约

---

## 当前分配

### [project-name]（主 worktree — 统筹 + 编码）

| 字段 | 值 |
|------|---|
| 目录 | `D:\AI\[project]\` |
| 分支 | `main` |
| 角色 | **统筹指挥 + 复杂编码** |

**统筹职责**：
- 更新本文件，分配和调整各 worktree 的任务
- 将 `review-work` 合并到 `main`
- 解决合并冲突
- 监控各 worktree 进度

**当前编码任务**：[description]

---

### [project-name]-review（审校 — 技术经理角色）

| 字段 | 值 |
|------|---|
| 目录 | `D:\AI\[project]-review\` |
| 分支 | `review-work` |
| 角色 | **技术经理**：代码终审 + 合并把关 |

**审校循环（Review Loop）**：
[Include the full Review Loop definition from SKILL.md Part 3]

**Review 检查清单**：
[Include the full checklist from SKILL.md Part 3.2]

---

### [project-name]-codex（编码 1）

| 字段 | 值 |
|------|---|
| 目录 | `D:\AI\[project]-codex\` |
| 分支 | `codex-work` |
| 角色 | 编码：功能实现 + 测试 |
| 工作状态 | `IDLE` |

**当前分配的 spec**：

| Spec | 进度 | 涉及路径 |
|------|------|---------|
| [spec-name] | [N/M] | [file paths] |

**禁止触碰**（分配给编码 2 的独占路径）：
- [list of paths]

---

### [project-name]-codex-gpt（编码 2）

| 字段 | 值 |
|------|---|
| 目录 | `D:\AI\[project]-codex-gpt\` |
| 分支 | `codex-gpt-work` |
| 角色 | 编码：功能实现 + 测试 |
| 工作状态 | `IDLE` |

**当前分配的 spec**：

| Spec | 进度 | 涉及路径 |
|------|------|---------|
| [spec-name] | [N/M] | [file paths] |

**禁止触碰**（分配给编码 1 的独占路径）：
- [list of paths]

---

## 共享文件修改范围约定

| 共享文件 | 编码 1 修改范围 | 编码 2 修改范围 |
|---------|---------------|---------------|
| [file path] | [specific functions/sections] | [specific functions/sections] |

---

## 跨 Spec 依赖提示

| 源 Spec | 影响 Spec | 影响内容 | 状态 |
|---------|----------|---------|------|
| [spec] | [spec] | [description] | [active/resolved] |

---

## Agent 共享信箱

### 活跃消息

| 时间 | 发送方 | 接收方 | 消息 | 状态 |
|------|--------|--------|------|------|
| _(暂无)_ | | | | |

### 已归档消息

<details>
<summary>点击展开历史消息</summary>

| 时间 | 发送方 | 接收方 | 消息 | 结果 |
|------|--------|--------|------|------|
| _(暂无)_ | | | | |

</details>

---

## 下一轮待分配

| Spec | Tasks | 优先级 | 备注 |
|------|-------|--------|------|
| [spec-name] | [N] | [P0/P1/P2] | [notes] |

---

## 分配历史

| 日期 | 变更 | 原因 |
|------|------|------|
| [date] | [what changed] | [why] |
```
