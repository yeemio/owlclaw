# SPEC_TASKS_SCAN — OwlClaw 功能清单总览

> **来源**: `docs/ARCHITECTURE_ANALYSIS.md` v4.7（§6.2 MVP 模块清单 + §9 下一步行动 + §4.8 编排框架标准接入 + §2.7 产品愿景 + §4.10 Skills 生态 + §8.5 安全模型 + §5.3.1 六类触发入口 + §6.4 技术栈 + §8.9 Spec 洞察反哺架构 + §4.11 Protocol-first + §4.12 Declarative Binding + cli-migrate 集成 + §4.13 双模接入架构 + §4.14 运行模式契约/闭环门禁/Heartbeat 韧性）+ `docs/DATABASE_ARCHITECTURE.md` + `docs/DUAL_MODE_ARCHITECTURE_DECISION.md`（已批准 2026-02-27）
> **角色**: Spec 循环的**单一真源**（Authority），所有 spec 的 tasks.md 必须映射到此清单
> **最后更新**: 2026-02-27

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
  说明：`owlclaw` 已存在；`owlclaw/mcp/` 已随 mcp-server spec 完成实现（12/12 ✅）。
- [x] pyproject.toml + MIT LICENSE + README
- [x] 配置 CI（GitHub Actions: lint + test） → spec: ci-setup

### Phase 1：Agent 核心（MVP）

- [x] `owlclaw.capabilities.skills` — Skills 挂载（Agent Skills 规范，从应用目录加载 SKILL.md） → spec: capabilities-skills
- [x] `owlclaw.capabilities.registry` — 能力注册（@handler + @state 装饰器） → spec: capabilities-skills
- [x] `docs/DATABASE_ARCHITECTURE.md` — 数据库架构设计（部署模式、数据模型、迁移策略、运维 CLI 设计、灾备） → 架构文档（已完成）
- [x] `.cursor/rules/owlclaw_database.mdc` — 数据库编码规范（tenant_id、SQLAlchemy、Alembic、pgvector） → 编码规则（已完成）
- [x] `owlclaw.cli.db` — 数据库运维 CLI（`owlclaw db init/migrate/status/revision/rollback/backup/restore/check` 已实现并通过测试） → spec: cli-db
- [x] `owlclaw.db` — SQLAlchemy 基础设施（Base、engine、session、异常、Alembic 占位迁移 + 属性测试） → spec: database-core
- [x] `owlclaw.agent.runtime` — Agent 运行时 MVP（SOUL.md 身份加载、IdentityLoader、AgentRunContext、trigger_event） → spec: agent-runtime
- [x] `owlclaw.agent.runtime` — function calling 决策循环（litellm.acompletion、工具路由、max_iterations） → spec: agent-runtime
- [x] `owlclaw.agent.tools` — 内建工具（query_state、log_decision、schedule_once、cancel_schedule、remember、recall 已实现） → spec: agent-tools
- [x] `owlclaw.agent.heartbeat` — Heartbeat 机制（无事不调 LLM） → spec: agent-runtime
- [x] `owlclaw.agent.memory` — 记忆系统（STM + LTM + pgvector 向量搜索 + Snapshot + 生命周期管理） → spec: **agent-memory**（独立 spec，解锁 remember/recall）
- [x] `owlclaw.governance.visibility` — 能力可见性过滤（约束/预算/熔断/限流） → spec: governance
- [x] `owlclaw.governance.ledger` — 执行记录 → spec: governance
- [x] `owlclaw.governance.router` — task_type → 模型路由 → spec: governance
- [x] `owlclaw.triggers.cron` — Cron 触发器（核心 MVP：数据模型/注册表/装饰器/Hatchet 集成/执行引擎） → spec: triggers-cron
- [x] `owlclaw.integrations.hatchet` — Hatchet 直接集成（MIT，持久执行 + cron + 调度） → spec: integrations-hatchet
- [x] `owlclaw.integrations.llm` — litellm 集成（config、routing、fallback、错误处理、mock_mode） → spec: integrations-llm
- [x] `owlclaw.cli.skill` — Skills CLI（`owlclaw skill init/validate/list`，纯本地操作） → spec: cli-skill
- [x] SKILL.md 模板库 — 分类模板（monitoring/analysis/workflow/integration/report） → spec: skill-templates
- [x] `owlclaw.security` — 安全模型（Prompt Injection 防护 / 高风险操作确认 / 数据脱敏） → spec: security
- [x] `owlclaw.config` — 统一配置系统（owlclaw.yaml + Pydantic + 环境变量覆盖 + 热更新） → spec: configuration
- [x] mionyee 3 个任务端到端验证 → spec: e2e-validation
- [x] 决策质量对比测试：v3 Agent vs 原始 cron → spec: e2e-validation

