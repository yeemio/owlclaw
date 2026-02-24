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

### owlclaw（主 worktree — 统筹 + 编码）

| 字段 | 值 |
|------|---|
| 目录 | `D:\AI\owlclaw\` |
| 分支 | `main` |
| 角色 | **统筹指挥 + 复杂编码**（Cursor + 人工） |

**统筹职责**：
- 更新本文件（`WORKTREE_ASSIGNMENTS.md`），分配和调整各 worktree 的任务
- 将 `review-work` 合并到 `main`（`git merge review-work`）
- 解决合并冲突
- 与人工讨论架构决策和 spec 设计
- 监控各 worktree 进度，动态调整负载

**编码职责**：
- 跨模块架构级重构（涉及多个 spec 交叉的改动）
- 需要人工参与决策的关键路径实现
- 紧急 hotfix

**当前编码任务**：按需，无固定 spec 分配。

---

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

**Review 检查清单**（每次审核编码分支时逐项检查）：

代码质量：
- [ ] 类型注解完整（函数签名、返回值、关键变量）
- [ ] 错误处理充分（异常捕获、边界条件、降级策略）
- [ ] 命名规范（snake_case 函数/模块、PascalCase 类、UPPER_SNAKE_CASE 常量）
- [ ] 绝对导入（`from owlclaw.xxx import ...`，无相对导入）
- [ ] 无 TODO/FIXME/HACK 占位符
- [ ] 无硬编码业务规则（AI 决策优先原则）
- [ ] 无假数据/硬编码备用数据
- [ ] 日志使用 structlog，关键操作有日志

Spec 一致性：
- [ ] 实现与 design.md 的架构设计一致（组件结构、数据流、接口定义）
- [ ] tasks.md 中的勾选与实际代码实现匹配
- [ ] 新增/修改的接口与 requirements.md 的功能需求对应

测试覆盖：
- [ ] 新代码有对应的单元测试
- [ ] 测试文件命名正确（`test_*.py`）
- [ ] `poetry run pytest` 在 review worktree 中通过
- [ ] 关键路径覆盖率 >= 75%

架构合规：
- [ ] 包边界正确（不跨越 `owlclaw_architecture.mdc` 定义的模块边界）
- [ ] 集成组件隔离（Hatchet 调用在 `integrations/hatchet.py`，litellm 在 `integrations/llm/`）
- [ ] 数据库规范（tenant_id、UUID 主键、TIMESTAMPTZ、Alembic 迁移）
- [ ] 无跨 database 访问（owlclaw / hatchet 各自独立 database）

跨 Spec 影响：
- [ ] 检查变更是否影响其他 spec 的接口或数据模型
- [ ] 若有影响，更新本文件「跨 Spec 依赖提示」表

**常规审校任务**（无编码分支变更时执行）：

- [ ] Spec 规范化审计：检查进行中 spec 的 requirements/design/tasks 与架构文档、代码实现的一致性
- [ ] SPEC_TASKS_SCAN 状态校准：核实各 spec 的 (checked/total) 是否与 tasks.md 实际勾选一致
- [ ] 代码质量全局扫描：`poetry run ruff check .` + `poetry run mypy owlclaw/`
- [ ] 架构漂移检测：代码实现是否偏离 docs/ARCHITECTURE_ANALYSIS.md

**权限**：全仓库读 + 轻量修正（文档、注释、类型注解、测试补全）。不做功能实现。可以在 review-work 分支上直接修复审校发现的轻量问题。

**审校输出格式**（每次 Review 后 commit message 中记录）：

```
review(<spec-name>): <APPROVE|FIX_NEEDED|REJECT> — <一句话结论>

