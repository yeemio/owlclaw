# OwlClaw 定位：Business System Intelligence

> **版本**: v1.1.0 (2026-02-25)
> **角色**: OwlClaw 的产品定位、差异化价值和生态关系的**唯一真源**
> **关联文档**:
> - `docs/ARCHITECTURE_ANALYSIS.md` — 架构设计（技术真源）
> - `.cursor/rules/owlclaw_core.mdc` — 工作指导总纲（流程真源）
> - `README.md` — 对外入口（引用本文档定位叙事）

---

## 一、核心问题

企业拥有大量已建成的信息化系统——ERP、CRM、HR、财务、供应链、工单系统。这些系统中沉淀了海量的业务数据和业务逻辑，但它们是**被动的**：只有人来操作，系统才会响应。

AI Agent 技术的出现带来了一个新的可能性：**让这些系统自己观察、自己判断、自己行动**。但当前的 AI Agent 框架几乎全部假设你从零开始构建——LangChain 要你写 Python 编排链，LangGraph 要你设计状态机，CrewAI 要你编排多 Agent 协作。

**没有一个框架是为"让已有系统变聪明"而设计的。**

这就是 OwlClaw 要解决的问题。

---

## 二、OwlClaw 的方法

> **让已有的信息化系统获得 AI 自主观察和决策能力，无需重写一行业务代码。**

OwlClaw 提供了一条完整的链路，从发现现有系统的能力到 AI Agent 自主决策：

```
owlclaw scan          owlclaw migrate          SKILL.md
(AST 扫描现有代码)  → (从 OpenAPI/ORM 生成)  → (业务知识 + 声明式绑定)
                                                      │
                                                      ▼
                                              Declarative Binding
                                              (HTTP/Queue/SQL 自动连接)
                                                      │
                                                      ▼
                                              Governance Layer
                                              (可见性过滤 / 预算 / 审计)
                                                      │
                                                      ▼
                                              Agent Runtime
                                              (function calling 自主决策)
```

### 关键设计选择

1. **SKILL.md 即能力描述**：业务开发者用 Markdown 描述已有接口的用途、业务规则和决策指引。Agent 通过 function calling 自主理解和使用。不需要 AI 知识，不需要 prompt engineering。

2. **声明式绑定（Declarative Binding）**：SKILL.md 中声明 HTTP/Queue/SQL 绑定信息，Agent 运行时自动完成调用。零代码连接现有系统。

3. **治理优先**：Agent 看到的工具列表是经过多层过滤的子集（约束/预算/熔断/限流/角色）。所有决策记录到 Ledger，可审计可追溯。

4. **六种触发器**：Cron / Webhook / Queue / DB Change / API / Signal——覆盖业务系统的所有事件入口。

5. **渐进式迁移**：`migration_weight` 控制 Agent 接管比例（0% → 100%），从零风险观察到完全自主。

---

## 三、三角色模型：IT 配置一次，业务人员持续受益

OwlClaw 的使用者不只是开发者，更是企业中各个岗位的业务人员。整个使用链路分为三个角色：

### 角色 1：IT 团队（一次性配置）

IT 团队的工作量 = 跑一条命令 + 配一个 YAML：

```bash
owlclaw migrate scan --openapi https://erp.company.com/api/v3/openapi.json --output-mode binding
```

自动生成一组带 Declarative Binding 的 SKILL.md + `owlclaw.yaml` 连接配置。IT 团队审核后部署。

### 角色 2：业务人员（持续使用）

采购经理写的 SKILL.md——**纯自然语言，零技术门槛**：

```markdown
---
name: 库存预警
description: 当商品库存低于安全线时提醒我
---

# 库存预警

每天早上 9 点检查一次库存。如果有商品的库存低于安全线，告诉我：
- 哪些商品库存不足
- 当前库存数量和安全库存线
- 建议补货数量（按过去 30 天日均销量 × 7 天）

周五补货数量多算 3 天。A 类商品标记为紧急。
```

没有 `owlclaw:` 字段、没有 cron 表达式、没有 JSON Schema。Agent 自己从已发现的工具中匹配能力，自己理解"每天早上 9 点"的含义。

### 角色 3：Agent（自主决策）

