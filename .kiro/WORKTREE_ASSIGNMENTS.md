# Worktree 任务分配

> **角色**: 多 Worktree 并行开发的任务分配唯一真源  
> **更新者**: 人工（或 Cursor 辅助）  
> **最后更新**: 2026-03-03（Phase 12 深度审计修复分配）

---

## 规则

1. **AI Agent 启动时必须读取本文件**，确认自己所在 worktree 的当前任务分配
2. **只做分配给自己的 spec/模块**，不越界
3. **任务分配由人工更新**，AI Agent 不得自行修改本文件
4. **两个编码 worktree 的 spec 不得重叠**，避免合并冲突
5. 分配变更后，人工通知各 worktree 同步（`git merge main`）
6. **零残留规则（必须遵守）**：每轮工作结束时，**必须 commit 所有变更**，工作目录必须干净（`git status` 无 modified/untracked）。不允许留未提交修改。原因：review-work 会独立审校并修正同样的文件，如果编码 worktree 留有未提交修改，下次 `git merge main` 时会产生冲突，浪费统筹时间。违反此规则 = 给其他 worktree 制造阻塞。
7. **工作状态标记（并行协调）**：每个编码 worktree 在下方分配表中维护 `工作状态` 字段，取值：
   - `IDLE`：空闲，无活跃 Codex 会话。统筹可自由 merge/分配。
   - `WORKING`：Codex 正在执行，工作目录可能有未提交改动。**统筹跳过该 worktree 的 `git merge main`**，避免冲突打断编码。统筹仅读取分支 log 评估进度。
   - `DONE`：本轮工作已完成并 commit，等待统筹 merge + 审校。统筹正常 merge。
   - 编码 worktree 在 Codex 会话**启动时**将状态改为 `WORKING`，**结束时**改为 `DONE`（已 commit）或 `IDLE`（无产出）。
   - **统筹判断规则**：若状态为 `WORKING` 但 `git status` 干净且分支有新 commit → 视为 `DONE`，可 merge。若状态为 `IDLE` 但 `git status` 有残留 → 真违规，统筹标记并要求清理。
8. **契约先行规则（并行开发强制）**：当多个编码 worktree 并行开发同一系统的不同层（如前端+后端、API+消费方）时，**必须先由一方输出共享契约文件并 commit 到 main**，另一方从契约生成代码/类型定义。禁止两端各自独立实现后再对齐。
   - 契约文件形式：OpenAPI Schema（`.yaml`）/ JSON Schema / Protocol 接口定义 / 契约文档
   - 分配顺序：先分配契约生产方（通常是后端/API 定义方）→ 契约 commit 到 main → 再分配契约消费方（通常是前端/调用方）
   - 违反后果：审校发现契约不一致时，修复成本由两端共担（本次 Phase 9 P0 即为教训）

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

**当前编码任务**：Phase 12 深度审计修复统筹分配。Phase 11 F11 全量回归由 review-work 执行。Phase 8 外部阻塞项跟踪。

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

**审校状态（2026-03-04 统筹）**：review-work 已合并入 main（90+ commits）。codex-work、codex-gpt-work 已同步 main。config-propagation-fix + security-hardening 已收口。

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
| 工作状态 | `IDLE`（最新提交 ee546d5 已被 review-work APPROVE） |

**当前分配的 spec**：

| Spec | 进度 | 涉及路径 |
|------|------|---------|
| **config-propagation-fix**（Task 1-8） | 0/24 | `owlclaw/config/models.py`, `owlclaw/app.py`（create_agent_runtime + configure 防护）, `owlclaw/governance/router.py`（default_model + 返回 None）, `owlclaw/agent/runtime/config.py`, `owlclaw/config/manager.py` |
| **security-hardening**（Task 1-14） | 0/43 | `owlclaw/capabilities/knowledge.py`, `owlclaw/agent/runtime/runtime.py`（工具消毒）, `owlclaw/triggers/webhook/`（鉴权 + eval + XXE + 体积）, `owlclaw/mcp/server.py`, `owlclaw/security/`（sanitizer + audit）, `owlclaw/web/`（Console 鉴权 + CORS） |

**当前任务**：Phase 12 config-propagation-fix Task 1-8 → security-hardening Task 1-14。config-propagation-fix 优先（P0，配置链路是所有功能基础）。

**共享文件修改范围约定**（避免冲突）：

