# SPEC_TASKS_SCAN — OwlClaw 功能清单总览

> **来源**: `docs/ARCHITECTURE_ANALYSIS.md` v4.8（§6.2 MVP 模块清单 + §9 下一步行动 + §4.8 编排框架标准接入 + §2.7 产品愿景 + §4.10 Skills 生态 + §8.5 安全模型 + §5.3.1 六类触发入口 + §6.4 技术栈 + §8.9 Spec 洞察反哺架构 + §4.11 Protocol-first + §4.12 Declarative Binding + cli-migrate 集成 + §4.13 双模接入架构 + §4.14 运行模式契约/闭环门禁/Heartbeat 韧性 + §4.15 Web Console 决策）+ `docs/DATABASE_ARCHITECTURE.md` + `docs/DUAL_MODE_ARCHITECTURE_DECISION.md`（已批准 2026-02-27）
> **角色**: Spec 循环的**单一真源**（Authority），所有 spec 的 tasks.md 必须映射到此清单
> **最后更新**: 2026-03-04（Phase 12 tasks 重构后进度对齐：runtime/governance 状态回填）

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

- [x] Mionyee 治理叠加 — OwlClaw 治理代理包裹 Mionyee LLM 调用（预算上限 + 限流 + 熔断 + 审计） → spec: mionyee-governance-overlay
- [x] Mionyee 调度迁移 — 48 个 APScheduler 任务迁移到 Hatchet（进程重启恢复 + 分布式执行） → spec: mionyee-hatchet-migration

**Phase 8.2：MCP 能力输出 + OpenClaw 切入（对应决策 Phase 1.5 + Phase 2，5-7 周）**

- [x] MCP 架构 Spike — 验证 OwlClaw MCP Server 在 OpenClaw 中的实际接入体验（连接模式 + 延迟 + 配置步骤 ≤ 3 步） → spec: mcp-capability-export
- [x] MCP 能力输出 — 治理层/持久任务/业务接入作为 MCP Server 暴露（`owlclaw migrate` 生成业务 MCP Server） → spec: mcp-capability-export
- [ ] OpenClaw Skill 包 — 打包 `owlclaw-for-openclaw` 发布到 ClawHub（SKILL.md 兼容性测试 + 安装教程） → spec: openclaw-skill-pack
- [x] A2A Agent Card — 静态 JSON 实现 `/.well-known/agent.json`（成本极低，战略预留） → spec: mcp-capability-export

**Phase 8.3：内容营销 + 咨询准备（对应决策 Phase 2-3，持续）**

- [ ] 第一篇技术文章 — 解决具体痛点的教程（非产品介绍），发布到 Reddit/HN/掘金/V2EX → spec: content-launch
- [ ] Mionyee 案例材料 — 治理后成本降低 X%、调度稳定性提升的真实数据 → spec: content-launch
- [x] 咨询方案模板 — "AI 智能化转型"标准咨询方案（调研→实施→交付→维护） → spec: content-launch

**Phase 8.4：深度集成（对应决策 Phase 3，按需）**

- [ ] Mionyee AI 权重提升 — 各维度分析注册为 OwlClaw Capabilities，Agent 通过 function calling 自主决定权重 → 需 mionyee-governance-overlay + mionyee-hatchet-migration 完成后评估
- [ ] 代理模式 MVP — 用 Mionyee 真实数据或开源 ERP（ERPNext/Odoo）做 Reference Implementation → 需 Phase 8.1-8.2 完成后评估

**Phase 8.5：闭环可证明性 + 韧性基线（决策 D14，2026-02-27 批准）**

> **来源**: `docs/ARCHITECTURE_ANALYSIS.md` §4.14 + GPT-5.3 红军审视 + 人工补强
> **优先级**: 高（与 Phase 8.1 并行，发布前必须完成）
> **前置**: 无硬前置，可立即启动

- [x] D14-1 运行模式契约落地 — `app.start()` docstring 明确 heartbeat 外部驱动责任 + `app.run()` docstring 明确内建 heartbeat + 集成文档（quick-start/complete-workflow）补充服务化 heartbeat 配置示例 → 涉及 `owlclaw/app.py` + `docs/`
- [x] D14-2 端到端闭环发布门禁 — CI 自动化验收用例：外部事件→Trigger→决策→Capability→回写→Ledger→可观测全链路（mock LLM + 真实 Trigger + 真实 Ledger），失败阻断发布 → 新增 `tests/integration/test_e2e_closed_loop.py` + `release-supply-chain` spec 联动
- [x] D14-3 Heartbeat 韧性最小实现 — `HeartbeatChecker._check_database_events()` 接入 Ledger 表查询（只读，有索引）+ SLO 验收（漏检<5%，延迟<500ms，误触<1%）+ 集成测试 → 涉及 `owlclaw/agent/runtime/heartbeat.py` + `tests/`

