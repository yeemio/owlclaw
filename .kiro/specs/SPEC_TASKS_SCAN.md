# SPEC_TASKS_SCAN — OwlClaw 功能清单总览

> **来源**: `docs/ARCHITECTURE_ANALYSIS.md` §6.2 MVP 模块清单 + §9 下一步行动 + `docs/DATABASE_ARCHITECTURE.md` + §4.8 编排框架标准接入 + §2.7 产品愿景 + §4.10 Skills 生态
> **角色**: Spec 循环的**单一真源**（Authority），所有 spec 的 tasks.md 必须映射到此清单
> **最后更新**: 2026-02-11

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
- [ ] 配置 CI（GitHub Actions: lint + test） → spec: ci-setup

### Phase 1：Agent 核心（MVP）

- [x] `owlclaw.capabilities.skills` — Skills 挂载（Agent Skills 规范，从应用目录加载 SKILL.md） → spec: capabilities-skills
- [x] `owlclaw.capabilities.registry` — 能力注册（@handler + @state 装饰器） → spec: capabilities-skills
- [x] `docs/DATABASE_ARCHITECTURE.md` — 数据库架构设计（部署模式、数据模型、迁移策略、运维 CLI 设计、灾备） → 架构文档（已完成）
- [x] `.cursor/rules/owlclaw_database.mdc` — 数据库编码规范（tenant_id、SQLAlchemy、Alembic、pgvector） → 编码规则（已完成）
- [x] `owlclaw.cli.db` — 数据库运维 CLI（`owlclaw db init/migrate/status` P0 已实现并集成） → spec: cli-db
- [x] `owlclaw.db` — SQLAlchemy 基础设施（Base、engine、session、异常、Alembic 占位迁移） → spec: database-core
- [x] `owlclaw.agent.runtime` — Agent 运行时（SOUL.md 身份加载、记忆系统、Skills 知识注入） → spec: agent-runtime
- [x] `owlclaw.agent.runtime` — function calling 决策循环（基于 litellm） → spec: agent-runtime
- [x] `owlclaw.agent.tools` — 内建工具（schedule_once、remember、recall、query_state） → spec: agent-tools
- [x] `owlclaw.agent.heartbeat` — Heartbeat 机制（无事不调 LLM） → spec: agent-runtime
- [ ] `owlclaw.governance.visibility` — 能力可见性过滤（约束/预算/熔断/限流） → spec: governance
- [ ] `owlclaw.governance.ledger` — 执行记录 → spec: governance
- [ ] `owlclaw.governance.router` — task_type → 模型路由 → spec: governance
- [ ] `owlclaw.triggers.cron` — Cron 触发器 → spec: triggers-cron
- [x] `owlclaw.integrations.hatchet` — Hatchet 直接集成（MIT，持久执行 + cron + 调度） → spec: integrations-hatchet
- [x] `owlclaw.integrations.llm` — litellm 集成 → spec: integrations-llm
- [x] `owlclaw.cli.skill` — Skills CLI（`owlclaw skill init/validate/list`，纯本地操作） → spec: cli-skill
- [ ] SKILL.md 模板库 — 分类模板（monitoring/analysis/workflow/integration/report） → spec: skill-templates
- [ ] mionyee 3 个任务端到端验证 → spec: e2e-validation
- [ ] 决策质量对比测试：v3 Agent vs 原始 cron → spec: e2e-validation

### Phase 2：扩展 + 可观测 + 生态接入

