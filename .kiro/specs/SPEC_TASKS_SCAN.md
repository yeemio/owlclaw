# SPEC_TASKS_SCAN — OwlClaw 功能清单总览

> **来源**: `docs/ARCHITECTURE_ANALYSIS.md` v4.1（§6.2 MVP 模块清单 + §9 下一步行动 + §4.8 编排框架标准接入 + §2.7 产品愿景 + §4.10 Skills 生态 + §8.5 安全模型 + §5.3.1 六类触发入口 + §6.4 技术栈 + §8.9 Spec 洞察反哺架构）+ `docs/DATABASE_ARCHITECTURE.md`
> **角色**: Spec 循环的**单一真源**（Authority），所有 spec 的 tasks.md 必须映射到此清单
> **最后更新**: 2026-02-22

---

## 依赖与顺序（架构约束）

**打勾 = spec 文档 + 实现 + 验收均通过。** 仅文档齐全不算完成。

按 `docs/DATABASE_ARCHITECTURE.md` 与 `docs/ARCHITECTURE_ANALYSIS.md`：

- **database-core（owlclaw.db）** 与 **cli-db（owlclaw db）** 必须在 **governance（Ledger 等）**、**agent 持久化 Memory** 之前完成并验收，否则后续落库与运维无法进行。
- 顺序建议：**database-core 实现 → cli-db 实现与集成 → 验收**，通过后再做 governance / triggers-cron / e2e 等。

---

## 功能清单（从架构文档 §6.2 映射）

### Phase 0：仓库初始化

- [x] 清理 OwlClaw 仓库
- [x] 建立包结构（owlclaw / owlclaw-mcp）
- [x] pyproject.toml + MIT LICENSE + README
- [x] 配置 CI（GitHub Actions: lint + test） → spec: ci-setup

### Phase 1：Agent 核心（MVP）

- [x] `owlclaw.capabilities.skills` — Skills 挂载（Agent Skills 规范，从应用目录加载 SKILL.md） → spec: capabilities-skills
- [x] `owlclaw.capabilities.registry` — 能力注册（@handler + @state 装饰器） → spec: capabilities-skills
- [x] `docs/DATABASE_ARCHITECTURE.md` — 数据库架构设计（部署模式、数据模型、迁移策略、运维 CLI 设计、灾备） → 架构文档（已完成）
- [x] `.cursor/rules/owlclaw_database.mdc` — 数据库编码规范（tenant_id、SQLAlchemy、Alembic、pgvector） → 编码规则（已完成）
- [x] `owlclaw.cli.db` — 数据库运维 CLI（`owlclaw db init/migrate/status` P0 已实现并集成） → spec: cli-db
- [x] `owlclaw.db` — SQLAlchemy 基础设施（Base、engine、session、异常、Alembic 占位迁移） → spec: database-core
- [x] `owlclaw.agent.runtime` — Agent 运行时 MVP（SOUL.md 身份加载、IdentityLoader、AgentRunContext、trigger_event） → spec: agent-runtime
- [x] `owlclaw.agent.runtime` — function calling 决策循环（litellm.acompletion、工具路由、max_iterations） → spec: agent-runtime
- [ ] `owlclaw.agent.tools` — 内建工具（query_state、log_decision、schedule_once、cancel_schedule 已完成；remember/recall 待 Memory） → spec: agent-tools
- [x] `owlclaw.agent.heartbeat` — Heartbeat 机制（无事不调 LLM） → spec: agent-runtime
- [ ] `owlclaw.agent.memory` — 记忆系统（STM + LTM + pgvector 向量搜索 + Snapshot + 生命周期管理） → spec: **agent-memory**（独立 spec，解锁 remember/recall）
- [x] `owlclaw.governance.visibility` — 能力可见性过滤（约束/预算/熔断/限流） → spec: governance
- [x] `owlclaw.governance.ledger` — 执行记录 → spec: governance
- [x] `owlclaw.governance.router` — task_type → 模型路由 → spec: governance
- [x] `owlclaw.triggers.cron` — Cron 触发器（核心 MVP：数据模型/注册表/装饰器/Hatchet 集成/执行引擎） → spec: triggers-cron
- [x] `owlclaw.integrations.hatchet` — Hatchet 直接集成（MIT，持久执行 + cron + 调度） → spec: integrations-hatchet  
  **验收备注**：集成测试 `test_hatchet_durable_task_aio_sleep_for_mock` 当前为 **SKIP**（mock_run 下无 durable event listener）。完成 integrations-hatchet Task 7.2.3/7.2.4（真实 Worker 重启/定时恢复）后，需用真实 Hatchet Worker 跑通该用例并视情况去掉 skip。
