# 多 AI Agent Worktree 协作指南

> **版本**: v1.0.0  
> **创建日期**: 2026-02-23  
> **状态**: 🔴 必读规范（所有 AI Agent 在开始工作前必须阅读本文档）  
> **适用工具**: Cursor、Codex-CLI、以及任何未来接入的 AI 编码工具

---

## 一、架构概览

本项目使用 **Git Worktree** 实现多 AI Agent 物理隔离，避免工作区文件冲突。

```
D:\AI\owlclaw\              ← 主 worktree（main 分支）— Cursor / 人工
D:\AI\owlclaw-review\       ← 审校 worktree（review-work 分支）— Codex-CLI 审校
D:\AI\owlclaw-codex\        ← 编码 worktree 1（codex-work 分支）— Codex-CLI 编码
D:\AI\owlclaw-codex-gpt\    ← 编码 worktree 2（codex-gpt-work 分支）— Codex-CLI 编码
```

所有目录共享同一个 `.git` 仓库（历史、分支、远程全部共享），但文件系统完全独立。在一个 worktree 中的编辑不会影响其他 worktree 的文件。

```
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ owlclaw\         │ │ owlclaw-review\  │ │ owlclaw-codex\   │ │ owlclaw-codex-gpt│
│ Cursor / 人工     │ │ Codex-CLI 审校   │ │ Codex-CLI 编码1  │ │ Codex-CLI 编码2  │
│ main             │ │ review-work      │ │ codex-work       │ │ codex-gpt-work   │
└────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘
         │                    │                     │                    │
         └────────────────────┴──────────┬──────────┴────────────────────┘
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
D:/AI/owlclaw            <hash> [main]
D:/AI/owlclaw-review     <hash> [review-work]
D:/AI/owlclaw-codex      <hash> [codex-work]
D:/AI/owlclaw-codex-gpt  <hash> [codex-gpt-work]
```

判断规则：

| 当前工作目录 | Worktree | 分支 | 角色 |
|-------------|----------|------|------|
| `D:\AI\owlclaw\` | 主 worktree | `main` | Cursor / 人工交互式开发 |
| `D:\AI\owlclaw-review\` | 审校 worktree | `review-work` | Codex-CLI 审校（spec 对齐、code review、文档修正） |
| `D:\AI\owlclaw-codex\` | 编码 worktree 1 | `codex-work` | Codex-CLI 编码（功能实现、测试编写） |
| `D:\AI\owlclaw-codex-gpt\` | 编码 worktree 2 | `codex-gpt-work` | Codex-CLI 编码（功能实现、测试编写） |

**禁止**：在一个 worktree 中切换到另一个 worktree 正在使用的分支（Git 会拒绝，但不要尝试）。

---

## 三、工作规则

### 3.0 环境准备与启动

**虚拟环境**：每个 worktree 需要独立的 `.venv`。新建 worktree 后必须执行：

```bash
cd D:\AI\owlclaw-<name>
poetry install
```

Poetry 有依赖缓存，重复安装很快（几秒到一分钟）。

**Codex CLI 启动**：在 Windows 上使用 **PowerShell**（不要用 CMD）。全局配置已设置 `approval_mode = "full-auto"`（`~/.codex/config.toml`），Codex CLI 启动后自动执行，无需逐条确认。

```powershell
# 审校
cd D:\AI\owlclaw-review
codex

# 编码 1
cd D:\AI\owlclaw-codex
codex