### Phase 1.5：声明式工具绑定（决策 4.12）

- [x] `owlclaw.capabilities.bindings` — Declarative Binding 系统（HTTP/Queue/SQL 执行器 + shadow 模式 + Ledger 集成） → spec: declarative-binding
- [x] `owlclaw.capabilities.skills` 扩展 — Skills Loader binding 检测与 BindingTool 自动注册 → spec: declarative-binding Task 6
- [x] `owlclaw.cli.skill` 扩展 — `owlclaw skill validate` binding schema 验证 → spec: declarative-binding Task 7
- [x] `owlclaw.cli.migrate` 扩展 — BindingGenerator（从 OpenAPI/ORM 自动生成 binding SKILL.md）→ spec: declarative-binding Task 16-19 + cli-migrate §4

### Phase 2：扩展 + 可观测 + 生态接入

- [x] `owlclaw.triggers.webhook` — Webhook 触发器 → spec: triggers-webhook
- [x] `owlclaw.triggers.queue` — 消息队列触发器 → spec: triggers-queue
- [x] `owlclaw.triggers.db_change` — 数据库变更触发器（PostgreSQL NOTIFY/LISTEN + CDC 预留） → spec: triggers-db-change
- [x] `owlclaw.triggers.api` — API 调用触发器（REST 端点 → Agent Run） → spec: triggers-api
- [x] `owlclaw.triggers.signal` — Signal 触发器（人工介入：暂停/恢复/强制触发/注入指令） → spec: triggers-signal
- [x] `owlclaw.integrations.langfuse` — Langfuse tracing → spec: integrations-langfuse
- [x] `owlclaw.integrations.langchain` — LangChain 生态标准接入（LLM 后端适配器 + 集成文档） → spec: integrations-langchain
- [x] `owlclaw.cli.skill` — Skills CLI 扩展（`owlclaw skill search/install/publish`，依赖 OwlHub） → spec: cli-skill
- [x] `owlclaw.cli.scan` — AST 扫描器（自动生成 SKILL.md 骨架） → spec: cli-scan
- [x] OwlHub Phase 1 — GitHub 仓库索引（`owlclaw/owlhub` 仓库 + index.json + PR 审核流程） → spec: owlhub
- [x] OwlHub Phase 2 — 静态站点（浏览/搜索/分类 + 向量搜索） → spec: owlhub
- [x] `owlclaw-mcp` — MCP Server（通用 Agent 协议接口，只读查询为主） → spec: mcp-server  
  说明：MVP 先落地于 `owlclaw/mcp/`（协议处理 + tools/resources + stdio 处理 + e2e 验证）；后续按 release 计划补独立 `owlclaw-mcp/` 打包形态。
- [x] 非交易场景 examples（至少 2 个） → spec: examples
- [x] LangChain 集成示例（LangChain chain + LangGraph workflow 作为 capability） → spec: examples
- [x] 业务 Skills 示例（至少 3 个行业：电商/金融/SaaS） → spec: examples

### Phase 3：开源发布 + Skills 生态

- [ ] PyPI 发布 owlclaw + owlclaw-mcp → spec: release
- [x] GitHub 开源（MIT） → spec: release
- [ ] OwlHub 仓库公开（`owlclaw/owlhub`）+ 首批 10+ 行业 Skills → spec: owlhub
- [x] mionyee 完整接入示例 → spec: examples
- [x] `owlclaw.cli.migrate` — AI 辅助迁移工具 → spec: cli-migrate
- [ ] 社区反馈收集 → spec: release
- [ ] 根据社区需求评估是否需要 Temporal 支持 → spec: release
- [ ] OwlHub Phase 3 评估 — 是否需要迁移到数据库后端（基于 Skills 数量和社区规模） → spec: owlhub