- [x] `owlclaw.integrations.llm` — litellm 集成（config、routing、fallback、错误处理、mock_mode） → spec: integrations-llm
- [x] `owlclaw.cli.skill` — Skills CLI（`owlclaw skill init/validate/list`，纯本地操作） → spec: cli-skill
- [x] SKILL.md 模板库 — 分类模板（monitoring/analysis/workflow/integration/report） → spec: skill-templates
- [ ] `owlclaw.security` — 安全模型（Prompt Injection 防护 / 高风险操作确认 / 数据脱敏） → spec: security
- [ ] `owlclaw.config` — 统一配置系统（owlclaw.yaml + Pydantic + 环境变量覆盖 + 热更新） → spec: configuration
- [ ] mionyee 3 个任务端到端验证 → spec: e2e-validation
- [ ] 决策质量对比测试：v3 Agent vs 原始 cron → spec: e2e-validation

### Phase 2：扩展 + 可观测 + 生态接入

- [ ] `owlclaw.triggers.webhook` — Webhook 触发器 → spec: triggers-webhook
- [ ] `owlclaw.triggers.queue` — 消息队列触发器 → spec: triggers-queue
- [ ] `owlclaw.triggers.db_change` — 数据库变更触发器（PostgreSQL NOTIFY/LISTEN + CDC 预留） → spec: triggers-db-change
- [ ] `owlclaw.triggers.api` — API 调用触发器（REST 端点 → Agent Run） → spec: triggers-api
- [ ] `owlclaw.triggers.signal` — Signal 触发器（人工介入：暂停/恢复/强制触发/注入指令） → spec: triggers-signal
- [ ] `owlclaw.integrations.langfuse` — Langfuse tracing → spec: integrations-langfuse
- [ ] `owlclaw.integrations.langchain` — LangChain 生态标准接入（LLM 后端适配器 + 集成文档） → spec: integrations-langchain
- [ ] `owlclaw.cli.skill` — Skills CLI 扩展（`owlclaw skill search/install/publish`，依赖 OwlHub） → spec: cli-skill
- [ ] `owlclaw.cli.scan` — AST 扫描器（自动生成 SKILL.md 骨架） → spec: cli-scan
- [ ] OwlHub Phase 1 — GitHub 仓库索引（`owlclaw/owlhub` 仓库 + index.json + PR 审核流程） → spec: owlhub
- [ ] OwlHub Phase 2 — 静态站点（浏览/搜索/分类 + 向量搜索） → spec: owlhub
- [ ] `owlclaw-mcp` — MCP Server（OpenClaw 通道，只读查询为主） → spec: mcp-server
- [ ] 非交易场景 examples（至少 2 个） → spec: examples
- [ ] LangChain 集成示例（LangChain chain + LangGraph workflow 作为 capability） → spec: examples
- [ ] 业务 Skills 示例（至少 3 个行业：电商/金融/SaaS） → spec: examples

### Phase 3：开源发布 + Skills 生态