### Phase 9：Web Console（治理控制面 + 统一入口，决策 D15 已批准 2026-02-27）

> **来源**: `docs/ARCHITECTURE_ANALYSIS.md` §4.15 + `docs/DUAL_MODE_ARCHITECTURE_DECISION.md` D15
> **优先级**: 高（产品交付第一印象，企业客户评估入口）
> **前置**: Phase 1-2 核心模块已完成（数据源就绪）

**Phase 9.1：Console 后端 REST API**

- [x] Console REST API 基础框架 — FastAPI/Starlette 路由挂载 + 认证中间件（Token MVP）+ 分页/筛选通用框架 + 错误处理 → spec: console-backend-api
- [x] Overview API — 系统健康（Runtime/DB/Hatchet/LLM/Langfuse 连通性）+ 关键指标（今日成本/执行次数/成功率/活跃 Agent）+ 告警规则 → spec: console-backend-api
- [x] Agents API — Agent 列表 + 身份配置 + 记忆统计 + 知识库挂载 + 运行历史（Ledger 聚合） → spec: console-backend-api
- [x] Governance API — 预算消耗趋势 + 限流/熔断状态 + 能力可见性矩阵 + migration_weight + Skills 质量评分 + 安全统计 → spec: console-backend-api
- [x] Capabilities API — Handlers + Skills + Bindings 列表 + JSON Schema 查看 + 调用统计 + MCP 暴露工具 + **扫描结果视图**（cli-scan 产物：可接入函数列表）+ **迁移进度视图**（cli-migrate 产物：已迁移/待迁移/binding 状态） → spec: console-backend-api
- [x] Triggers API — 6 类触发器统一状态聚合 + 执行历史 + 下次触发时间 → spec: console-backend-api
- [x] Ledger API — 执行审计时间线 + 多维筛选（Agent/Capability/时间/成本）+ 分页 + 详情 → spec: console-backend-api
- [x] Settings API — 运行时配置（只读）+ MCP Server 状态 + 已连接客户端 + DB 迁移版本 + 系统信息 + **版本与供应链**（版本号/构建时间/commit hash/provenance 验证状态）+ **OwlHub 连接状态**（已安装 Skills 来源与版本） → spec: console-backend-api
- [x] WebSocket 实时推送 — Overview 指标 + Trigger 事件 + Ledger 新记录的实时流 → spec: console-backend-api

**Phase 9.2：Console 前端 SPA**

- [x] 前端工程脚手架 — Vite + React + TypeScript + Tailwind + Shadcn/ui + 暗色主题 + 路由 + API Client 类型生成 → spec: console-frontend
- [x] Overview 页面 — 系统健康指示灯 + 指标卡片（成本/执行/成功率/Agent）+ 告警横幅 + 自动刷新 + **首次使用引导卡片**（链接 Quick Start/完整示例/SKILL.md 编写指南） → spec: console-frontend
- [x] Governance 页面 — 预算消耗趋势图 + 限流/熔断状态卡片 + 能力可见性矩阵 + migration_weight 进度条 + Skills 质量排行 → spec: console-frontend
- [x] Ledger 页面 — 执行审计时间线 + 多维筛选面板 + 详情展开（输入/输出/成本/模型/延迟） → spec: console-frontend
- [x] Agents 页面 — Agent 列表 + 身份详情面板 + 记忆浏览 + 知识库状态 + 运行历史时间线 → spec: console-frontend
- [x] Capabilities 页面 — Handlers/Skills/Bindings 分类列表 + Schema 查看器 + 调用统计图 + **扫描结果标签页**（可接入函数列表）+ **迁移进度标签页**（已迁移/待迁移/binding 状态） → spec: console-frontend
- [x] Triggers 页面 — 6 类触发器统一视图 + 执行历史表格 + 下次触发倒计时 → spec: console-frontend
- [x] Settings 页面 — 配置树形展示 + MCP 连接列表 + DB 状态 + **版本与供应链信息**（版本号/构建时间/commit/provenance）+ **OwlHub 状态**（连接/已安装 Skills 来源）+ **开发者文档链接区域**（Quick Start/SKILL.md 指南/AI 辅助生成/示例） → spec: console-frontend
- [x] Traces/Workflows 页面 — Langfuse/Hatchet 深链接或 iframe 嵌入 → spec: console-frontend