- [ ] `owlclaw.triggers.webhook` — Webhook 触发器 → spec: triggers-webhook
- [ ] `owlclaw.triggers.queue` — 消息队列触发器 → spec: triggers-queue
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
| capabilities-skills | `.kiro/specs/capabilities-skills/` | ✅ 文档齐全 | skills + registry |
| database-core | `.kiro/specs/database-core/` | ✅ 文档齐全，实现已完成 | SQLAlchemy Base、engine、session、异常、Alembic |
| cli-db | `.kiro/specs/cli-db/` | ✅ 文档齐全，P0 实现已完成 | `owlclaw db` init/migrate/status，已挂载到主入口 |
| agent-runtime | `.kiro/specs/agent-runtime/` | ✅ 文档齐全 | runtime + heartbeat + function calling |
| agent-tools | `.kiro/specs/agent-tools/` | ✅ 文档齐全 | 内建工具 |
| governance | `.kiro/specs/governance/` | 待创建 | visibility + ledger + router |
| triggers-cron | `.kiro/specs/triggers-cron/` | 待创建 | cron 触发器 |
| integrations-hatchet | `.kiro/specs/integrations-hatchet/` | ✅ 文档齐全 | Hatchet 集成 |
| integrations-llm | `.kiro/specs/integrations-llm/` | ✅ 文档齐全 | litellm 集成 |
| e2e-validation | `.kiro/specs/e2e-validation/` | 待创建 | mionyee 端到端验证 |
| triggers-webhook | `.kiro/specs/triggers-webhook/` | 待创建 | webhook 触发器 |
| triggers-queue | `.kiro/specs/triggers-queue/` | 待创建 | 消息队列触发器 |
| integrations-langfuse | `.kiro/specs/integrations-langfuse/` | 待创建 | Langfuse tracing |
| integrations-langchain | `.kiro/specs/integrations-langchain/` | 待创建 | LangChain LLM 后端适配器 + 编排框架集成文档/示例 |
| cli-skill | `.kiro/specs/cli-skill/` | ✅ 文档齐全，MVP 已实现 | `owlclaw skill` CLI（init/validate/list，纯本地） |
| skill-templates | `.kiro/specs/skill-templates/` | 待创建 | SKILL.md 分类模板库（monitoring/analysis/workflow/integration/report） |
| owlhub | `.kiro/specs/owlhub/` | 待创建 | OwlHub Skills 注册中心（Phase 1 GitHub 索引 → Phase 2 静态站点 → Phase 3 数据库） |
| cli-scan | `.kiro/specs/cli-scan/` | 待创建 | AST 扫描器 |
| mcp-server | `.kiro/specs/mcp-server/` | 待创建 | owlclaw-mcp |
| examples | `.kiro/specs/examples/` | 待创建 | 示例（含业务 Skills 示例 + LangChain 集成示例） |
| cli-migrate | `.kiro/specs/cli-migrate/` | 待创建 | 迁移工具 |
| release | `.kiro/specs/release/` | 待创建 | PyPI + GitHub 发布 |
| ci-setup | `.kiro/specs/ci-setup/` | 待创建 | GitHub Actions CI |

---

## Checkpoint（供 Spec 循环使用）

| 字段 | 值 |
|------|---|
| 最后更新 | 2026-02-11 |
| 当前批次 | database-core + cli-db（实现与集成） |
| 批次状态 | 完成。owlclaw.db 与 owlclaw db init/migrate/status 已实现、已挂载、单元测试通过 |
| 已完成项 | database-core：Base/engine/session/exceptions、Alembic+占位迁移；cli-db：db_app 注册、init（asyncpg+env OWLCLAW_ADMIN_URL）、migrate（Alembic upgrade）、status（engine 校验）；tests/unit/test_db.py 与 test_cli_db.py 共 11 通过；SPEC_TASKS_SCAN 对应项已打勾 |
| 下一待执行 | **governance / skill-templates / triggers-cron**（按架构顺序，在 database-core + cli-db 验收通过后进行） |
| 阻塞项 | 无 |
| 健康状态 | 正常 |
| 连续无进展轮数 | 0 |

---

## 使用说明

1. **Spec 循环**启动时，AI 从本文件的 Checkpoint 读取状态
2. **打勾 = 实现 + 验收通过**；仅 spec 文档齐全不勾选。每轮循环完成后，AI 更新 Checkpoint 和对应的 `[ ]` → `[x]`
3. **顺序约束**：database-core、cli-db 必须先于 governance（Ledger）、agent 持久化 Memory 完成并验收（见上文「依赖与顺序」）
4. 功能清单须 ⊇ 各 spec 的 tasks.md 中的所有 task
5. 新增 spec 时须同步更新 Spec 索引表
6. 详细 Spec 循环流程见 `.cursor/rules/owlclaw_core.mdc` 第四节
