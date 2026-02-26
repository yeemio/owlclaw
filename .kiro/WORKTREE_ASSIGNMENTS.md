# Worktree 任务分配

> **角色**: 多 Worktree 并行开发的任务分配唯一真源  
> **更新者**: 人工（或 Cursor 辅助）  
> **最后更新**: 2026-02-26

---

## 规则

1. **AI Agent 启动时必须读取本文件**，确认自己所在 worktree 的当前任务分配
2. **只做分配给自己的 spec/模块**，不越界
3. **任务分配由人工更新**，AI Agent 不得自行修改本文件
4. **两个编码 worktree 的 spec 不得重叠**，避免合并冲突
5. 分配变更后，人工通知各 worktree 同步（`git merge main`）
6. **零残留规则（必须遵守）**：每轮工作结束时，**必须 commit 所有变更**，工作目录必须干净（`git status` 无 modified/untracked）。不允许留未提交修改。原因：review-work 会独立审校并修正同样的文件，如果编码 worktree 留有未提交修改，下次 `git merge main` 时会产生冲突，浪费统筹时间。违反此规则 = 给其他 worktree 制造阻塞。

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

**当前编码任务**：Phase 5 落地收尾核心代码（Lite Mode 已完成）。

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
| triggers-webhook | 18/18 ✅ | — |
| triggers-queue | 89/89 ✅ | — |
| triggers-db-change | 11/11 ✅ | — |
| triggers-api | 11/11 ✅ | — |
| triggers-signal | 15/15 ✅ | — |
| cli-scan | 80/80 ✅ | — |
| declarative-binding | 26/26 ✅ | — |

**前置条件**：triggers 族全部 ✅ + cli-scan ✅ 已全部完成。

**当前任务**（按顺序执行）：
1. test-infra(9/11) 收尾：Task 4.2 + 11.1 + 11.3 + 11.4（性能门槛与 CI 验收）
2. skill-dx P2(7/7) — 工具语义匹配（`capability_matcher` + SkillParser 集成）
3. skill-ai-assist P2(6/6) — 文档提取生成（`skill_doc_extractor` + `--from-doc` CLI）

**禁止触碰**（分配给编码 2 的路径）：

- `owlclaw/security/**`
- `owlclaw/integrations/llm/**`
- `owlclaw/config/**`
- `owlclaw/owlhub/**`（industry-skills 分配给编码 2）

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
| owlhub | 141/143 🟡 | Task 40.4 外部阻塞（生产部署） |
| examples | 14/14 ✅ | `examples/**`, `tests/unit/test_examples*.py` |
| cli-migrate | 24/24 ✅ | `owlclaw/cli/migrate.py`, `tests/unit/test_cli_migrate*.py` |
| ci-setup | 12/12 ✅ | `.github/workflows/**` |
| release | 25/32 🟡 | `pyproject.toml`, `CHANGELOG.md`, `.github/workflows/release*.yml` |
| local-devenv | 10/10 ✅ | `docker-compose.*.yml`, `Makefile`, `.env.example`, `docs/DEVELOPMENT.md` |

**前置条件**：skill-templates ✅ + e2e-validation ✅ + mcp-server ✅ + local-devenv ✅ 已完成。

**当前任务**（按顺序执行）：
1. owlhub 收尾（Task 40.4 外部阻塞，等生产凭据）
2. release 剩余 7 tasks（PyPI token/tag/验证，需人工凭据）
3. 待命：如编码 1 遇阻，协助 test-infra 非冲突项（CI 文档/workflow 验收）

**禁止触碰**（分配给编码 1 的路径）：