**Phase 9.3：Console 集成与部署**

- [x] `owlclaw start` 自动挂载 — 检测静态文件存在时自动挂载 Console 路由到同端口 → spec: console-integration
- [x] CLI `owlclaw console` 命令 — 打开浏览器 + 显示 URL + 支持 `--port` 参数 → spec: console-integration
- [x] 构建流程集成 — 前端 Vite build → `owlclaw/web/static/` → Python 包发布包含静态文件 → spec: console-integration
- [x] pyproject.toml 更新 — 新增 `console` extras（可选依赖） → spec: console-integration

### Phase 10：架构审计修复（2026-03-02 审计发现）

> **来源**: 总架构师全面审计（架构设计 → Spec → 代码实现三层审视）
> **优先级**: P0 Critical 必须修复 + P1 High 尽快修复

**Phase 10.1：Critical 修复（阻断性，交付前必须完成）**

- [x] C1 修复 CircuitBreaker 状态匹配 — `"failure"` → `"error"` / `"timeout"`，熔断器核心保护恢复 → spec: audit-fix-critical
- [x] C2 修复 Console API 挂载路径 — `owlclaw.web.api.app` → `owlclaw.web.app`，Console 端到端可用 → spec: audit-fix-critical

**Phase 10.2：High 修复（重要功能缺陷）**

- [x] H1 Heartbeat 事件源补全 — schedule 接入 Hatchet + database 状态修正 + 扩展点文档 → spec: audit-fix-high
- [x] H2 成本追踪实现 — LLM token usage → estimated_cost → BudgetConstraint 生效 → spec: audit-fix-high
- [x] H3 litellm embedding 隔离 — 添加 aembedding 门面 + 重构 embedder_litellm → spec: audit-fix-high
- [x] H4 Console Governance 前端映射 — CircuitBreaker name + VisibilityMatrix 分组 → spec: audit-fix-high
- [x] H5 治理 fail-policy 配置 — fail-open / fail-close 可配置 → spec: audit-fix-high

### Phase 11：Lite Mode 端到端体验修复（2026-03-03 真实用户体验测试）

> **来源**: 真实用户视角深度体验测试，发现 Lite Mode 体验链路从设计上断裂
> **优先级**: P0（产品核心承诺不成立，阻断新用户上手）

**Phase 11.1：核心链路修复（P0 阻断性）**

- [x] F1 统一 LLM 调用路径 — `acompletion()` 门面函数检查 mock_mode，Lite Mode 下不调真实 LLM → spec: lite-mode-e2e
- [x] F2 Lite Mode Heartbeat 直通 — disabled HeartbeatChecker 时跳过 check_events 直接进入决策循环 → spec: lite-mode-e2e
- [x] F3 自动配置日志 — `app.run()` 入口配置 logging.basicConfig，用户可见启动和运行日志 → spec: lite-mode-e2e
- [x] F4 `--once` 走决策循环 — `run_once()` 改为调用 `runtime.trigger_event()` 展示完整决策过程 → spec: lite-mode-e2e

**Phase 11.2：体验完善（P1 重要缺陷）**

- [x] F5 延迟导入 pgvector — 提取 `time_decay` 到公共模块，`import owlclaw` 不因可选依赖缺失崩溃 → spec: lite-mode-e2e
- [x] F6 Quick Start 示例重写 — mock_responses 配置 function_calls，展示 Agent 决策过程 → spec: lite-mode-e2e
- [x] F7 Ledger CLI 优雅降级 — 无 DB 时输出友好提示而非崩溃 → spec: lite-mode-e2e
- [x] F8 API 端点优雅降级 — 无 DB 时返回空结果 + 提示，不返回 500 → spec: lite-mode-e2e
- [x] F9 Model 配置传递 — `create_agent_runtime()` 将 `integrations.llm.model` 传递给 Runtime → spec: lite-mode-e2e
- [x] F10 Router 默认行为 — 无显式路由规则时 Router 返回 None，不覆盖用户配置的 model → spec: lite-mode-e2e