| 共享文件 | 编码 1 修改范围 | 编码 2 修改范围 |
|---------|---------------|---------------|
| `owlclaw/app.py` | `create_agent_runtime()`、`configure()` 方法 | `start()`、`stop()`、`mount_skills()` 方法 |
| `owlclaw/agent/runtime/runtime.py` | `_execute_tool()` 内参数/结果消毒 | `_decision_loop()` 并发安全、max_iterations、cache key |
| `owlclaw/governance/router.py` | `__init__` default_model 参数化 | 不修改（已由 config-propagation-fix 覆盖） |

**禁止触碰**（分配给编码 2 的独占路径）：

- `owlclaw/triggers/db_change/manager.py`（R7）
- `owlclaw/agent/memory/store_inmemory.py`（R8/R9）
- `owlclaw/integrations/hatchet.py`（R10）
- `owlclaw/integrations/langfuse.py`（R14 + G4）
- `owlclaw/triggers/queue/`（R15/R16）
- `owlclaw/triggers/api/handler.py`（R17）
- `owlclaw/db/`（G7/G8/G9）
- `owlclaw/triggers/cron.py`（G10）
- `migrations/`（G1/G2/G5/G6）
- `owlclaw/capabilities/registry.py`（R3）
- `owlclaw/web/api/ws.py`（R13）

---

### owlclaw-codex-gpt（编码 2）