### Phase 4：开发基础设施统一（新增）

- [x] 统一本地开发环境（一条命令启动全部依赖，PG 镜像与 CI 一致） → spec: local-devenv
- [x] 测试分层清晰（unit 零外部依赖，integration 优雅 skip，CI 与本地镜像） → spec: test-infra
- [x] 仓库卫生清理（根目录整洁、.gitignore 完整、deploy/ 文档化） → spec: repo-hygiene

### Phase 5：落地收尾（架构重塑）

- [x] Lite Mode 零依赖启动（`OwlClaw.lite()` + `InMemoryLedger`） → 主 worktree 已实现
- [x] Quick Start 指南（10 分钟从安装到看见 Agent 决策） → spec: quick-start
- [x] 完整端到端示例（库存管理场景，可运行） → spec: complete-workflow
- [x] 架构演进路线章节（Multi-Agent/自我进化/可解释性/OwlHub 安全治理） → spec: architecture-roadmap

### Phase 6：差异化能力（业务落地核心）

- [x] SKILL.md 自然语言书写模式（业务人员零门槛） → spec: skill-dx
- [x] AI 辅助 Skill 生成（对话式创建 + 文档提取 + 模板） → spec: skill-ai-assist
- [x] 渐进式迁移 migration_weight（0%→100% 逐步放权） → spec: progressive-migration
- [x] Skills 质量评分与数据飞轮（执行指标 → 评分 → 推荐优化） → spec: skills-quality
- [x] OwlHub 语义搜索推荐（用户描述 → 最佳模板建议 + 行业标签） → spec: industry-skills

### Phase 7：协议优先（API + MCP）

- [x] Protocol-first 治理收口（统一版本策略 / 错误模型 / 兼容门禁 / Java Golden Path） → spec: protocol-first-api-mcp
- [x] 协议治理规范化（版本/兼容/错误域/门禁） → spec: protocol-governance
- [x] 网关运行与发布运维标准化（canary/rollback/SLO） → spec: gateway-runtime-ops
- [x] API + MCP 契约测试体系（diff + replay + blocking gate） → spec: contract-testing
- [ ] 发布供应链安全（OIDC Trusted Publishing + provenance） → spec: release-supply-chain
- [x] 跨语言接入黄金路径（Java + curl 可执行验收） → spec: cross-lang-golden-path

### Phase 8：双模接入 + OpenClaw 生态（决策已批准 2026-02-27）

> **来源**: `docs/DUAL_MODE_ARCHITECTURE_DECISION.md` §5 验收路线图 + `docs/ARCHITECTURE_ANALYSIS.md` §4.13
> **优先级**: 高（Phase 3 release 收口后立即启动）
> **前置**: Phase 1-2 核心模块已完成，Phase 3 release/owlhub 收口中

**Phase 8.1：Mionyee 增强模式验证（对应决策 Phase 1，4-8 周）**

- [ ] Mionyee 治理叠加 — OwlClaw 治理代理包裹 Mionyee LLM 调用（预算上限 + 限流 + 熔断 + 审计） → spec: mionyee-governance-overlay
- [ ] Mionyee 调度迁移 — 48 个 APScheduler 任务迁移到 Hatchet（进程重启恢复 + 分布式执行） → spec: mionyee-hatchet-migration

**Phase 8.2：MCP 能力输出 + OpenClaw 切入（对应决策 Phase 1.5 + Phase 2，5-7 周）**

- [ ] MCP 架构 Spike — 验证 OwlClaw MCP Server 在 OpenClaw 中的实际接入体验（连接模式 + 延迟 + 配置步骤 ≤ 3 步） → spec: mcp-capability-export
- [ ] MCP 能力输出 — 治理层/持久任务/业务接入作为 MCP Server 暴露（`owlclaw migrate` 生成业务 MCP Server） → spec: mcp-capability-export
- [ ] OpenClaw Skill 包 — 打包 `owlclaw-for-openclaw` 发布到 ClawHub（SKILL.md 兼容性测试 + 安装教程） → spec: openclaw-skill-pack
- [x] A2A Agent Card — 静态 JSON 实现 `/.well-known/agent.json`（成本极低，战略预留） → spec: mcp-capability-export