Agent Runtime 完成意图到执行的全链路：
- 读 SKILL.md → 理解业务意图
- 读 connections → 发现可用系统工具
- 治理层约束 → 可见性过滤 / 预算 / 限流
- function calling → 自主决策 + Ledger 审计

### 与 LangChain 方案的对比

| | LangChain 方案 | OwlClaw |
|---|---|---|
| IT 工作量 | 每个能力写 Python chain + 部署 | 跑一条命令，审核后部署 |
| 业务人员参与 | 不可能 | 写自然语言（5 分钟） |
| 新增 Agent 能力 | IT 写代码 + 部署 | 业务人员自己写 SKILL.md |
| Agent 灵活性 | 被 chain 逻辑锁死 | Agent 自主决策，治理层约束边界 |

**关键差异**：用 LangChain，每新增一个 Agent 能力都需要 IT 写代码部署。用 OwlClaw，IT 一次性配好 connections，之后业务人员自己写 SKILL.md 就能获得新的 Agent 能力。**这才是真正的"Markdown 即 AI 能力"。**

---

## 四、生态位关系

AI Agent 生态由两个正交的能力维度构成：

| 维度 | 解决的问题 | 代表框架 |
|------|-----------|---------|
| **编排能力**（怎么做） | 如何调用 LLM、检索文档、编排工具链 | LangChain / LangGraph / CrewAI |
| **自驱能力**（什么时候做、该不该做） | 自主触发、治理边界、持久执行、业务接入 | **OwlClaw** |

**这两个维度不是竞争关系，是同一个 Agent 的两半。**

### 与编排框架的关系：互补

LangChain 的 chain 可以注册为 OwlClaw 的 capability handler。OwlClaw 的 Agent 通过 function calling 决定什么时候调用它。用户已有的编排投资直接升级为自主 Agent。

```python
@app.handler(name="query_knowledge_base", knowledge="skills/kb-query/SKILL.md")
async def query_kb(question: str) -> str:
    return await rag_chain.ainvoke(question)
```

### 与个人 AI 助理的关系：不同问题域

| 维度 | 个人 AI 助理 | OwlClaw |
|------|-------------|---------|
| 核心问题 | "如何让 AI 帮我做事" | "如何让现有系统自己变聪明" |
| 入口 | 对话（IM 渠道） | 业务事件（Cron/Webhook/Queue/DB/API） |
| 价值来源 | 个人效率提升 | 企业数据资产激活 |
| 信任模型 | 个人信任 | 组织信任（治理 + 审计 + 预算） |
| 数据敏感度 | 个人数据，本地优先 | 企业数据，多租户隔离 |
| 失败代价 | 个人不便 | 业务损失，合规风险 |
| 规模 | 单用户单 Agent | 多租户多 Agent 多业务系统 |

两者通过 MCP 协议互通：OwlClaw 的 MCP Server 将业务能力暴露为通用 Agent 协议接口，任何 MCP 客户端均可连接。

### 与真正的竞品的关系

OwlClaw 的竞品不是编排框架，而是那些也在解决"自驱能力"的产品：

| 竞品 | 差异 |
|------|------|
| **Restate AI Loops** | 持久执行强，但无治理、无 Skills、无自主调度，且 BSL 许可证 |
| **MuleSoft Agent Fabric** | 企业治理强，但闭源、Salesforce 生态锁定 |
| **Microsoft Foundry** | 云托管强，但闭源、Azure 生态锁定 |
| **Letta (MemGPT)** | 记忆层强，但无治理、无业务接入、无持久执行 |

**没有一个开源产品同时提供**：自主调度 + 治理 + 业务接入 + Skills 知识体系 + 持久执行 + 编排框架标准接入。这是 OwlClaw 的差异化空间。

---

## 五、共享标准

OwlClaw 不发明新格式，复用已有的开放标准：

| 标准 | 来源 | OwlClaw 的使用方式 |
|------|------|------------------|
| **Agent Skills 规范** | agentskills.io（Anthropic 发起） | SKILL.md 格式，OwlClaw 的 `owlclaw:` 字段是兼容扩展 |
| **MCP 协议** | Anthropic 开源 | OwlClaw MCP Server 暴露业务能力为通用 Agent 协议接口 |
| **OpenTelemetry** | CNCF 标准 | 分布式追踪标准 |

