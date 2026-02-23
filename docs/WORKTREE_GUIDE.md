# 多 AI Agent Worktree 协作指南

> **版本**: v1.0.0  
> **创建日期**: 2026-02-23  
> **状态**: 🔴 必读规范（所有 AI Agent 在开始工作前必须阅读本文档）  
> **适用工具**: Cursor、Codex-CLI、以及任何未来接入的 AI 编码工具

---

## 一、架构概览

本项目使用 **Git Worktree** 实现多 AI Agent 物理隔离，避免工作区文件冲突。

```
D:\AI\owlclaw\          ← 主 worktree（main 分支）
D:\AI\owlclaw-codex\    ← Codex worktree（codex-work 分支）
```

两个目录共享同一个 `.git` 仓库（历史、分支、远程全部共享），但文件系统完全独立。在一个 worktree 中的编辑不会影响另一个 worktree 的文件。

```
┌─────────────────────────────┐    ┌─────────────────────────────┐
│  D:\AI\owlclaw\             │    │  D:\AI\owlclaw-codex\       │
│  ┌───────────────────────┐  │    │  ┌───────────────────────┐  │
│  │ Cursor / 人工          │  │    │  │ Codex-CLI             │  │
│  │ 分支: main             │  │    │  │ 分支: codex-work      │  │
│  │ 角色: 交互式开发/review │  │    │  │ 角色: 批量/自主实现    │  │
│  └───────────────────────┘  │    │  └───────────────────────┘  │
│          独立文件系统         │    │         独立文件系统         │
└──────────────┬──────────────┘    └──────────────┬──────────────┘
               │                                   │
               └──────────┬───────────────────────┘
                          │
                ┌─────────▼─────────┐
                │   共享 .git 仓库   │
                │  （历史/分支/远程） │
                └───────────────────┘
```

---

## 二、身份识别 — 你在哪个 Worktree？

**AI Agent 在开始任何工作前，必须确认自己所在的 worktree。**

运行以下命令判断：

```bash
git worktree list
```

输出示例：

```
D:/AI/owlclaw        <hash> [main]
D:/AI/owlclaw-codex  <hash> [codex-work]
```