**Phase 8.3：内容营销 + 咨询准备（对应决策 Phase 2-3，持续）**

- [ ] 第一篇技术文章 — 解决具体痛点的教程（非产品介绍），发布到 Reddit/HN/掘金/V2EX → spec: content-launch
- [ ] Mionyee 案例材料 — 治理后成本降低 X%、调度稳定性提升的真实数据 → spec: content-launch
- [ ] 咨询方案模板 — "AI 智能化转型"标准咨询方案（调研→实施→交付→维护） → spec: content-launch

**Phase 8.4：深度集成（对应决策 Phase 3，按需）**

- [ ] Mionyee AI 权重提升 — 各维度分析注册为 OwlClaw Capabilities，Agent 通过 function calling 自主决定权重 → 需 mionyee-governance-overlay + mionyee-hatchet-migration 完成后评估
- [ ] 代理模式 MVP — 用 Mionyee 真实数据或开源 ERP（ERPNext/Odoo）做 Reference Implementation → 需 Phase 8.1-8.2 完成后评估

**Phase 8.5：闭环可证明性 + 韧性基线（决策 D14，2026-02-27 批准）**

> **来源**: `docs/ARCHITECTURE_ANALYSIS.md` §4.14 + GPT-5.3 红军审视 + 人工补强
> **优先级**: 高（与 Phase 8.1 并行，发布前必须完成）
> **前置**: 无硬前置，可立即启动

- [ ] D14-1 运行模式契约落地 — `app.start()` docstring 明确 heartbeat 外部驱动责任 + `app.run()` docstring 明确内建 heartbeat + 集成文档（quick-start/complete-workflow）补充服务化 heartbeat 配置示例 → 涉及 `owlclaw/app.py` + `docs/`
- [ ] D14-2 端到端闭环发布门禁 — CI 自动化验收用例：外部事件→Trigger→决策→Capability→回写→Ledger→可观测全链路（mock LLM + 真实 Trigger + 真实 Ledger），失败阻断发布 → 新增 `tests/integration/test_e2e_closed_loop.py` + `release-supply-chain` spec 联动
- [ ] D14-3 Heartbeat 韧性最小实现 — `HeartbeatChecker._check_database_events()` 接入 Ledger 表查询（只读，有索引）+ SLO 验收（漏检<5%，延迟<500ms，误触<1%）+ 集成测试 → 涉及 `owlclaw/agent/runtime/heartbeat.py` + `tests/`

---

## Spec 索引