---

## 六、核心价值排序

基于红军审视和市场分析，OwlClaw 的核心价值按优先级排序：

1. **业务接入层**（核心壁垒）：scan → migrate → SKILL.md → Declarative Binding，让已有系统零代码接入 AI 能力
2. **治理层**（企业门槛）：可见性过滤 + Ledger 审计 + 预算控制 + 熔断限流，满足企业合规需求
3. **Skills 知识体系**（差异化）：SKILL.md 让业务人员用自然语言描述业务规则，Agent 自动理解
4. **持久执行**（集成能力）：通过 Hatchet（MIT）实现，崩溃恢复 + 调度 + cron
5. **编排框架标准接入**（生态杠杆）：LangChain/LangGraph/CrewAI 的 chain/workflow 一行代码注册为 capability

---

## 七、一句话定位

> **LangChain 给了 Agent 手和脚（编排能力），OwlClaw 给了 Agent 大脑和心跳（自驱能力）。OwlClaw 让已有的业务系统获得 AI 自主能力，无需重写一行业务代码。**

---

## 八、增长飞轮

增长飞轮对应的中长期技术承接已在 [docs/ARCHITECTURE_ANALYSIS.md](./ARCHITECTURE_ANALYSIS.md) §10 明确（Multi-Agent / 自我进化 / 可解释性 / OwlHub 安全治理 / 性能与规模）。

```
业务人员写 SKILL.md（纯自然语言描述业务需求）
        │
        ▼
Agent 自动工作，产生业务价值
        │
        ▼
口碑传播 → 更多企业加入 → 更多行业覆盖
        │
        ▼
OwlHub 积累行业 Skills 模板 → 同行业企业直接复用
        │
        ▼
网络效应：每多一个 Skill，所有同行业用户受益
```

**三层飞轮**：
1. **产品飞轮**：写 SKILL.md → Agent 工作 → 产生价值 → 口碑传播
2. **生态飞轮**：用户发布 Skills → OwlHub 积累 → 同行业复用 → 接入门槛持续降低
3. **数据飞轮**：Agent 运行数据 → Skills 质量评分 → 推荐优化 → Agent 决策更准

---

## 九、架构演进方向

> 详见 `docs/ARCHITECTURE_ANALYSIS.md` §10（spec: architecture-roadmap，已落地）

| 方向 | 阶段 | 与现有架构的衔接 |
|------|------|----------------|
| Multi-Agent 协作 | v2.0 | AgentRuntime 多实例 + Signal 触发器 Agent 间通信 |
| Agent 自我进化 | v2.0 | Ledger 执行历史 → 策略优化反馈闭环 |
| 可解释性 | v1.1 | Langfuse tracing + Ledger 决策推理链路 |
| OwlHub 安全治理 | v1.1 | PR 审核流程 + SKILL.md validator + 恶意 binding 检测 |
| 性能与规模 | 长期 | Hatchet 分布式 + Heartbeat 分片 |

---

## 附录：产品能力全景 → Spec 追溯矩阵

> 覆盖 OwlClaw 平台的**全部产品能力**，按产品阶段分层追溯到 spec。
> **进度数据不在此维护**——查看实时进度请看 `.kiro/specs/SPEC_TASKS_SCAN.md`（单一真源）。

### S0：工程基础

| 产品能力 | Spec |
|---------|------|
| 包结构 + pyproject.toml + MIT LICENSE | — |
| GitHub Actions CI（lint/test/build/release） | ci-setup |
| 统一本地开发环境（docker-compose + Makefile） | local-devenv |
| 测试分层（unit 零外部依赖 + integration skip） | test-infra |
| 仓库卫生（.gitignore + CODEOWNERS + .editorconfig） | repo-hygiene |

### S1：Agent 运行时（核心引擎）

| 产品能力 | Spec |
|---------|------|
| Agent Runtime（SOUL.md 身份 + function calling 决策循环） | agent-runtime |
| Heartbeat（无事不调 LLM，零成本空转） | agent-runtime |
| 内建工具（schedule/remember/recall/query_state/log_decision） | agent-tools |
| 记忆系统（STM + LTM + pgvector + Snapshot + 生命周期） | agent-memory |
| 统一配置（owlclaw.yaml + Pydantic + 环境变量 + 热更新） | configuration |
| Lite Mode（OwlClaw.lite() + InMemoryLedger） | — |
| app.run() 阻塞式启动 + 优雅关停 | — |