| 字段 | 值 |
|------|---|
| 目录 | `D:\AI\owlclaw-codex-gpt\` |
| 分支 | `codex-gpt-work` |
| 角色 | 编码：功能实现 + 测试 |
| 工作状态 | `IDLE`（最新提交 592d6b1 已被 review-work APPROVE） |

**当前分配的 spec**：

| Spec | 进度 | 涉及路径 |
|------|------|---------|
| **runtime-robustness**（Task 1-19） | 0/55 | `owlclaw/agent/runtime/runtime.py`（R1 并发 + R2 max_iter + R11 cache + R18 context）, `owlclaw/capabilities/registry.py`（R3 超时）, `owlclaw/app.py`（R4/R5/R6 幂等）, `owlclaw/triggers/db_change/manager.py`（R7 重试）, `owlclaw/agent/memory/store_inmemory.py`（R8/R9）, `owlclaw/integrations/hatchet.py`（R10）, `owlclaw/web/api/ws.py`（R13）, `owlclaw/integrations/langfuse.py`（R14）, `owlclaw/triggers/queue/`（R15/R16）, `owlclaw/triggers/api/handler.py`（R17） |
| **governance-hardening**（Task 1-11） | 0/30 | `migrations/`（G1/G2/G5 新迁移）, `owlclaw/triggers/webhook/persistence/models.py`（G2）, `owlclaw/governance/ledger.py`（G3）, `owlclaw/integrations/langfuse.py`（G4）, `owlclaw/governance/quality_store.py`（G5）, `migrations/env.py`（G6）, `owlclaw/db/session.py`（G7）, `owlclaw/db/engine.py`（G8/G9）, `owlclaw/triggers/cron.py`（G10） |

**当前任务**：Phase 12 runtime-robustness Task 1-19 → governance-hardening Task 1-11。runtime-robustness 优先（影响稳定性）。

**共享文件修改范围约定**（与编码 1 相同表格，见上方）

**禁止触碰**（分配给编码 1 的独占路径）：

- `owlclaw/config/models.py`（CP1）
- `owlclaw/config/manager.py`（CP5）
- `owlclaw/agent/runtime/config.py`（CP7）
- `owlclaw/capabilities/knowledge.py`（S1）
- `owlclaw/triggers/webhook/http/app.py`（S4/S8）
- `owlclaw/triggers/webhook/transformer.py`（S6/S7）
- `owlclaw/triggers/webhook/persistence/models.py`（S12）
- `owlclaw/mcp/server.py`（S5）
- `owlclaw/security/`（S9/S10）
- `owlclaw/web/mount.py`（S11）
- `owlclaw/web/api/middleware.py`（S13）

---

## 跨 Spec 依赖提示

> 由审校 worktree 在 Review Loop 中检测并更新。编码 worktree 开始新一轮工作前应检查本节。

| 源 Spec（变更方） | 影响 Spec（被影响方） | 影响内容 | 状态 |
|-------------------|---------------------|---------|------|
| database-core | configuration | `owlclaw.db.engine` 的连接参数可能影响配置系统的 DB 配置项定义 | 待关注 |
| database-core | governance | Ledger 持久化依赖 `owlclaw.db` 的 Base/session，database-core 接口变更需同步 | 阻塞中（governance 未分配） |
| integrations-llm | agent-runtime | runtime 的 function calling 循环依赖 `litellm.acompletion`，接口变更需同步 | 待关注 |
| security | governance | 数据脱敏可能需要与 visibility 过滤协调 | 待关注 |
| console-backend-api | console-frontend | 前端 TypeScript 类型从后端 OpenAPI Schema 生成，API 变更需重新生成 | **活跃**（Phase 9 并行开发） |
| console-backend-api + console-frontend | console-integration | 集成依赖前后端均就绪 | ✅ 已完成（Phase 9） |
| audit-fix-critical C1 | audit-fix-high H2 | CircuitBreaker 修复后 BudgetConstraint 才能端到端验证 | **活跃**（Phase 10 顺序依赖） |
| audit-fix-high H3 | audit-fix-high H2 | embedding 门面需先就位，成本追踪才能覆盖 embedding 调用 | **活跃**（同 worktree 内顺序） |

**规则**：
- 审校 worktree 在每轮 Review Loop 中检查编码分支的变更是否影响其他 spec，有则更新本表
- 编码 worktree 若发现自己的改动影响了其他 spec，在 commit message 中标注 `cross-dep: <affected-spec>`
- 被影响的编码 worktree 在下次 Sync 时读取本表，评估是否需要适配

---

## Agent 共享信箱

> **用途**：编码 worktree 之间的异步通信通道。无需等统筹中转，直接在此留言。
> **规则**：
> - 发送方写入消息并 commit（消息随 `git merge main` 自动送达对方）
> - 接收方在每轮 Sync 后检查本节，处理后标记 `✅ 已读`
> - 统筹在每轮循环中检查是否有未处理消息，必要时协调
> - 消息处理完毕后由统筹归档（移到「已归档消息」折叠区）

### 活跃消息

| 时间 | 发送方 | 接收方 | 消息 | 状态 |
|------|--------|--------|------|------|
| 2026-03-04 | 统筹(main) | 全部 | **v4 审计完成**：GLM-5 独立审计生成 v4 报告（18 发现：3 P0 + 10 P1 + 5 Low）。P0 问题仍未修复。E2E 测试 18/18 通过。review-work 已 APPROVE codex-work/codex-gpt-work 最新提交。 | 🟢 已同步 |
| 2026-03-04 | 统筹(main) | codex-work | **状态更新**：你已完成 lite-mode-e2e F11 + security-hardening Task 12-15。P0 任务（Task 1-3）仍待执行。 | 🟡 已知 |
| 2026-03-04 | 统筹(main) | codex-gpt-work | **状态更新**：你已完成 ssl_mode fix + runtime-robustness/governance-hardening 部分任务。P0 Task 1 依赖 codex-work Task 2。 | 🟡 已知 |

### 已归档消息

<details>
<summary>点击展开历史消息</summary>

| 时间 | 发送方 | 接收方 | 消息 | 结果 |
|------|--------|--------|------|------|
| _(暂无)_ | | | | |

</details>

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
| 2026-02-26 | 新增 protocol-first-api-mcp 三层 spec（0/24），待下一轮统筹分配 | 响应 API/MCP 优先战略，先固化规范与执行路径 |
| 2026-02-26 | 按发布阶段拆分 5 个子 spec：protocol-governance / gateway-runtime-ops / contract-testing / release-supply-chain / cross-lang-golden-path | 将“总纲”转为可并行执行的交付包 |
| 2026-02-26 | 统筹重分配：codex-work 主攻 protocol-governance + contract-testing + gateway-runtime-ops + test-infra 收尾；codex-gpt-work 承担 release-supply-chain + cross-lang-golden-path | 按“单活编码 worktree”策略降低空转与冲突 |
| 2026-02-26 | 新一轮统筹：codex-gpt-work 标记为暂停待命；release-supply-chain + cross-lang-golden-path 并入 codex-work/main；test-infra 11.3 调整为外部条件项（不新增 CI 订阅） | 响应“停用新增 CI + 单活推进”决策 |
| 2026-02-26 | 重新分配：恢复 codex-gpt-work 并行执行，任务拆分为 codex-work（protocol-governance + contract-testing + test-infra联动）与 codex-gpt-work（gateway-runtime-ops + release-supply-chain + cross-lang-golden-path） | 响应“重新分配”，提升并行吞吐并保持低冲突边界 |

| 2026-02-27 | Phase 8 分配：codex-work → mionyee-governance-overlay + mionyee-hatchet-migration；codex-gpt-work → mcp-capability-export + openclaw-skill-pack + content-launch | 双模架构决策批准后，Phase 7 全部完成，启动 Phase 8 双模接入 + OpenClaw 生态 |
| 2026-02-28 | 统筹同步：merge review-work → main；回写 Phase 8 与 D14 实际完成度（D14-1/2/3 ✅，content-launch 14/16，openclaw-skill-pack 12/14） | 防止分配表与 SPEC_TASKS_SCAN 漂移 |
| 2026-02-28 | Phase 9 分配：codex-work → console-backend-api（0/11）；codex-gpt-work → console-frontend（0/10）+ console-integration（0/5）。Phase 8 外部阻塞项留 main 跟踪 | D15 Web Console 架构决策批准 + spec 三层文档创建完成，启动 Phase 9 实现 |
| 2026-03-02 | 审校修复分配：merge review-work 审校报告 → main；codex-work console-backend-api 11/11 🔧 需修复 P0（ErrorResponse 统一 + 契约文档输出）；codex-gpt-work console-frontend 10/10 🔧 需修复 P0（useApi.ts 契约映射 + WS 消息类型）。编码分支代码未合并（FIX_NEEDED） | 审校发现前后端 API 契约漂移 + WS 协议不一致 + 错误响应未统一 |
| 2026-03-02 | Phase 9 完成：merge review-work（APPROVE，9 轮审校）→ main。console-backend-api ✅(11/11)，console-frontend ✅(10/10)，console-integration ✅(5/5)。160 文件 +17,584 行。两个编码 worktree 状态改为 DONE | 审校通过，Phase 9 Web Console 全部合并到 main |
| 2026-03-02 | Phase 10 分配：总架构师审计发现 2 Critical + 5 High。codex-work → audit-fix-critical（C1+C2）+ audit-fix-high（H2+H3+H5）；codex-gpt-work → audit-fix-high（H1+H4+Task 5）。按文件边界隔离避免冲突 | 架构审计报告驱动，P0 阻断性问题必须修复 |
| 2026-03-02 | Phase 10 完成：audit-fix-critical ✅(11/11) + audit-fix-high ✅(23/23)。经 Round 13 APPROVE 审校，合并到 main。两个编码 worktree 状态改为 DONE | 架构审计修复全部完成，工程达到可交付状态 |
| 2026-03-03 | Phase 11 分配：新建 lite-mode-e2e spec（三层齐全）。codex-work → Task 1-4（核心链路：mock LLM 统一 + heartbeat 直通 + 日志 + --once 决策循环）；codex-gpt-work → Task 5-8（体验完善：pgvector 延迟导入 + Quick Start 重写 + Ledger CLI + API 降级）。按文件边界隔离 | 真实用户体验测试发现 Lite Mode 端到端体验链路断裂（P0），产品核心承诺不成立 |
| 2026-03-03 | Phase 11 完成 + Phase 12 分配：lite-mode-e2e F1-F10 全部完成（Task 1-10 ✅），仅 F11 全量回归待执行。新建 4 个 Phase 12 spec（80+ 问题）。codex-work → config-propagation-fix + security-hardening；codex-gpt-work → runtime-robustness + governance-hardening。共享文件按函数范围隔离 | 全方位深度审计（4 维度逐行审计）发现 80+ 问题，按领域拆分 4 个 spec |
| 2026-03-04 | **v4 审计统筹**：GLM-5 独立重审计完成，生成 v4 报告（18 发现）。review-work 已 APPROVE 两个编码分支最新提交。E2E 测试 18/18 通过。P0 问题（CORS/工具消毒/Schema 校验）仍未修复。更新消息状态，同步审计报告。 | 独立审计验证 + 状态同步 |

---

## 下一轮待分配（人工决定后填入上方）

以下 spec 尚未分配到任何编码 worktree，等当前批次完成后按优先级分配：

**Phase 1-11 全部已分配完毕 ✅**

**Phase 12 进行中**（2026-03-04 更新 — GLM-5 重审计后）

### 任务优先级说明

| 优先级 | 含义 | 执行要求 |
|--------|------|----------|
| **P0** | 阻塞发布 | 必须在发布前完成，安全漏洞/核心功能断裂 |
| **P1** | 发布后尽快修复 | 重要问题，但不阻塞发布 |
| **Low** | 后续迭代处理 | 改进项，可排期处理 |

### codex-work 分配

| Spec | Phase | Task | Finding | 优先级 | 状态 |
|------|-------|------|---------|--------|------|
| **security-hardening** | Phase 1 | Task 1: 工具结果消毒 | #2 | **P0** | 🟡 待开始 |
| | Phase 1 | Task 2: 工具参数 Schema 校验 | #3 | **P0** | 🟡 待开始 |
| | Phase 1 | Task 3: CORS 安全修复 | #1, #4, #15 | **P0** | 🟡 待开始 |
| | Phase 2 | Task 4: HTTP Executor SSRF | #5 | P1 | 🟡 待开始 |
| | Phase 2 | Task 5: Unicode 归一化 | #6 | P1 | 🟡 待开始 |
| | Phase 2 | Task 6: SKILL.md 注入防护 | - | P1 | 🟡 待开始 |
| | Phase 3 | Task 7-14: 其他安全任务 | - | P1 | 🟡 待开始 |
| **config-propagation-fix** | Phase 1 | Task 1: Auth 空 Token 绕过 | #7 | P1 | 🟡 待开始 |
| | Phase 2 | Task 2-8: 配置传播修复 | - | P1 | 🟡 待开始 |

**codex-work 执行顺序**：
1. security-hardening Phase 1 (P0) → 阻塞发布
2. config-propagation-fix Phase 1 (P1)
3. security-hardening Phase 2-3 (P1)

### codex-gpt-work 分配

| Spec | Phase | Task | Finding | 优先级 | 状态 |
|------|-------|------|---------|--------|------|
| **runtime-robustness** | Phase 1 | Task 1: Schema 校验依赖 | #3 | **P0** | 🟡 等待 security-hardening Task 2 |
| | Phase 1 | Task 2: _tool_call_timestamps 并发安全 | #16 | P1 | 🟡 待开始 |
| | Phase 1 | Task 3: skills_context_cache 隔离 | #17 | P1 | 🟡 待开始 |
| | Phase 2 | Task 4-19: 其他健壮性任务 | - | P1 | 🟡 待开始 |
| **governance-hardening** | Phase 1 | Task 1: API Trigger 速率限制 | #8 | P1 | 🟡 待开始 |
| | Phase 1 | Task 2: fail_policy 默认值 | #9 | P1 | 🟡 待开始 |
| | Phase 1 | Task 3: Budget 竞态条件 | #10 | P1 | 🟡 待开始 |
| | Phase 2 | Task 4-13: 其他治理任务 | - | P1 | 🟡 待开始 |

**codex-gpt-work 执行顺序**：
1. runtime-robustness Phase 1 Task 2-3（Task 1 需等待 codex-work security-hardening Task 2）
2. governance-hardening Phase 1 (P1)
3. runtime-robustness Phase 2 (P1)

### 共享文件修改边界

| 共享文件 | codex-work 范围 | codex-gpt-work 范围 |
|---------|----------------|-------------------|
| `owlclaw/agent/runtime/runtime.py` | `_execute_tool()` 消毒、schema 校验 | `_tool_call_timestamps`、`_skills_context_cache` |
| `owlclaw/web/api/middleware.py` | CORS + Auth 修复 | 不修改 |
| `owlclaw/governance/visibility.py` | 不修改 | fail_policy 默认值 |

### Low 级别发现（后续迭代）

| Finding | 问题 | 建议归属 |
|---------|------|----------|
| #11 | Langfuse secret in config | security-hardening 后续 |
| #12 | `_is_select_query` 启发式 | declarative-binding 后续 |
| #13 | Shadow mode 查询泄露 | declarative-binding 后续 |
| #14 | Heartbeat DB I/O | agent-runtime 后续 |

**下一轮待分配**：Phase 11 F11 全量回归由 review-work 审校执行。Phase 12 全部完成后评估是否需要 Phase 13。

**Phase 8 外部阻塞项**（等外部条件就绪后由 main 收口）：

| Spec | 剩余 | 阻塞原因 |
|------|------|---------|
| release-supply-chain（11/15） | Trusted Publisher 外部配置 | 需维护者操作 PyPI |
| release（28/32） | 发布凭据与发布验证 | 需 PYPI_TOKEN |
| owlhub（141/143） | Task 40.4 生产部署收尾 | 需生产凭据 |
| openclaw-skill-pack（12/14） | PR 合并 + 线上验证 | 需外部仓库审核 |
| content-launch（14/16） | 外部发布证据回填 | 需真实数据 + 发布渠道 |