| Spec 名称 | 路径 | 状态 | 覆盖模块 |
|-----------|------|------|---------|
| capabilities-skills | `.kiro/specs/capabilities-skills/` | ✅ 三层齐全，已完成（115/115） | skills + registry |
| database-core | `.kiro/specs/database-core/` | ✅ 三层齐全，已完成（30/30） | SQLAlchemy Base、engine、session、异常、Alembic |
| cli-db | `.kiro/specs/cli-db/` | ✅ 三层齐全，已完成（53/53） | `owlclaw db` init/migrate/status/revision/rollback/backup/restore/check |
| agent-runtime | `.kiro/specs/agent-runtime/` | ✅ 三层齐全，已完成（105/105） | runtime + heartbeat + function calling |
| agent-tools | `.kiro/specs/agent-tools/` | ✅ 三层齐全，已完成（139/139） | 内建工具 |
| governance | `.kiro/specs/governance/` | ✅ 三层齐全，已完成（173/173） | visibility + ledger + router |
| triggers-cron | `.kiro/specs/triggers-cron/` | ✅ 三层齐全，已完成（117/117） | cron 触发器 |
| integrations-hatchet | `.kiro/specs/integrations-hatchet/` | ✅ 三层齐全，已完成（147/147） | Hatchet 集成 |
| integrations-llm | `.kiro/specs/integrations-llm/` | ✅ 三层齐全，已完成（128/128） | litellm 集成（config、routing、fallback、errors、mock_mode） |
| **security** | `.kiro/specs/security/` | ✅ 三层齐全，已完成（44/44） | Prompt Injection 防护 + 高风险操作确认 + 数据脱敏 |
| **agent-memory** | `.kiro/specs/agent-memory/` | ✅ 三层齐全，已完成（18/18） | Agent Memory 子系统（STM/LTM/Snapshot/向量检索/生命周期） |
| **configuration** | `.kiro/specs/configuration/` | ✅ 三层齐全，已完成（12/12） | 统一配置系统（owlclaw.yaml + Pydantic + 环境变量） |
| e2e-validation | `.kiro/specs/e2e-validation/` | ✅ 三层齐全，已完成（85/85） | mionyee 端到端验证 |
| triggers-webhook | `.kiro/specs/triggers-webhook/` | ✅ 三层齐全，已完成（18/18） | webhook 触发器 |
| triggers-queue | `.kiro/specs/triggers-queue/` | ✅ 三层齐全，已完成（89/89） | 消息队列触发器 |
| **triggers-db-change** | `.kiro/specs/triggers-db-change/` | ✅ 三层齐全，已完成（11/11） | 数据库变更触发器（NOTIFY/LISTEN + CDC 预留） |
| **triggers-api** | `.kiro/specs/triggers-api/` | ✅ 三层齐全，已完成（11/11） | API 调用触发器（REST 入口到 Agent Run） |
| **triggers-signal** | `.kiro/specs/triggers-signal/` | ✅ 三层齐全，已完成（15/15） | Signal 触发器 |
| integrations-langfuse | `.kiro/specs/integrations-langfuse/` | ✅ 三层齐全，已完成（66/66） | Langfuse tracing |
| integrations-langchain | `.kiro/specs/integrations-langchain/` | ✅ 三层齐全，已完成（101/101） | LangChain LLM 后端适配器 + 编排框架集成文档/示例 |
| cli-skill | `.kiro/specs/cli-skill/` | ✅ 三层齐全，已完成（7/7） | `owlclaw skill` CLI（init/validate/list，纯本地） |
| **declarative-binding** | `.kiro/specs/declarative-binding/` | ✅ 三层齐全，已完成（26/26） | 声明式工具绑定（Task 0~19 全部完成：契约/schema + Resolver/Registry + HTTP/Queue/SQL Executor + BindingTool/Ledger + Skills 自动注册 + CLI 验证扩展 + Shadow 报告链路 + 安全/治理集成 + SKILL.md 最小模式/简化 tools + reference examples + 文档/模板联动 + BindingGenerator(OpenAPI/ORM) + cli-migrate output-mode 集成 + 三角色工作流文档/示例 + `skill init --from-binding`） |
| skill-templates | `.kiro/specs/skill-templates/` | ✅ 三层齐全，已完成（149/149） | SKILL.md 分类模板库（monitoring/analysis/workflow/integration/report） |
| owlhub | `.kiro/specs/owlhub/` | 🟡 三层齐全，收尾中（141/143） | OwlHub Skills 注册中心（Phase 1 GitHub 索引 → Phase 2 静态站点 → Phase 3 数据库；release gate 已实现，Task 40.4 外部阻塞） |
| cli-scan | `.kiro/specs/cli-scan/` | ✅ 三层齐全，已完成（80/80） | AST 扫描器（Task 1~20 已完成，包含属性测试/集成测试/最终验收） |
| mcp-server | `.kiro/specs/mcp-server/` | ✅ 三层齐全，已完成（12/12） | owlclaw-mcp |
| examples | `.kiro/specs/examples/` | ✅ 三层齐全，已完成（14/14） | 示例（非交易场景、LangChain、3 行业 Skills、mionyee-trading 完整示例、批量验证脚本、CI 接入、文档对齐全部完成） |
| cli-migrate | `.kiro/specs/cli-migrate/` | ✅ 三层齐全，已完成（24/24） | AI 辅助迁移工具（binding、dry-run、报告、冲突处理、Python 扫描与真实 handler 生成、配置校验与迁移向导全部完成） |
| release | `.kiro/specs/release/` | 🟡 三层齐全，进行中（28/32） | PyPI + GitHub 发布 |
| ci-setup | `.kiro/specs/ci-setup/` | ✅ 三层齐全，已完成（12/12） | GitHub Actions CI（lint/test/build/release + pre-commit/dependabot + CI 文档与配置测试） |
| **local-devenv** | `.kiro/specs/local-devenv/` | ✅ 三层齐全，已完成（10/10） | 统一本地开发环境（docker-compose.dev/test/minimal + Makefile + .env.example + DEVELOPMENT.md） |
| **test-infra** | `.kiro/specs/test-infra/` | ✅ 三层齐全，已完成（11/11） | 测试基础设施统一（skip 机制 + unit 纯净化 + 共享 fixtures + 覆盖率分层 + CI 镜像对齐；含 CI matrix 验收闭环） |
| **repo-hygiene** | `.kiro/specs/repo-hygiene/` | ✅ 三层齐全，已完成（37/37） | 仓库卫生清理（.gitignore + 根目录清理 + deploy/ 文档化 + scripts/ README + .editorconfig + CODEOWNERS + Makefile + docs/README.md） |
| **quick-start** | `.kiro/specs/quick-start/` | ✅ 三层齐全，已完成（13/13） | Quick Start 指南（10 分钟上手 + 最小示例） |
| **complete-workflow** | `.kiro/specs/complete-workflow/` | ✅ 三层齐全，已完成（18/18） | 完整端到端示例（库存管理场景，4 个能力 + 治理 + 触发器） |
| **architecture-roadmap** | `.kiro/specs/architecture-roadmap/` | ✅ 三层齐全，已完成（13/13） | 架构演进路线（Multi-Agent/自我进化/可解释性/OwlHub 安全/性能规模） |
| **skill-dx** | `.kiro/specs/skill-dx/` | ✅ 三层齐全，已完成（25/25） | SKILL.md 自然语言书写模式（P1 触发解析+缓存 + P2 工具语义匹配/解析集成全部完成） |
| **skill-ai-assist** | `.kiro/specs/skill-ai-assist/` | ✅ 三层齐全，已完成（28/28） | AI 辅助 Skill 生成（P1 对话式创建+模板 + P2 文档提取 `--from-doc` 全部完成） |
| **progressive-migration** | `.kiro/specs/progressive-migration/` | ✅ 三层齐全，已完成（31/31） | 渐进式迁移 migration_weight（MigrationGate + 风险评估 + 审批队列 + Ledger 增强 + CLI） |
| **skills-quality** | `.kiro/specs/skills-quality/` | ✅ 三层齐全，已完成（27/27） | Skills 质量评分（执行指标采集 + 评分模型 + 趋势告警 + CLI + Agent/OwlHub 集成） |
| **industry-skills** | `.kiro/specs/industry-skills/` | ✅ 三层齐全，已完成（12/12） | OwlHub 语义搜索推荐（embedding 匹配 + 行业标签 + 包格式规范） |
| **protocol-first-api-mcp** | `.kiro/specs/protocol-first-api-mcp/` | ✅ 三层齐全，已完成（24/24） | 协议优先专项（Gateway-first、API/MCP 契约与版本治理、跨语言 Golden Path） |
| **protocol-governance** | `.kiro/specs/protocol-governance/` | ✅ 三层齐全，已完成（27/27） | 协议治理基线（版本策略、兼容政策、错误模型、门禁策略） |
| **gateway-runtime-ops** | `.kiro/specs/gateway-runtime-ops/` | ✅ 三层齐全，已完成（18/18） | 网关发布与运维（灰度、回滚、SLO、运行手册） |
| **contract-testing** | `.kiro/specs/contract-testing/` | ✅ 三层齐全，已完成（19/19） | API/MCP 契约测试体系（diff 检测、回归、对齐矩阵） |
| **release-supply-chain** | `.kiro/specs/release-supply-chain/` | 🟡 三层齐全，进行中（11/15） | 发布供应链安全（OIDC、attestation、发布门禁） |
| **cross-lang-golden-path** | `.kiro/specs/cross-lang-golden-path/` | ✅ 三层齐全，已完成（16/16） | 跨语言落地路径（Java/curl 场景化接入与验收） |
| **mionyee-governance-overlay** | `.kiro/specs/mionyee-governance-overlay/` | 🟡 三层齐全，进行中（12/14） | Mionyee 治理叠加（预算/限流/熔断包裹 LLM 调用） |
| **mionyee-hatchet-migration** | `.kiro/specs/mionyee-hatchet-migration/` | 🟡 三层齐全，待实施（0/15） | Mionyee 调度迁移（APScheduler → Hatchet 持久执行） |
| **mcp-capability-export** | `.kiro/specs/mcp-capability-export/` | 🟡 三层齐全，进行中（15/18） | MCP 能力输出（治理/持久任务/业务接入作为 MCP Server 暴露 + A2A Agent Card） |
| **openclaw-skill-pack** | `.kiro/specs/openclaw-skill-pack/` | 🟡 三层齐全，待实施（0/14） | OpenClaw Skill 包（owlclaw-for-openclaw 发布到 ClawHub） |
| **content-launch** | `.kiro/specs/content-launch/` | 🟡 三层齐全，待实施（0/16） | 内容营销启动（第一篇技术文章 + Mionyee 案例 + 咨询方案模板） |