- `owlclaw/db/**`
- `owlclaw/cli/db*.py`
- `migrations/`
- `owlclaw/agent/runtime/**`
- `owlclaw/capabilities/skill_creator.py`（skill-ai-assist 分配给编码 1）
- `owlclaw/capabilities/skill_nl_parser.py`（skill-dx 分配给编码 1）

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
| 2026-02-25 | declarative-binding ✅(26/26) 收口；owlhub 更新为 41/42（Task 40.4 外部阻塞）；codex-work 转向协助 ci-setup/release | 统筹轮次合并 review-work |
| 2026-02-25 | ci-setup ✅(12/12)；examples ✅(14/14)；cli-migrate ✅(24/24)；release 22/32；owlhub 41/42 | 统筹轮次合并 review-work（50+ commits） |
| 2026-02-25 | 新建 local-devenv/test-infra/repo-hygiene spec；分配：codex-work→repo-hygiene+test-infra，codex-gpt-work→local-devenv+capabilities-skills | 统筹轮次：开发基础设施统一规划 |
| 2026-02-25 | 负载再平衡：review-work 已完成 repo-hygiene(33/37)+local-devenv(37/56)+test-infra(32/52)部分；codex-gpt-work 无工作→重分配 local-devenv剩余+owlhub收尾；codex-work→repo-hygiene收尾+test-infra剩余 | 统筹轮次：负载均衡 |
| 2026-02-25 | 合并 review-work（6 commits：test-infra Task 3/9.1~9.3 + queue修复）→ main；repo-hygiene ✅(7/7)；test-infra 7/11；local-devenv 4/10；codex-work 任务更新为 test-infra Task 4/6/9.4/11 | 统筹轮次：review-work 合并 + 冲突解决 |
| 2026-02-25 | 合并 review-work(11)+codex-gpt-work(11)+codex-work(5) → main；capabilities-skills ✅(115/115)；local-devenv ✅(10/10)；owlhub 137/143；release 25/32；test-infra 7/11 | 统筹轮次：三分支全合并 + 所有 worktree 同步 |
| 2026-02-25 | repo-hygiene ✅(37/37)：.editorconfig + CODEOWNERS + docs/README.md；fix(test) skills_context_cache_hits；所有 worktree 同步 | 统筹轮次：repo-hygiene backlog 收口 |
| 2026-02-25 | Phase 5 落地收尾：Lite Mode 核心代码完成（主 worktree）；新建 quick-start/complete-workflow/architecture-roadmap spec；codex-gpt-work→quick-start+complete-workflow；codex-work→architecture-roadmap | 架构重塑：落地差距收尾 |
| 2026-02-25 | Phase 6 差异化能力：新建 skill-dx/skill-ai-assist/progressive-migration spec（三层齐全）；POSITIONING.md 规范化 v1.1.0 + 文档关联建立 | 补齐战略讨论中识别的缺失 spec |
| 2026-02-25 | Phase 6 补充：新建 skills-quality/industry-skills spec；skill-dx/skill-ai-assist 分期策略；industry-skills 降级为搜索推荐 | 产品策略审计 + 技术成熟度评估 |
| 2026-02-26 | 统筹：merge review-work → main；同步所有 worktree；Phase 6 分配计划 | 统筹轮次 |
| 2026-02-26 | Phase 6 全量分配：codex-work→skill-dx P1+skill-ai-assist P1+skills-quality；codex-gpt-work→progressive-migration+industry-skills。仅 P2（skill-dx P2/skill-ai-assist P2）暂不分配 | 一次分完，减少统筹轮次 |
| 2026-02-26 | 启动原“暂不分配”项：codex-work 追加 skill-dx P2 + skill-ai-assist P2；codex-gpt-work 保持 release/owlhub 阻塞跟踪 | P1 能力与入口已落地，具备可执行条件 |

---

## 下一轮待分配（人工决定后填入上方）

以下 spec 尚未分配到任何编码 worktree，等当前批次完成后按优先级分配：

**Phase 1 + Phase 2 integrations 全部完成 ✅**

**全部 spec 已分配完毕 ✅**

新增 3 个 Phase 5 spec 已分配：
- codex-work → test-infra（继续） + architecture-roadmap（新增）
- codex-gpt-work → quick-start + complete-workflow（新增） + owlhub/release 收尾

**Phase 6 全部已分配** ✅（含 P2）

| Spec | Tasks | Worktree | 执行顺序 |
|------|-------|----------|---------|
| skill-dx P2（0/7） | 工具语义匹配 | codex-work | #2 |
| skill-ai-assist P2（0/6） | 文档提取生成 | codex-work | #3 |
| test-infra 剩余（9/11） | 性能与 CI 收口 | codex-work | #1 |
| release 剩余（25/32） | 发布凭据与发布验证 | codex-gpt-work | #1（外部依赖） |
| owlhub 剩余（141/143） | Task 40.4 生产部署收尾 | codex-gpt-work | #2（外部依赖） |