判断规则：
- 当前工作目录在 `D:\AI\owlclaw\` 下 → 你在**主 worktree**，使用 `main` 分支
- 当前工作目录在 `D:\AI\owlclaw-codex\` 下 → 你在 **Codex worktree**，使用 `codex-work` 分支

**禁止**：在一个 worktree 中切换到另一个 worktree 正在使用的分支（Git 会拒绝，但不要尝试）。

---

## 三、工作规则

### 3.1 通用规则（两个 worktree 都适用）

- **只在自己的 worktree 中编辑文件**，不要跨目录操作
- **正常 commit 到自己的分支**，commit 规范不变（见 `AGENTS.md`）
- **Spec 体系不变**：三层文档结构、SPEC_TASKS_SCAN、Spec 循环流程全部照旧
- **规则文件不变**：`.cursor/rules/*.mdc` 的所有规范继续生效
- **合并由人工决定**：完成一批工作后，由人工（或 Cursor 辅助）决定何时合并

### 3.2 主 Worktree（`D:\AI\owlclaw\`，main 分支）

- **使用者**：Cursor、人工
- **适合的工作**：交互式开发、复杂重构、设计讨论、code review、合并操作
- **分支策略**：直接在 `main` 上工作，或按需创建 feature 分支

### 3.3 Codex Worktree（`D:\AI\owlclaw-codex\`，codex-work 分支）

- **使用者**：Codex-CLI
- **适合的工作**：批量实现、测试补全、文档生成、Spec 循环自主推进
- **分支策略**：在 `codex-work` 分支上工作，完成后等待合并到 `main`

---

## 四、协调流程

### 4.1 日常工作流

```
1. AI Agent 启动
   ↓
2. 确认自己在哪个 worktree（见第二节）
   ↓
3. 拉取最新代码：git pull origin main（或 git merge main）
   ↓
4. 在自己的 worktree 中正常工作、commit
   ↓
5. 工作完成后通知人工（或在 commit message 中标注）
```

### 4.2 合并流程（由人工或 Cursor 执行）

```bash
# 在主 worktree 中操作
cd D:\AI\owlclaw

# 查看 codex-work 分支的变更
git log main..codex-work --oneline

# 合并 codex-work 到 main
git merge codex-work

# 如果有冲突，解决后 commit
# git add . && git commit

# 合并完成后，codex worktree 同步 main
cd D:\AI\owlclaw-codex
git merge main
```

### 4.3 保持同步

Codex worktree 需要定期同步 main 的最新变更，避免分支偏离过远：

```bash
# 在 codex worktree 中
cd D:\AI\owlclaw-codex
git merge main
```

**建议频率**：每次开始新一轮 Spec 循环前同步一次。

### 4.4 冲突处理

- **预防**：两个 worktree 尽量工作在不同的 spec/模块上（通过 SPEC_TASKS_SCAN 的批次分配自然实现）
- **检测**：合并时 Git 会自动报告冲突文件
- **解决**：由人工或 Cursor 在主 worktree 中解决冲突
- **原则**：谁后合并谁负责解决冲突

---

## 五、Spec 循环适配

### 5.1 替代 AGENT_WORK_CLAIMS.md

原来的 `.kiro/AGENT_WORK_CLAIMS.md` 文件级 claim 机制**已被 worktree 物理隔离替代**。

- **不再需要**：读写 AGENT_WORK_CLAIMS.md、声明/释放 claim
- **自然隔离**：两个 worktree 各自编辑自己的文件副本，不存在文件级冲突
- **冲突后移**：冲突从"编辑时"后移到"合并时"，在人工控制下解决

### 5.2 Spec 循环中的"多 AI 协作"规则变更

**旧规则**（已废弃）：
> 若某 task 涉及的文件在工作区中已被修改（git status 显示该文件被他人/其他会话改动），则跳过该 task。

**新规则**：
> 每个 AI Agent 在自己的 worktree 中独立工作，无需检查文件是否被其他 Agent 修改。Spec 循环正常推进，不跳过任何 task。合并时的冲突由人工解决。

### 5.3 SPEC_TASKS_SCAN 的使用

两个 worktree 各自有一份 `SPEC_TASKS_SCAN.md` 的副本。更新规则：

- 各自在自己的副本中更新 Checkpoint
- 合并时以最新进度为准（人工判断）
- 建议：主 worktree 的 SPEC_TASKS_SCAN 为权威版本，codex worktree 合并后以 main 为准

---

## 六、常用命令速查

```bash
# 查看所有 worktree
git worktree list

# 在 codex worktree 中同步 main 最新代码
cd D:\AI\owlclaw-codex && git merge main

# 在主 worktree 中合并 codex-work
cd D:\AI\owlclaw && git merge codex-work

# 查看 codex-work 相对于 main 的变更
git log main..codex-work --oneline
git diff main..codex-work --stat

# 删除 worktree（如果不再需要）
git worktree remove D:\AI\owlclaw-codex

# 重新创建 worktree（如果需要重建）
git worktree add -b codex-work D:\AI\owlclaw-codex main
```

---

## 七、故障排除

### Q: Git 报错 "fatal: '<branch>' is already checked out at '<path>'"
**A**: 不能在两个 worktree 中同时 checkout 同一个分支。每个 worktree 必须在不同分支上。

### Q: Codex worktree 落后 main 太多，合并冲突很多
**A**: 定期在 codex worktree 中运行 `git merge main` 保持同步。建议每轮 Spec 循环开始前同步。

### Q: 需要增加第三个 AI Agent
**A**: 创建新 worktree：`git worktree add -b <branch-name> D:\AI\owlclaw-<name> main`，然后在本文档中添加对应条目。

### Q: 想让 Codex-CLI 在不同分支上做不同 spec
**A**: 可以为 codex worktree 切换分支（先 commit 当前工作），或创建多个 codex worktree。

---

**维护者**: yeemio  
**下次审核**: 2026-03-01