**Phase 11.3：全量回归**

- [ ] F11 全量回归与端到端验收 — 现有测试通过 + Lite Mode 端到端 + 真实 LLM 验证 → spec: lite-mode-e2e

### Phase 12：深度审计修复（2026-03-03 全方位多维度审计）

> **来源**: 全方位多维度审计（4 维度：Runtime 决策循环 + App 生命周期/集成 + 触发器/能力 + 数据库/安全）
> **优先级**: P0~P1（安全缺陷 + 健壮性 + 治理合规）
> **发现总数**: 80+ 个问题，按领域拆分为 4 个 spec

**Phase 12.1：配置传播链路修复（P0，配置不生效导致核心功能失效）**

- [ ] CP1 LLMIntegrationConfig 补 mock_mode/mock_responses 字段 → spec: config-propagation-fix
- [ ] CP2 create_agent_runtime() 传递 LLM 配置到 Runtime → spec: config-propagation-fix
- [ ] CP3 Router default_model 从 integrations.llm.model 派生 → spec: config-propagation-fix
- [ ] CP4 Router 未配置 task_type 返回 None → spec: config-propagation-fix
- [ ] CP5 ConfigManager 优先级明确（configure() > ENV > YAML > 默认值）→ spec: config-propagation-fix
- [ ] CP6 configure() 不得在 start() 之后调用 → spec: config-propagation-fix
- [ ] CP7 DEFAULT_RUNTIME_CONFIG 的 model 从 app config 派生 → spec: config-propagation-fix

**Phase 12.2：安全加固（P0/P1，安全缺陷可导致系统被控制）**

- [ ] S1 SKILL.md 内容注入系统提示前消毒 → spec: security-hardening
- [ ] S2 工具调用结果回传 LLM 前消毒 → spec: security-hardening
- [ ] S3 工具调用参数传给 handler 前消毒 → spec: security-hardening
- [ ] S4 Webhook 管理接口鉴权 → spec: security-hardening
- [ ] S5 MCP Server 认证层 → spec: security-hardening
- [ ] S6 Webhook transformer 禁用 eval → spec: security-hardening
- [ ] S7 XML 解析防 XXE → spec: security-hardening
- [ ] S8 Webhook 请求体大小限制 → spec: security-hardening
- [ ] S9 InputSanitizer Unicode 归一化 → spec: security-hardening
- [ ] S10 SecurityAuditLog 持久化 → spec: security-hardening
- [ ] S11 Console API 鉴权 → spec: security-hardening
- [ ] S12 Webhook auth_token 哈希存储 → spec: security-hardening
- [ ] S13 CORS 配置修复 → spec: security-hardening

**Phase 12.3：运行时健壮性（P1，影响稳定性和可靠性）**

- [ ] R0 工具参数 Schema 校验依赖（security-hardening Task 2）→ spec: runtime-robustness
- [x] R1 _tool_call_timestamps 并发安全 → spec: runtime-robustness
- [x] R2 max_iterations 退出时保留最终响应 → spec: runtime-robustness
- [x] R3 Handler 超时机制 → spec: runtime-robustness
- [x] R4 app.start() 幂等性 → spec: runtime-robustness
- [x] R5 app.start() 部分启动清理 → spec: runtime-robustness
- [x] R6 mount_skills() 幂等性 → spec: runtime-robustness
- [x] R7 db_change 重试限制 → spec: runtime-robustness
- [x] R8 InMemoryStore 线程安全 → spec: runtime-robustness
- [x] R9 InMemoryStore 大小限制 → spec: runtime-robustness
- [x] R10 Hatchet 连接超时 → spec: runtime-robustness
- [x] R11 skills_context_cache 跨租户隔离 → spec: runtime-robustness
- [x] R12 store_inmemory.py 解除 pgvector 硬依赖 → spec: runtime-robustness
- [x] R13 WebSocket 断连清理 → spec: runtime-robustness
- [x] R14 Langfuse atexit 去重 → spec: runtime-robustness
- [x] R15 Redis idempotency 值序列化 → spec: runtime-robustness
- [x] R16 Queue executor 连接复用 → spec: runtime-robustness
- [x] R17 API trigger 无效 JSON 返回 400 → spec: runtime-robustness
- [x] R18 Prompt context window 检查 → spec: runtime-robustness

