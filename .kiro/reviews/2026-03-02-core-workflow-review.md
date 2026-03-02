# 核心工作流更新审校（2026-03-02）

## 范围
- `.cursor/rules/owlclaw_core.mdc`
- `.kiro/WORKTREE_ASSIGNMENTS.md`
- `docs/WORKTREE_GUIDE.md`（一致性抽查）

## 结论
- `FIX_NEEDED`（文档规则存在互相冲突）

## Findings（按严重度）

### 1) 开发命令规范冲突（P1）
- `owlclaw_core.mdc` 统筹循环 Step 6 写法为：`git add -A && git commit -m ...`
- 但 `owlclaw_development.mdc` 明确禁止将 `git add` 与 `git commit` 组合在同一命令。
- 同一仓库内出现互斥指令，执行者无法同时满足两条规则。

受影响位置：
- `.cursor/rules/owlclaw_core.mdc`（Orchestrator Loop Step 6）
- `.cursor/rules/owlclaw_development.mdc`（Git 规范 4.1）

建议修复：
- 将 `owlclaw_core.mdc` Step 6 改为两行：
  - `git add -A`
  - `git commit -m "..."`

### 2) 日志规范冲突（P1）
- `WORKTREE_ASSIGNMENTS.md` 的审校清单要求“日志使用 structlog”。
- 但 `owlclaw_principles.mdc` 明确规定生产代码统一使用 Python 标准库 `logging`，且不引入第三方日志库。
- 审校标准与核心编码规范冲突，会导致审校结论不稳定。

受影响位置：
- `.kiro/WORKTREE_ASSIGNMENTS.md`（Review 检查清单）
- `.cursor/rules/owlclaw_principles.mdc`（统一日志章节）

建议修复：
- 将审校清单中的“structlog”统一替换为“Python stdlib logging”。

## 说明
- 本次审校针对“核心工作流更新”文档一致性，不涉及功能代码质量判定。
- 编码分支当前处于 `WORKING`，存在进行中未提交改动，属于执行态，不纳入本次文档冲突判定。