- [ ] PyPI 发布 owlclaw + owlclaw-mcp → spec: release
- [ ] GitHub 开源（MIT） → spec: release
- [ ] OwlHub 仓库公开（`owlclaw/owlhub`）+ 首批 10+ 行业 Skills → spec: owlhub
- [ ] mionyee 完整接入示例 → spec: examples
- [ ] `owlclaw.cli.migrate` — AI 辅助迁移工具 → spec: cli-migrate
- [ ] 社区反馈收集 → spec: release
- [ ] 根据社区需求评估是否需要 Temporal 支持 → spec: release
- [ ] OwlHub Phase 3 评估 — 是否需要迁移到数据库后端（基于 Skills 数量和社区规模） → spec: owlhub

---

## Spec 索引

| Spec 名称 | 路径 | 状态 | 覆盖模块 |
|-----------|------|------|---------|
| capabilities-skills | `.kiro/specs/capabilities-skills/` | ✅ 三层齐全，实现已完成 | skills + registry |
| database-core | `.kiro/specs/database-core/` | ✅ 三层齐全，实现已完成 | SQLAlchemy Base、engine、session、异常、Alembic |
| cli-db | `.kiro/specs/cli-db/` | ✅ 三层齐全，P0 实现已完成 | `owlclaw db` init/migrate/status，已挂载到主入口 |
| agent-runtime | `.kiro/specs/agent-runtime/` | ✅ 三层齐全，MVP 实现已完成 | runtime + heartbeat + function calling |
| agent-tools | `.kiro/specs/agent-tools/` | ✅ 三层齐全，部分实现（remember/recall 依赖 Memory） | 内建工具 |
| governance | `.kiro/specs/governance/` | ✅ 三层齐全，核心实现已完成 | visibility + ledger + router |
| triggers-cron | `.kiro/specs/triggers-cron/` | ✅ 三层齐全，实现进行中（Task 1-5 已完成） | cron 触发器 |
| integrations-hatchet | `.kiro/specs/integrations-hatchet/` | ✅ 三层齐全；集成测试 1 个 SKIP（见清单验收备注） | Hatchet 集成 |
| integrations-llm | `.kiro/specs/integrations-llm/` | ✅ 三层齐全，核心实现已完成 | litellm 集成（config、routing、fallback、errors、mock_mode） |
| **security** | `.kiro/specs/security/` | ✅ **三层齐全**，未开始实现 | Prompt Injection 防护 + 高风险操作确认 + 数据脱敏 |
| **agent-memory** | `.kiro/specs/agent-memory/` | ✅ **三层齐全（新建）**，未开始实现 | Agent Memory 子系统（STM/LTM/Snapshot/向量检索/生命周期） |
| **configuration** | `.kiro/specs/configuration/` | ✅ **三层齐全** | 统一配置系统（owlclaw.yaml + Pydantic + 环境变量） |
| e2e-validation | `.kiro/specs/e2e-validation/` | ✅ 三层齐全，未开始实现 | mionyee 端到端验证 |
| triggers-webhook | `.kiro/specs/triggers-webhook/` | ✅ 三层齐全，未开始实现 | webhook 触发器 |
| triggers-queue | `.kiro/specs/triggers-queue/` | ✅ 三层齐全，未开始实现 | 消息队列触发器 |
| **triggers-db-change** | `.kiro/specs/triggers-db-change/` | ✅ **三层齐全** | 数据库变更触发器（NOTIFY/LISTEN + CDC） |
| **triggers-api** | `.kiro/specs/triggers-api/` | ✅ **三层齐全** | API 调用触发器 |
| **triggers-signal** | `.kiro/specs/triggers-signal/` | ✅ **三层齐全** | Signal 触发器（人工介入：暂停/恢复/指令注入） |
| integrations-langfuse | `.kiro/specs/integrations-langfuse/` | ✅ 三层齐全，未开始实现 | Langfuse tracing |
| integrations-langchain | `.kiro/specs/integrations-langchain/` | ✅ 三层齐全，未开始实现 | LangChain LLM 后端适配器 + 编排框架集成文档/示例 |
| cli-skill | `.kiro/specs/cli-skill/` | ✅ 三层齐全，MVP 已实现 | `owlclaw skill` CLI（init/validate/list，纯本地） |
| skill-templates | `.kiro/specs/skill-templates/` | ✅ 三层齐全，Task 1-25 已完成 | SKILL.md 分类模板库（monitoring/analysis/workflow/integration/report） |
| owlhub | `.kiro/specs/owlhub/` | ✅ 三层齐全，未开始实现 | OwlHub Skills 注册中心（Phase 1 GitHub 索引 → Phase 2 静态站点 → Phase 3 数据库） |
| cli-scan | `.kiro/specs/cli-scan/` | ✅ 三层齐全，未开始实现 | AST 扫描器 |
| mcp-server | `.kiro/specs/mcp-server/` | ✅ 三层齐全，未开始实现 | owlclaw-mcp |
| examples | `.kiro/specs/examples/` | ✅ 三层齐全，未开始实现 | 示例（含业务 Skills 示例 + LangChain 集成示例） |
| cli-migrate | `.kiro/specs/cli-migrate/` | ✅ 三层齐全，未开始实现 | AI 辅助迁移工具 |
| release | `.kiro/specs/release/` | ✅ 三层齐全，未开始实现 | PyPI + GitHub 发布 |
| ci-setup | `.kiro/specs/ci-setup/` | ✅ 三层齐全，最小实现已完成 | GitHub Actions CI（lint + test） |