**Phase 12.4：治理层加固（P1，治理层缺陷影响 Agent 可控性）**

- [x] G11 API Trigger 速率限制（per-tenant + per-endpoint）→ spec: governance-hardening
- [x] G12 VisibilityFilter 默认 fail_policy=close → spec: governance-hardening
- [x] G13 Budget 原子预约/退款机制（并发预算竞态）→ spec: governance-hardening
- [x] G1 Ledger 索引添加 tenant_id 前缀 → spec: governance-hardening
- [x] G2 WebhookIdempotencyKeyModel UUID 主键 → spec: governance-hardening
- [x] G3 Ledger fallback 路径可配置 → spec: governance-hardening
- [x] G4 MODEL_PRICING 扩展 → spec: governance-hardening
- [x] G5 SkillQualityStore 索引合规 → spec: governance-hardening
- [x] G6 Alembic env.py 导入 OwlHub 模型 → spec: governance-hardening
- [x] G7 Session factory 缓存 → spec: governance-hardening
- [x] G8 DB 连接失败包装为自定义异常 → spec: governance-hardening
- [x] G9 DB SSL/TLS 配置 → spec: governance-hardening
- [x] G10 Cron 任务去重 → spec: governance-hardening

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
| **mionyee-governance-overlay** | `.kiro/specs/mionyee-governance-overlay/` | ✅ 三层齐全，已完成（14/14） | Mionyee 治理叠加（预算/限流/熔断包裹 LLM 调用） |
| **mionyee-hatchet-migration** | `.kiro/specs/mionyee-hatchet-migration/` | ✅ 三层齐全，已完成（15/15） | Mionyee 调度迁移（APScheduler → Hatchet 持久执行） |
| **mcp-capability-export** | `.kiro/specs/mcp-capability-export/` | ✅ 三层齐全，已完成（18/18） | MCP 能力输出（治理/持久任务/业务接入作为 MCP Server 暴露 + A2A Agent Card） |
| **openclaw-skill-pack** | `.kiro/specs/openclaw-skill-pack/` | 🟡 三层齐全，进行中（18/22） | OpenClaw Skill 包（owlclaw-for-openclaw 发布到 ClawHub） |
| **content-launch** | `.kiro/specs/content-launch/` | 🟡 三层齐全，进行中（14/16） | 内容营销启动（第一篇技术文章 + Mionyee 案例 + 咨询方案模板） |
| **console-backend-api** | `.kiro/specs/console-backend-api/` | ✅ 三层齐全，已完成（11/11） | Console REST API（查询契约层 + 7 数据 API + 认证 + 分页 + WebSocket + 架构隔离验证）。经 9 轮审校 APPROVE |
| **console-frontend** | `.kiro/specs/console-frontend/` | ✅ 三层齐全，已完成（10/10） | Console 前端 SPA（9 页面 + React + Tailwind + Shadcn/ui + 暗色主题 + WebSocket + 测试）。经 9 轮审校 APPROVE |
| **console-integration** | `.kiro/specs/console-integration/` | ✅ 三层齐全，已完成（5/5） | Console 集成（`owlclaw start` 挂载 + CLI + 构建流程 + 打包 + 集成测试）。经 9 轮审校 APPROVE |
| **audit-fix-critical** | `.kiro/specs/audit-fix-critical/` | ✅ 三层齐全，已完成（11/11） | 架构审计 Critical 修复：C1 熔断器状态匹配 + C2 Console API 挂载路径 |
| **audit-fix-high** | `.kiro/specs/audit-fix-high/` | ✅ 三层齐全，已完成（23/23） | 架构审计 High 修复：H1-H5 全部完成（Heartbeat + 成本追踪 + Embedding 隔离 + Governance 映射 + fail-policy） |
| **lite-mode-e2e** | `.kiro/specs/lite-mode-e2e/` | 🟡 三层齐全，进行中（42/47） | Lite Mode 端到端体验修复：Task 1-10 已完成（F1-F10 ✅），仅 Task 11 全量回归待执行 |
| **config-propagation-fix** | `.kiro/specs/config-propagation-fix/` | 🟡 三层齐全，待实现（3/27） | 配置传播链路修复：LLMIntegrationConfig 补字段 + create_agent_runtime 传配置 + Router 默认行为 + ConfigManager 优先级 + configure 防护 |
| **security-hardening** | `.kiro/specs/security-hardening/` | 🟡 三层齐全，待实现（3/46） | 安全加固：SKILL.md 注入防护 + 工具结果/参数消毒 + Webhook 鉴权 + MCP 认证 + eval 替换 + XXE + 请求体限制 + Unicode 归一化 + 审计日志持久化 + Console 鉴权 + CORS |
| **runtime-robustness** | `.kiro/specs/runtime-robustness/` | 🟡 三层齐全，进行中（41/42） | 运行时健壮性：新增 Task 1（工具参数 Schema 校验依赖 security-hardening）未完成，其余 R1-R18 + 回归已完成 |
| **governance-hardening** | `.kiro/specs/governance-hardening/` | ✅ 三层齐全，已完成（38/38） | 治理层加固：P1 新增 Task 1-3（API 速率限制/Visibility 默认 fail-close/Budget 原子预约）已完成；原 G1-G10 + 回归已完成 |

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
| Phase 10 H1/H4 审计修复（Heartbeat + Console Governance 映射） | ✅ 通过 | `HeartbeatChecker` 已实现 database+schedule 双事件源并补扩展开关；`useApi.ts` 已适配 `capability_name` 与 visibility 扁平 items 分组，契约测试与前端 build 已通过 |
| `spec -> tasks -> 清单` 一致性（core/spec loop） | ✅ 通过 | 本次已将 Spec 索引与任务进度改为量化进度（`checked/total`），并修正功能清单勾选 |