检查项：代码质量 ✅ | Spec 一致性 ✅ | 测试覆盖 ✅ | 架构合规 ✅
问题：<无 / 具体问题列表>
```

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
| triggers-webhook | 18/18 ✅ | `owlclaw/triggers/webhook.py`, `tests/unit/triggers/test_webhook*.py` |
| triggers-queue | 89/89 ✅ | `owlclaw/triggers/queue.py`, `tests/unit/triggers/test_queue*.py` |
| triggers-db-change | 11/11 ✅ | `owlclaw/triggers/db_change.py`, `tests/unit/triggers/test_db_change*.py` |
| triggers-api | 11/11 ✅ | `owlclaw/triggers/api.py`, `tests/unit/triggers/test_api*.py` |
| triggers-signal | 15/15 ✅ | `owlclaw/triggers/signal.py`, `tests/unit/triggers/test_signal*.py` |
| cli-scan | 80/80 ✅ | `owlclaw/cli/scan/`, `tests/unit/cli_scan/` |
| declarative-binding | 8/26 🟡 | `owlclaw/capabilities/bindings/`, `tests/unit/capabilities/` |

**前置条件**：triggers 族全部 ✅ + cli-scan ✅ 已全部完成。

**当前任务**：declarative-binding（8/26 进行中）— 声明式工具绑定，与 cli-migrate 联动。

**下一任务（当前完成后）**：declarative-binding 收口后协助 ci-setup / release。

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
| e2e-validation | 85/85 ✅ | `tests/integration/test_e2e*.py` |
| mcp-server | 12/12 ✅ | `owlclaw_mcp/**` |
| owlhub | 38/42 🟡 | `owlclaw/owlhub/**`, `tests/unit/test_owlhub*.py` |
| examples | 0/12 🟡 | `examples/**`, `tests/unit/test_examples*.py` |
| cli-migrate | 0/24 🟡 | `owlclaw/cli/migrate.py`, `tests/unit/test_cli_migrate*.py` |
| ci-setup | 0/12 🟡 | `.github/workflows/**` |
| release | 0/32 🟡 | `pyproject.toml`, `CHANGELOG.md`, `.github/workflows/release*.yml` |

**前置条件**：skill-templates ✅ + e2e-validation ✅ + mcp-server ✅ 已完成。

**当前任务**：owlhub(38/42) → examples → cli-migrate → ci-setup → release 依序推进。

**下一任务（当前完成后）**：全部收口即完成 Phase 2/3，项目进入发布阶段。

**禁止触碰**（分配给编码 1 的路径）：

- `owlclaw/db/**`
- `owlclaw/cli/db*.py`
- `migrations/`
- `owlclaw/agent/runtime/**`

---

## 跨 Spec 依赖提示

> 由审校 worktree 在 Review Loop 中检测并更新。编码 worktree 开始新一轮工作前应检查本节。

| 源 Spec（变更方） | 影响 Spec（被影响方） | 影响内容 | 状态 |
|-------------------|---------------------|---------|------|
| database-core | configuration | `owlclaw.db.engine` 的连接参数可能影响配置系统的 DB 配置项定义 | 待关注 |
| database-core | governance | Ledger 持久化依赖 `owlclaw.db` 的 Base/session，database-core 接口变更需同步 | 阻塞中（governance 未分配） |
| integrations-llm | agent-runtime | runtime 的 function calling 循环依赖 `litellm.acompletion`，接口变更需同步 | 待关注 |
| security | governance | 数据脱敏可能需要与 visibility 过滤协调 | 待关注 |

**规则**：
- 审校 worktree 在每轮 Review Loop 中检查编码分支的变更是否影响其他 spec，有则更新本表
- 编码 worktree 若发现自己的改动影响了其他 spec，在 commit message 中标注 `cross-dep: <affected-spec>`
- 被影响的编码 worktree 在下次 Sync 时读取本表，评估是否需要适配

---

## 分配历史

| 日期 | 变更 | 原因 |
|------|------|------|
| 2026-02-23 | 初始分配 | 建立 4 worktree 并行架构 |
| 2026-02-23 | codex-work：database-core/cli-db → agent-runtime | database-core/cli-db 已完成并通过审校合并到 main |
| 2026-02-23 | codex-gpt-work：security/configuration → governance | security(44/44) + configuration(12/12) 已完成，governance 进度最高(130/173)且 security 完成可解锁协调需求 |
| 2026-02-23 | codex-work：agent-runtime → integrations-hatchet | agent-runtime 已完成(105/105)，hatchet_bridge 已就绪，integrations-hatchet 收尾(138/147) |
| 2026-02-23 | codex-gpt-work：governance → capabilities-skills + agent-tools | governance 已完成(173/173)，capabilities-skills 只差1 task，agent-tools 接续 |
| 2026-02-23 | codex-gpt-work：capabilities-skills+agent-tools → skill-templates | capabilities-skills(108/108) + agent-tools(139/139) 已完成 |
| 2026-02-23 | codex-work：integrations-hatchet 追加 triggers-cron | triggers-cron 116/117 接近完成，hatchet 同步收尾 |
| 2026-02-23 | codex-work：追加 integrations-langchain | triggers-cron(117/117) 已完成，等待审校；提前分配 Phase 2 任务 |
| 2026-02-23 | codex-work：hatchet+langchain+cron 全完成 → triggers-webhook + triggers-queue | Phase 1 全部完成，进入 Phase 2 触发器族 |
| 2026-02-23 | codex-gpt-work：skill-templates+langfuse+langchain 全完成 → e2e-validation + mcp-server | Phase 1/2 integrations 完成，进入 e2e 与 mcp |
| 2026-02-23 | 全量分配：codex-work 追加 triggers-db-change/api/signal + cli-scan | 一次分完所有剩余 spec，减少统筹轮次 |
| 2026-02-23 | 全量分配：codex-gpt-work 追加 owlhub + examples + cli-migrate + ci-setup + release | 同上 |

---

## 下一轮待分配（人工决定后填入上方）

以下 spec 尚未分配到任何编码 worktree，等当前批次完成后按优先级分配：

**Phase 1 + Phase 2 integrations 全部完成 ✅**

**全部 spec 已分配完毕 ✅**

剩余 13 个 spec 已全部分配到两个编码 worktree，无待分配项。