---

## Checkpoint（供 Spec 循环使用）

| 字段 | 值 |
|------|---|
| 最后更新 | 2026-02-22 |
| 当前批次 | 架构反哺 + Spec 深度补全（v4.1） |
| 批次状态 | **完成**。本次批次完成以下工作：|
| | 1. **架构文档 v4.1 更新**：解决 app.trigger() vs @app.cron() API 双模式决策（§5.3.2）；更新 SKILL.md owlclaw 扩展字段增加 focus/risk_level/requires_confirmation（§4.3）；新增 §8.9 Spec 洞察反哺架构 6 项（migration_weight/Focus/mock_mode/instruct/risk_level/event_aggregation）|
| | 2. **新建 agent-memory 三层 spec**（requirements + design + tasks，18 个实现任务），解锁 remember/recall |
| | 3. **补全 4 个 spec 的 design.md + tasks.md**：configuration（12 tasks）、triggers-db-change（11 tasks）、triggers-api（10 tasks）、triggers-signal（14 tasks）|
| | 4. **增强 e2e-validation spec**：新增需求 9（历史回放）、需求 10（Shadow Mode）、需求 11（A/B 测试），对应设计和 tasks |
| 已完成项 | ARCHITECTURE_ANALYSIS.md v4.1、agent-memory 三层 spec、configuration design+tasks、triggers-db-change design+tasks、triggers-api design+tasks、triggers-signal design+tasks、e2e-validation 增强、SPEC_TASKS_SCAN 索引更新 |
| 下一待执行 | **agent-memory 实现**（Phase 1 MVP，解锁 remember/recall）→ **security 实现** → **configuration 实现** |
| 阻塞项 | remember/recall 依赖 agent-memory 实现（spec 已齐全，可立即开始） |
| 健康状态 | 正常 |
| 连续无进展轮数 | 0 |

---

## 使用说明

1. **Spec 循环**启动时，AI 从本文件的 Checkpoint 读取状态
2. **打勾 = 实现 + 验收通过**；仅 spec 文档齐全不勾选。每轮循环完成后，AI 更新 Checkpoint 和对应的 `[ ]` → `[x]`
3. **顺序约束**：database-core、cli-db 必须先于 governance（Ledger）、agent 持久化 Memory 完成并验收（见上文「依赖与顺序」）
4. 功能清单须 ⊇ 各 spec 的 tasks.md 中的所有 task
5. 新增 spec 时须同步更新 Spec 索引表
6. **跳过测试的验收**：清单中标注「验收备注」的项，若含当前 SKIP 的测试，在完成备注所指的后续工作后，须跑通该测试并更新文档（见「功能清单」中 integrations-hatchet 备注）
7. 详细 Spec 循环流程见 `.cursor/rules/owlclaw_core.mdc` 第四节