---

## Checkpoint（供 Spec 循环使用）

| 字段 | 值 |
|------|---|
| 最后更新 | 2026-03-04（Phase 12 codex-gpt 新增测试稳定性修复 + 全量回归通过） |
| 当前批次 | **Phase 12（codex-gpt）**：已提交 `389f1c3`（治理 fail-open 集成用例对齐 + cli-scan 属性测试关键字过滤），并完成全量回归 `2068 passed, 35 skipped`。governance-hardening 保持 38/38，runtime-robustness 仍有依赖项 Task 1（41/42）。 |
| 批次状态 | **Phase 12 进行中**：governance-hardening 已收口；runtime Task 1 依赖 codex-work 的 security-hardening Task 2。 |
| 已完成项 | 1) `mionyee-governance-overlay` 已完成（14/14）；2) `mcp-capability-export` 已完成（18/18）；3) `mionyee-hatchet-migration` 已完成 Task 0~5（15/15）；4) `openclaw-skill-pack` 已完成基础包、结构/兼容测试、ClawHub 发布前置（PR `openclaw/clawhub#556`）与中英双语一键教程；5) `content-launch` 已完成咨询模板产物（总模板 + 3 个场景变体）与 Task 1 数据采集脚手架（采集脚本+输入校验+指南+清单+单测）；6) `content-launch` 已完成第一篇文章双语草稿与 3 步可运行示例：`first-article-draft-en.md`、`first-article-draft-zh.md`、`snippets/openclaw_one_command_demo.py`、`test_content_article_demo.py`；7) `content-launch` 已完成案例材料文档与双场景复用验证：`docs/content/mionyee-case-study.md` + `tests/unit/test_mionyee_case_study_material.py`（Task 3.1/3.3）；8) `content-launch` 验收项 5.2/5.4 已完成（示例可运行 + 咨询模板可参数化）；9) `content-launch` 已完成文章方向自动决策工具链（`scripts/content/select_article_direction.py` + `tests/unit/test_select_article_direction.py` + 指南更新），待真实数据触发 `2.1` 最终选择；10) `content-launch` 已完成发布证据自动校验工具链（`scripts/content/record_publication_results.py` + `docs/content/publication-evidence-template.json` + `tests/unit/test_publication_results.py`），待外部发布后触发 `2.6/2.7/5.1` 勾选；11) `content-launch` 已完成一键收口评估脚本（`scripts/content/assess_content_launch_readiness.py` + `tests/unit/test_content_launch_readiness.py`），可自动产出剩余外部待办；12) `D14-1` 运行模式契约已完成（`app.start()`/`app.run()` docstring + Quick Start + complete-workflow heartbeat 服务化示例 + `test_runtime_mode_contract.py`）；13) `D14-2` 闭环门禁已落地（`tests/integration/test_e2e_closed_loop.py`，并回写 `release-supply-chain/requirements.md` 的验收矩阵）；14) `D14-3` Heartbeat 韧性基线已落地（`_check_database_events()` 只读查询 + SLO 集成测试 `tests/integration/test_heartbeat_resilience.py`）；15) **Phase 10 全部完成**：audit-fix-critical ✅(11/11) + audit-fix-high ✅(23/23)，经 Round 13 APPROVE。 |
| 下一待执行 | **Phase 12（codex-gpt）**：等待 codex-work 完成 security-hardening Task 2 后，收口 runtime-robustness Task 1。 |
| 验收快照 | quick-start ✅(13/13)，complete-workflow ✅(18/18)，architecture-roadmap ✅(13/13)，skill-dx ✅(25/25)，skill-ai-assist ✅(28/28)，progressive-migration ✅(31/31)，skills-quality ✅(27/27)，industry-skills ✅(12/12)，protocol-governance ✅(27/27)，contract-testing ✅(19/19)，gateway-runtime-ops ✅(18/18)，cross-lang-golden-path ✅(16/16)，protocol-first-api-mcp ✅(24/24)，test-infra ✅(11/11)，mionyee-governance-overlay ✅(14/14)，mcp-capability-export ✅(18/18)，mionyee-hatchet-migration ✅(15/15)，openclaw-skill-pack 🟡(18/22)，content-launch 🟡(14/16)，release-supply-chain 🟡(11/15)，release 🟡(28/32，外部阻塞)，owlhub 🟡(141/143，仅 40/40.4 未完成)，Phase 8.5：D14-1 ✅(1/1)，D14-2 ✅(1/1)，D14-3 ✅(1/1)，Phase 9：console-backend-api ✅(11/11)，console-frontend ✅(10/10)，console-integration ✅(5/5)，**Phase 10**：audit-fix-critical ✅(11/11)，audit-fix-high ✅(23/23)，其余 spec 全部 ✅。 |
| 阻塞项 | 1) `release-supply-chain` Task 1.1/1.2：需维护者在 PyPI/TestPyPI 创建 Trusted Publisher；最新 preflight（2026-03-02）仍 `BLOCKED`，并提示 `main` 分支保护 API `HTTP 404`（`docs/release/reports/release-oidc-preflight-latest.md`，最近 release runs: 2026-02-27 的 `22471143360`/`22473801915`/`22475093887`/`22477795502` 均失败）。2) `owlhub` Task 40.4：生产凭据/环境所有权外部阻塞；3) `openclaw-skill-pack` Task 3.3/3.4/5.1/5.4 依赖外部仓库 PR 审核合并、线上索引刷新与真实下载量周期（PR: https://github.com/openclaw/clawhub/pull/556`，state=`OPEN`，`updatedAt=2026-02-28T01:45:00Z`）；4) `content-launch` Task 1/2/3.2/5 需 Mionyee 真实导出数据与外部发布渠道（最新 readiness：`docs/content/content-launch-readiness.json`，`all_external_gates_passed=false`）。 |
| 健康状态 | 正常（有可执行项） |
| 连续无进展轮数 | 0 |
| 分支量化进度 | codex-work: 12 commits, 46 files, +1071/-143; codex-gpt-work: 23 commits, 59 files, +1717/-346; review-work: 22 commits, 51 files, +1195/-137 |
| 审校状态 | codex-work: 待处理（安全 P0 任务）；codex-gpt-work: 已提交修复，待 review-work 复审；review-work: 审校中 |

---

## 使用说明

1. **Spec 循环**启动时，AI 从本文件的 Checkpoint 读取状态
2. **打勾 = 实现 + 验收通过**；仅 spec 文档齐全不勾选。每轮循环完成后，AI 更新 Checkpoint 和对应的 `[ ]` → `[x]`
3. **顺序约束**：database-core、cli-db 必须先于 governance（Ledger）、agent 持久化 Memory 完成并验收（见上文「依赖与顺序」）
4. 功能清单须 ⊇ 各 spec 的 tasks.md 中的所有 task
5. 新增 spec 时须同步更新 Spec 索引表
6. **跳过测试的验收**：若某功能在 spec 中记录了 SKIP/外部依赖测试，后续具备条件时必须回补真实环境验收并更新本清单
7. 详细 Spec 循环流程见 `.cursor/rules/owlclaw_core.mdc` 第四节