# 编码 2
cd D:\AI\owlclaw-codex-gpt
codex
```

**Cursor**：在 `D:\AI\owlclaw\` 中正常使用，无需额外配置。

### 3.1 通用规则（所有 worktree 都适用）

- **启动时必须读取 `.kiro/WORKTREE_ASSIGNMENTS.md`**，确认自己的任务分配和禁止触碰的路径
- **只做分配给自己的 spec/模块**，不越界；只在自己的 worktree 中编辑文件
- **正常 commit 到自己的分支**，commit 规范不变（见 `AGENTS.md`）
- **Spec 体系不变**：三层文档结构、SPEC_TASKS_SCAN、Spec 循环流程全部照旧
- **规则文件不变**：`.cursor/rules/*.mdc` 的所有规范继续生效
- **合并由人工决定**：完成一批工作后，由人工（或 Cursor 辅助）决定何时合并

### 3.2 主 Worktree（`D:\AI\owlclaw\`，main 分支）— 统筹 + 编码

- **使用者**：Cursor、人工
- **角色**：统筹指挥 + 复杂编码
- **统筹职责**：
  - 任务分配：更新 `.kiro/WORKTREE_ASSIGNMENTS.md`，决定哪个 spec 分给哪个 worktree
  - 合并操作：将 `review-work` 合并到 `main`，通知各 worktree 同步
  - 冲突解决：处理合并时的文件冲突
  - 设计讨论：与人工交互讨论架构决策、spec 设计
  - 分配调整：根据进度和负载动态调整 worktree 任务
- **编码职责**：
  - 复杂重构：跨模块的架构级变更（多个 spec 交叉的改动）
  - 关键路径实现：需要人工参与决策的核心功能
  - 紧急修复：不适合等 Codex 循环的 hotfix
- **分支策略**：直接在 `main` 上工作，或按需创建 feature 分支

### 3.3 审校 Worktree（`D:\AI\owlclaw-review\`，review-work 分支）

- **使用者**：Codex-CLI（审校角色）
- **适合的工作**：
  - Spec 规范化（spec → architecture → code 一致性审计）
  - Code review（检查其他 worktree 合并后的代码质量）
  - 文档修正（修复过时路径、术语不一致、格式问题）
  - SPEC_TASKS_SCAN 状态对齐
- **分支策略**：在 `review-work` 分支上工作，完成后等待合并到 `main`
- **注意**：审校 worktree 以读为主、改动较轻，优先合并以减少冲突

### 3.4 编码 Worktree 1（`D:\AI\owlclaw-codex\`，codex-work 分支）

- **使用者**：Codex-CLI（编码角色）
- **适合的工作**：功能实现、测试编写、Spec 循环自主推进
- **分支策略**：在 `codex-work` 分支上工作，完成后等待合并到 `main`

### 3.5 编码 Worktree 2（`D:\AI\owlclaw-codex-gpt\`，codex-gpt-work 分支）

- **使用者**：Codex-CLI（编码角色）
- **适合的工作**：功能实现、测试编写、Spec 循环自主推进
- **分支策略**：在 `codex-gpt-work` 分支上工作，完成后等待合并到 `main`
- **与编码 1 的分工**：两个编码 worktree 应分配到**不同的 spec/模块**，避免改动同一组文件导致合并冲突

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

### 4.2 合并流程（审校 worktree 把关）

**编码分支的变更不直接合并到 main，必须经过审校 worktree 的 Review Loop 审核。**

审校 worktree（owlclaw-review）承担技术经理角色，执行完整的 Review Loop（定义见 `.kiro/WORKTREE_ASSIGNMENTS.md`）：

```
编码 worktree commit
  ↓
审校 worktree Review Loop（Scan → Review → Verdict）
  ↓ APPROVE
审校 worktree 合并编码分支到 review-work 并运行测试
  ↓ 测试通过
人工将 review-work 合并到 main
  ↓
各 worktree git merge main 同步
```

**人工在主 worktree 中执行最终合并**：

```bash
cd D:\AI\owlclaw

# 合并审校 worktree（已包含审核通过的编码变更）
git log main..review-work --oneline
git merge review-work

# 通知各 worktree 同步
```

**注意**：审校 worktree 负责将编码分支合并到 review-work 并验证测试通过，人工只需将 review-work 合并到 main 这一步。

### 4.3 保持同步

所有 Codex worktree 需要定期同步 main 的最新变更，避免分支偏离过远：

```bash
# 在各 worktree 中分别执行
cd D:\AI\owlclaw-review    && git merge main
cd D:\AI\owlclaw-codex     && git merge main
cd D:\AI\owlclaw-codex-gpt && git merge main
```

**建议频率**：每次开始新一轮工作前同步一次。人工合并完一批变更后，通知各 worktree 同步。

### 4.4 冲突处理

- **预防**：各 worktree 工作在不同的 spec/模块上（通过 `.kiro/WORKTREE_ASSIGNMENTS.md` 分配）；两个编码 worktree 必须分配到不同 spec
- **检测**：审校 worktree 在 Review Loop 的 Merge 步骤中检测冲突
- **解决**：审校 worktree 负责解决编码分支之间的冲突；无法解决的由人工裁决
- **原则**：审校 worktree 是合并网关，所有编码变更经审校后统一进入 main

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
> 每个编码 Agent 在自己的 worktree 中独立工作，无需检查文件是否被其他 Agent 修改。Spec 循环正常推进，不跳过任何 task。编码完成后 commit 到自己的分支，由审校 worktree 的 Review Loop 审核后合并到 main。

### 5.4 审校 worktree 的独立循环

审校 worktree 运行独立的 **Review Loop**（非 Spec 循环），职责包括：

1. **审核编码分支**：检查 spec 一致性、代码质量、测试覆盖、架构合规
2. **合并把关**：只有审校 APPROVE 的分支才能合并到 review-work
3. **测试验证**：合并后运行完整测试套件，确保不引入回归
4. **状态同步**：更新 SPEC_TASKS_SCAN 的 Checkpoint

Review Loop 的完整定义见 `.kiro/WORKTREE_ASSIGNMENTS.md` 中审校部分。

### 5.3 SPEC_TASKS_SCAN 的使用

每个 worktree 各自有一份 `SPEC_TASKS_SCAN.md` 的副本。更新规则：

- 各自在自己的副本中更新 Checkpoint
- 合并时以最新进度为准（人工判断）
- 主 worktree 的 SPEC_TASKS_SCAN 为权威版本，各 worktree 合并后以 main 为准
- **审校 worktree** 可以修正 SPEC_TASKS_SCAN 的状态对齐，但不改动 task 勾选
- **编码 worktree** 完成 task 后在自己的副本中打勾，合并后反映到 main

---

## 六、并发控制

### 6.1 并发上限

建议同时运行的 Agent 数量不超过 **4-5 个**（含 Cursor）。超过此数量后：
- 人工审核和合并成为瓶颈，变更堆积
- 跨 spec 依赖的协调复杂度急剧上升
- 认知负荷过高，容易遗漏问题

### 6.2 降级策略

出现以下情况时，应减少并行 Agent 数量：

- **合并冲突频繁**：两个编码 worktree 反复在同一文件上冲突 → 合并为一个编码 worktree，或重新划分 spec 边界
- **审校积压**：审校 worktree 来不及审核编码分支的变更 → 暂停一个编码 worktree，让审校追上
- **跨 spec 依赖密集**：多个 spec 之间依赖频繁变动 → 将相关 spec 合并分配给同一个编码 worktree 串行处理
- **测试频繁失败**：合并后测试通过率低 → 减速，确保每个编码 worktree 在提交前本地测试通过

### 6.3 扩容策略

当前批次完成、审校无积压、合并顺畅时，可以增加 worktree：

```bash
# 1. 创建 worktree
git worktree add -b <branch-name> D:\AI\owlclaw-<name> main

# 2. 安装虚拟环境
cd D:\AI\owlclaw-<name>
poetry install

# 3. 在主 worktree 中更新分配文件
# 编辑 .kiro/WORKTREE_ASSIGNMENTS.md，添加新 worktree 的分配
# git add && git commit

# 4. 同步所有 worktree
# 各 worktree 执行 git merge main
```

---

## 七、常用命令速查

```bash
# 查看所有 worktree
git worktree list

# 同步所有 worktree（在各自目录中执行）
cd D:\AI\owlclaw-review    && git merge main
cd D:\AI\owlclaw-codex     && git merge main
cd D:\AI\owlclaw-codex-gpt && git merge main

# 在主 worktree 中合并各分支（推荐顺序）
cd D:\AI\owlclaw
git merge review-work       # 审校优先
git merge codex-work        # 编码 1
git merge codex-gpt-work    # 编码 2

# 查看某分支相对于 main 的变更
git log main..codex-work --oneline
git diff main..codex-work --stat

# 删除 worktree（如果不再需要）
git worktree remove D:\AI\owlclaw-review

# 重新创建 worktree
git worktree add -b review-work D:\AI\owlclaw-review main
```

---

## 八、故障排除

### Q: Git 报错 "fatal: '<branch>' is already checked out at '<path>'"
**A**: 不能在两个 worktree 中同时 checkout 同一个分支。每个 worktree 必须在不同分支上。

### Q: Codex worktree 落后 main 太多，合并冲突很多
**A**: 定期在 codex worktree 中运行 `git merge main` 保持同步。建议每轮 Spec 循环开始前同步。

### Q: 需要增加更多 AI Agent
**A**: 创建新 worktree：`git worktree add -b <branch-name> D:\AI\owlclaw-<name> main`，然后在本文档中添加对应条目。

### Q: 两个编码 worktree 改了同一个文件怎么办
**A**: 合并时会产生冲突，由人工在主 worktree 中解决。预防方法：分配任务时确保两个编码 worktree 工作在不同的 spec/模块上。

### Q: 审校 worktree 发现了编码 worktree 的 bug
**A**: 审校 worktree 在自己的分支上修复并 commit。合并时如果编码 worktree 也改了同一处，由人工裁决。

---

**维护者**: yeemio  
**下次审核**: 2026-03-01