### S1.5：数据层

| 产品能力 | Spec |
|---------|------|
| SQLAlchemy 基础设施（Base/engine/session/Alembic） | database-core |
| 数据库运维 CLI（init/migrate/status/rollback/backup/restore） | cli-db |

### S2：治理层（企业级门槛）

| 产品能力 | Spec |
|---------|------|
| 能力可见性过滤（约束/预算/熔断/限流/角色） | governance |
| 执行 Ledger（全量审计记录） | governance |
| 模型路由（task_type → 模型选择） | governance |
| 安全模型（Prompt Injection + 高风险确认 + 数据脱敏） | security |
| 渐进式迁移 migration_weight（0%→100%） | progressive-migration |
| Skills 质量评分（执行指标 → 评分 → 趋势告警） | skills-quality |

### S3：业务接入层（核心壁垒）

| 产品能力 | Spec |
|---------|------|
| Skills 挂载（SKILL.md 加载 + @handler/@state 注册） | capabilities-skills |
| Declarative Binding（HTTP/Queue/SQL + Shadow 模式） | declarative-binding |
| AST 扫描器（owlclaw scan → SKILL.md 骨架） | cli-scan |
| AI 辅助迁移（owlclaw migrate → binding SKILL.md） | cli-migrate |
| Skills CLI（init/validate/list/search/install/publish） | cli-skill |
| SKILL.md 模板库（5 类通用模板） | skill-templates |
| SKILL.md 自然语言书写（P1 触发解析+缓存，P2 工具匹配） | skill-dx |
| AI 辅助 Skill 生成（P1 对话式+模板，P2 文档提取） | skill-ai-assist |

### S4：触发器层（六种事件入口）

| 产品能力 | Spec |
|---------|------|
| Cron 触发器 | triggers-cron |
| Webhook 触发器 | triggers-webhook |
| 消息队列触发器（Kafka/RabbitMQ/Redis） | triggers-queue |
| 数据库变更触发器（NOTIFY/LISTEN + CDC） | triggers-db-change |
| API 调用触发器（REST → Agent Run） | triggers-api |
| Signal 触发器（暂停/恢复/强制/注入） | triggers-signal |

### S5：集成层（组合轮子）

| 产品能力 | Spec |
|---------|------|
| Hatchet 持久执行（崩溃恢复 + 调度 + cron） | integrations-hatchet |
| litellm LLM 统一接入（100+ 模型 + routing + fallback） | integrations-llm |
| Langfuse 可观测（tracing + evaluation） | integrations-langfuse |
| LangChain 生态接入（chain/workflow → capability） | integrations-langchain |
| MCP Server（通用 Agent 协议接口） | mcp-server |

### S6：Skills 生态（OwlHub + 网络效应）

| 产品能力 | Spec |
|---------|------|
| OwlHub Phase 1（GitHub 仓库索引 + PR 审核） | owlhub |
| OwlHub Phase 2（静态站点 + 搜索 + 分类） | owlhub |
| OwlHub 语义搜索推荐（用户描述 → 最佳模板建议） | industry-skills |
| OwlHub Phase 3（数据库后端，按需评估） | owlhub |

### S7：开源发布 + 落地

| 产品能力 | Spec |
|---------|------|
| PyPI 发布（owlclaw + owlclaw-mcp） | release |
| GitHub 开源（MIT） | release |
| Quick Start 指南（10 分钟上手） | quick-start |
| 完整端到端示例（可运行业务场景） | complete-workflow |
| 示例集（非交易 + LangChain + 3 行业 + mionyee） | examples |
| 端到端验证（mionyee 3 任务 + 决策质量对比） | e2e-validation |

### S8：架构前瞻（文档规划）

| 产品能力 | Spec |
|---------|------|
| 架构演进路线（Multi-Agent/自我进化/可解释性/安全/性能） | architecture-roadmap |

### 统计

50 项产品能力，覆盖 9 个阶段，映射到 41 个 spec。实时进度见 `SPEC_TASKS_SCAN.md`。

---

**维护者**: yeemio
**下次审核**: 2026-03-15