---

## 架构对齐审计（Spec 维度）

> 说明：本表只评估 **spec 文档是否满足架构要求**，不代表代码实现已完成。

| 架构要求（真源） | 对齐状态 | 证据与说明 |
|------------------|----------|------------|
| 核心栈 Python 优先、外层可多语言适配（ARCH §4.4/§6.4） | 🟡 部分通过 | `triggers-webhook` / `e2e-validation` 已声明并修正为 Python 栈；其余 spec 多为“未实现但方向一致” |
| Hatchet 集成隔离到 integrations 层（ARCH §4.5/§4.6） | ✅ 通过 | `integrations-hatchet` spec 明确；触发器相关 spec 使用集成层描述，无直接散落依赖 |
| 可观测性走 Langfuse/OpenTelemetry（ARCH §4.6/§6.4） | ✅ 通过 | `integrations-langfuse` 独立 spec，相关 spec 无自建 tracing 新契约 |
| 接入协议语言无关（ARCH §4.7） | 🟡 部分通过 | 多数文档已标注“契约/伪代码”，但仍有 Python 风格接口示例；协议层 JSON Schema 化仍需实现阶段固化 |
| DB 五条铁律：tenant_id/UUID/TIMESTAMPTZ/索引前缀/Alembic（DB ARCH §1.1） | 🟡 部分通过 | 关键 spec 已显式化“例外/无例外”口径（含 `triggers-api`、`integrations-hatchet`、`integrations-llm`、`integrations-langfuse` 在内的核心链路）；实现阶段仍需以迁移脚本最终验收 |
| database 级隔离（owlclaw/hatchet/langfuse）（DB ARCH §1.1） | ✅ 通过 | scan 与各集成 spec 均按独立 database 原则描述 |
| Trigger 统一层与 focus/debounce 等设计（ARCH §5.3.2） | 🟡 部分通过 | `triggers-*` 系列 spec 已覆盖触发器族；统一参数和行为一致性在实现阶段需二次验收 |
| `spec -> tasks -> 清单` 一致性（core/spec loop） | ✅ 通过 | 本次已将 Spec 索引与任务进度改为量化进度（`checked/total`），并修正功能清单勾选 |

---

## Checkpoint（供 Spec 循环使用）

| 字段 | 值 |
|------|---|
| 最后更新 | 2026-02-27 |
| 当前批次 | review-work 审校循环：Phase 8.1 governance overlay + Phase 8.2 MCP 并行推进 |
| 批次状态 | **进行中**。`mionyee-governance-overlay` 已完成 Task 0~3（12/14），`mcp-capability-export` 已完成 Task 0/2/3/4.1/4.2/5（15/18）；下一步推进 overlay Task 4 与 MCP Task 1/4.3/6。 |
| 已完成项 | 1) D1-R 至 D14-3 决策已签署，`ARCHITECTURE_ANALYSIS.md` 升级至 v4.7 并新增 §4.14；2) Phase 7 全部 spec 审校通过合并；3) `release` spec 三层文档按 28/32 实况规范化，外部阻塞口径固定；4) 新增 `owlclaw/governance/proxy.py` 并实现 `GovernanceProxy`（预算/限流/熔断/审计）+ `from_config` + passthrough；5) 新增 Mionyee 接入胶水 `examples/mionyee-trading/ai/client.py` 与 `examples/mionyee-trading/owlclaw.yaml`；6) 新增 `owlclaw ledger query` 命令与 `tests/unit/test_cli_ledger.py`；7) 完成治理 MCP 工具（budget/audit/rate-limit）、持久任务 MCP 工具（task_create/status/cancel）与 A2A Agent Card；8) 扩展 `owlclaw migrate --output-mode mcp` 并补齐 CLI/生成器单测。 |
| 下一待执行 | 1) `mionyee-governance-overlay` Task 4.1/4.2：治理判定延迟基线（p99 < 10ms）与端到端验收；2) `mcp-capability-export` Task 1：MCP 架构 Spike（HTTP/stdio 体验、延迟、demo、接入文档）；3) `mcp-capability-export` Task 4.3：生成 MCP 工具的集成测试（OpenClaw 可连接路径）；4) `mcp-capability-export` Task 6：端到端验收；5) D14-1/D14-2/D14-3 实装（运行模式契约文档、闭环 CI 验收、Heartbeat DB 事件源与 SLO 测试）；6) 并行跟踪外部阻塞：release-supply-chain Trusted Publisher 与 owlhub 40.4。 |
| 验收快照 | quick-start ✅(13/13)，complete-workflow ✅(18/18)，architecture-roadmap ✅(13/13)，skill-dx ✅(25/25)，skill-ai-assist ✅(28/28)，progressive-migration ✅(31/31)，skills-quality ✅(27/27)，industry-skills ✅(12/12)，protocol-governance ✅(27/27)，contract-testing ✅(19/19)，gateway-runtime-ops ✅(18/18)，cross-lang-golden-path ✅(16/16)，protocol-first-api-mcp ✅(24/24)，test-infra ✅(11/11)，release-supply-chain 🟡(11/15)，release 🟡(28/32，外部阻塞)，owlhub 🟡(141/143，仅 40/40.4 未完成)，Phase 8：mionyee-governance-overlay 🟡(12/14)，mionyee-hatchet-migration 🟡(0/15)，mcp-capability-export 🟡(15/18)，openclaw-skill-pack 🟡(0/14)，content-launch 🟡(0/16)，Phase 8.5：D14-1 🟡(0/1)，D14-2 🟡(0/1)，D14-3 🟡(0/1)，其余 spec 全部 ✅。 |
| 阻塞项 | 1) `release-supply-chain` Task 1.1/1.2：需维护者在 PyPI/TestPyPI 创建 Trusted Publisher；2) `owlhub` Task 40.4：生产凭据/环境所有权外部阻塞；3) Phase 8 与 Phase 8.5 代码任务无外部阻塞，可继续推进。 |
| 健康状态 | 正常 |
| 连续无进展轮数 | 0 |

---

## 使用说明

1. **Spec 循环**启动时，AI 从本文件的 Checkpoint 读取状态
2. **打勾 = 实现 + 验收通过**；仅 spec 文档齐全不勾选。每轮循环完成后，AI 更新 Checkpoint 和对应的 `[ ]` → `[x]`
3. **顺序约束**：database-core、cli-db 必须先于 governance（Ledger）、agent 持久化 Memory 完成并验收（见上文「依赖与顺序」）
4. 功能清单须 ⊇ 各 spec 的 tasks.md 中的所有 task
5. 新增 spec 时须同步更新 Spec 索引表
6. **跳过测试的验收**：若某功能在 spec 中记录了 SKIP/外部依赖测试，后续具备条件时必须回补真实环境验收并更新本清单
7. 详细 Spec 循环流程见 `.cursor/rules/owlclaw_core.mdc` 第四节


