# OwlClaw 架构分析：从调研到决策

> **创建时间**: 2026-02-10
> **前置文档**: `DEEP_ANALYSIS_AND_DISCUSSION.md`
> **目的**: 基于外部调研和内部代码分析，回答"OwlClaw 到底怎么做"

---

## 一、先承认问题

在之前的讨论中，我指出了 mionyee-agent 和 mionyee-platform 的一些问题。这些问题是真实的，不能因为定位清晰了就假装它们不存在。

### 1.1 mionyee-agent 的真实差距（对标 OpenClaw）

来源：`mionyee-agent/docs/architecture/gaps-with-openclaw.md`（你们自己的分析）

| 领域 | OpenClaw | mionyee-agent 现状 | 差距 |
|------|---------|-------------------|------|
| 调度与并发 | Lane队列 + 多种消息策略（Steer/Collect/Followup/Interrupt） | 无队列机制 | 🔴 严重 |
| 上下文守卫 | 多层防线 + 自动压缩 | 基础 Compaction | 🟡 中等 |
| 模型容错 | 认证轮转 + 模型降级链 | 单一 Provider | 🔴 严重 |
| Gateway架构 | 统一接入 + 安全拦截 + 路由 | 直接调用 | 🟠 较高 |
| 消息聚合 | 高频输入合并（避免token浪费） | 无 | 🔴 严重 |

**结论**：mionyee-agent 目前是"单用户、低并发"级别，不是生产级。

### 1.2 mionyee-platform 的治理层问题

之前我说"你们的治理重复了 Langfuse/Helicone"，这话说得不够准确。准确的说法是：

**你们做对了的**：
- policy_tick → ai/chat → ledger_record 的三步契约模式 —— 这是独创的，Langfuse 没有"先审批后调用"的概念
- task_type 路由 —— 按业务语义而非模型名称路由，这比 Helicone 的 proxy 模式更贴合业务

**你们不应该自己做的**：
- LLM调用的 tracing/logging —— Langfuse（开源）或 Helicone（开源）已经做得很好，支持 30+ 框架
- OpenTelemetry 集成 —— 应该直接用标准协议，不要自建
- 成本追踪的展示层 —— FinOps 的数据收集可以自己做，但展示/分析应该接 Langfuse

---

## 二、市场上已有什么（调研结果）

### 2.1 Agent 框架竞品分析

| 框架 | 入口 | 核心能力 | 治理 | 与OwlClaw的关系 |
|------|------|---------|------|---------------|
| **OpenClaw** | 对话（IM渠道） | 自主运行、工具执行、会话管理、Skills | Gateway安全拦截 | **互补**（对话入口，MCP通道） |
| **Restate** | 任何（框架无关） | 持久执行、Session、Multi-Agent、AI中间件 | 无（基础设施层） | 备选（BSL许可证，已选 Hatchet MIT） |
| **Dapr Agents** | 事件/Pub-Sub/HTTP | 持久执行、故障恢复、K8s原生、@tool装饰器 | Dapr生态 | ⚠️ 接近但太重（需Dapr sidecar） |
| **LangGraph** | 代码/API | 状态机、检查点、人工介入 | LangSmith（闭源） | ⚠️ 编排层好，缺业务接入层 |
| **Temporal** | 工作流定义 | 持久执行、故障恢复、人工介入 | Temporal Cloud | **组合**（企业级持久执行） |
| **OpenAI Agent SDK** | 代码 | Function calling、Handoff、Guardrails | 基础 | **组合**（Agent SDK 之一） |
| **CrewAI** | 代码 | 角色协作、Knowledge（RAG）、Memory | 基础 | ❌ 定位不同（多Agent编排） |
| **POLARIS**（学术） | 工作流 | 类型化DAG、策略护栏、审计轨迹 | 编译策略 | ⚠️ 治理思路可参考（非产品） |

**关键发现（2026年2月更新）**：

1. **没有一个框架是为"让成熟业务应用接入Agent能力"设计的** —— 它们都假设你从零开始构建
2. **Restate 已经在做 AI Agent 持久执行中间件** —— 2025年6月发布"Durable AI Loops"，支持 Vercel AI SDK、OpenAI Agent SDK。OwlClaw 应该与 Restate 组合，而不是在其之上再包一层
3. **Dapr Agents 2026年2月更新**，支持 Python @tool 装饰器、scale-to-zero，但仍需 Dapr sidecar
4. **Agent Skills 规范**（Anthropic 发起，2025年12月开源）已成为 Skills/知识文档的行业标准
5. **Context Engineering > Prompt Engineering** 已成为行业共识（Stanford/SambaNova 研究验证）

### 2.2 可观测/治理工具

| 工具 | 类型 | 开源 | 核心能力 | OwlClaw应该? |
|------|------|------|---------|-------------|
| **Langfuse** | LLM Observability | ✅ 完全开源 | Tracing、评估、Prompt管理、30+框架集成 | **集成**（不要自建tracing） |
| **Helicone** | LLM Gateway/Proxy | ✅ 完全开源 | 代理层缓存、限流、成本追踪、威胁检测 | **参考**（proxy模式可借鉴） |
| **OpenTelemetry** | 标准协议 | ✅ | 分布式追踪标准 | **采用**（作为OwlClaw的追踪标准） |

### 2.3 持久执行/工作流引擎

| 引擎 | 许可证 | 部署复杂度 | Python SDK | AI Agent 支持 | 适合OwlClaw? |
|------|--------|-----------|-----------|-------------|-------------|
| **Temporal** | MIT（Server） | 重（Server + DB） | ✅ 成熟 | ⚠️ 需自己封装 | ✅ 企业级首选 |
| **Restate** | **BSL**（Server）/ MIT（SDK） | 轻（单二进制） | ✅ 有SDK | ✅ AI中间件已有 | ⚠️ BSL风险 |
| **Hatchet** | **MIT** | 中（Go Server + PostgreSQL） | ✅ 有SDK | ⚠️ 任务队列定位 | ✅ **MIT替代** |
| **Inngest** | 开源 | 轻（事件驱动） | ✅ 有SDK | ⚠️ 基础 | ⚠️ 备选 |
| **Dapr Workflows** | Apache 2.0 | 中（需Dapr sidecar） | ✅ | ⚠️ 基础 | ❌ 太重 |

**关键发现（许可证风险更新）**：

1. **Restate Server 是 BSL（Business Source License），不是 MIT**
   - SDK 是 MIT（可自由使用）
   - Server 的 BSL 限制：不能用 Restate 做"公共托管平台服务"（即不能做 Restate Cloud 的竞品）
   - **对 OwlClaw 的影响**：OwlClaw 自己用 Restate 没问题（BSL 明确允许内部部署和自用）。但如果 OwlClaw Cloud 要托管 Restate 给第三方用户，需要评估是否构成"Public Restate Platform Service"
   - BSL 4年后转为 Apache 2.0（每个版本独立计算）
2. **Temporal Server 是 MIT** —— 完全自由，无任何商用限制
3. **Hatchet 是 MIT** —— 完全自由，6500+ GitHub stars，定位为"现代 Celery 替代"，支持 durable execution + cron + 调度
4. **最终决策**：MVP 选择 **Hatchet（MIT）**。理由：MIT 零风险 + Cron 一等公民 + 生产验证（1亿+任务/天）+ 共用 PostgreSQL。详见决策5

---

## 三、OwlClaw 的定位 —— 组合而非重造

### 3.1 AI 时代的产品哲学

> **AI 时代的核心竞争力不是"我有别人没有的"，而是"我能把成熟能力组合得最快最好"。**

试错成本很低，差异化不是重点。重点是：谁能把 Hatchet 的持久执行 + Agent Skills 的知识规范 + OpenClaw 的自主哲学 + litellm 的模型统一 + Langfuse 的可观测性，**快速组合成一个面向业务应用的解决方案**。

OwlClaw 不是要重造任何一个轮子。它是一个**组合层** —— 把成熟的开源能力组合起来，解决一个没人解决的问题：**让已有成熟业务系统获得 AI 自主能力，而不需要重写。**

### 3.2 从 OpenClaw 学到的核心哲学

深入读了 OpenClaw/moltbot 的代码后，最大的启发不是某个具体机制，而是一个设计哲学：

> **不要试图控制 AI，而是给 AI 提供它需要的一切，让它自己来。**

OpenClaw 的 Agent 有灵魂（SOUL.md）、有记忆（MEMORY.md + 向量搜索）、有知识（Skills 注入 prompt）、有工具（function calling）、有自我调度能力（cron tool + heartbeat）。它是一个**自主的实体**。

OwlClaw 要做的是：把这套"让 AI 活起来"的基础设施，从对话场景迁移到**业务应用场景**。

### 3.3 OwlClaw 的组合公式

```
OwlClaw = 业务应用接入层（自建，核心价值）
        + Agent 运行时（身份/记忆/知识/工具，自建）
        + 治理层（可见性过滤/Ledger/预算，自建）
        + Agent Skills 规范（Anthropic 开源标准，采用）
        + 持久执行（Hatchet MIT，集成）
        + LLM 调用（litellm，集成）
        + 可观测（Langfuse + OpenTelemetry，集成）
        + 对话通道（OpenClaw via MCP，集成）
```

**自建的是没人做的**：业务应用接入、治理、Agent 运行时。
**集成的是已经做好的**：持久执行、LLM、可观测、对话。

---

## 四、架构决策

### 4.1 决策1：在 OwlClaw 上直接开始

| 维度 | 在 mionyee-agent 上继续 | 在 OwlClaw 上重新开始 |
|------|----------------------|---------------------|
| 目标对齐 | mionyee-agent 对标 OpenClaw（对话式） | OwlClaw 面向业务应用，目标不同 |
| 技术债务 | 5个🔴严重差距需要补 | 从一开始就按正确的架构来 |
| 代码复用 | 治理钩子、工具策略可以搬过来 | 选择性搬运设计模式，不搬代码 |
| 开源友好 | 有大量 mionyee 业务耦合 | 干净的开源仓库 |

### 4.2 决策2：Agent 自驱动，不是外部循环驱动

**这是 v3 架构与 v2 最根本的区别。**

v2 的设计是一个外部 OODA 循环在替 Agent 做决策：`Observe → Orient → Decide → Act → Reflect → Schedule Next`。这个循环的每一步都是预定义的，LLM 只是在 `Decide` 步骤被调用来做判断。

**问题**：
1. **LLM 调用频率高** —— 每次循环都要调用 LLM 做 Decide + Reflect，即使什么都没发生
2. **决策空间被框架限制** —— Agent 只能在框架预设的 OODA 步骤中做选择，不能自由组合动作
3. **与 OpenClaw 的成功经验矛盾** —— OpenClaw 证明了 Agent 自己通过 function calling 做决策比外部循环更灵活、更高效

**v3 的设计哲学**（从 OpenClaw 学到的）：

> **OwlClaw 不是一个控制 Agent 的框架，而是一个赋能 Agent 的基础设施。**

具体来说：
- **Agent 自己决定做什么** —— 通过 function calling 从注册的 capability 中选择
- **Agent 自己决定什么时候做** —— 通过 `schedule` 工具自我调度
- **Agent 有持续的身份和记忆** —— 不是每次调用都从零开始
- **Agent 有业务知识** —— 每个 capability 不只是一个函数签名，而是附带完整的业务知识文档
- **无事时零成本** —— heartbeat 机制检查是否有待处理的事件，没有就不调用 LLM

### 4.3 决策3：采用 Agent Skills 规范（Anthropic 开源标准）

Anthropic 在 2025 年 12 月发布了 Agent Skills 开放规范（agentskills.io）。OwlClaw 直接采用这个规范，不自己发明格式。

**Agent Skills 规范的核心**：
- Skill = 一个文件夹，包含 `SKILL.md`（YAML frontmatter + Markdown 指令）
- 可选 `scripts/`、`references/`、`assets/` 子目录
- 渐进式加载：启动时只加载 metadata（~100 tokens），激活时才加载完整指令

**OwlClaw 的创新**：Skills 不是 Agent 自己的，而是**业务应用自带的**。

```
# 传统 Agent（OpenClaw 等）：Skills 在 Agent 目录里
~/.openclaw/skills/
├── git-workflow/SKILL.md
├── code-review/SKILL.md
└── ...

# OwlClaw：Skills 在业务应用目录里，由 OwlClaw 运行时挂载
mionyee/
├── capabilities/                    # 业务应用自带的 Skills
│   ├── entry-monitor/
│   │   ├── SKILL.md                # 遵循 Agent Skills 规范
│   │   ├── references/
│   │   │   └── trading-rules.md    # 交易规则参考
│   │   └── scripts/
│   │       └── check_signals.py    # 辅助脚本
│   ├── morning-decision/
│   │   └── SKILL.md
│   └── knowledge-feedback/
│       └── SKILL.md
└── owlclaw.yaml                    # OwlClaw 配置
```

**OwlClaw 扩展的 frontmatter 字段**（兼容 Agent Skills 规范，额外增加业务字段）：

```yaml
---
name: entry-monitor
description: 检查持仓股票的入场机会，当价格到达入场区间时识别建仓时机
# ── Agent Skills 标准字段 ──
metadata:
  author: mionyee-team
  version: "1.0"
# ── OwlClaw 扩展字段 ──
owlclaw:
  task_type: trading_decision        # AI 路由
  constraints:
    trading_hours_only: true
    cooldown_seconds: 300
    max_daily_calls: 50
  trigger: cron("*/60 * * * * *")    # 关联触发器
---
```

**好处**：
1. 业务应用开发者写 Skills，他们最懂自己的业务
2. Skills 和业务代码放在一起版本控制
3. OwlClaw 不需要内建大量 Skills，只需要提供挂载机制
4. 兼容 Agent Skills 生态 —— 其他 Agent 产品的 Skills 可以被 OwlClaw 使用，反之亦然

### 4.4 决策4：多语言仓库，包级别独立

```
owlclaw/
├── owlclaw/                # 核心 Python SDK（pip install owlclaw）
│   ├── agent/              # Agent 运行时（身份、记忆、知识、决策）
│   ├── capabilities/       # 能力注册、Skills 加载（Agent Skills 规范）
│   ├── governance/         # 能力可见性过滤、执行记录、守卫
│   ├── triggers/           # 事件触发器（cron/webhook/queue/db/api/file）
│   ├── tools/              # Agent 内建工具（schedule、memory、query_state）
│   ├── cli/                # owlclaw scan / owlclaw migrate
│   ├── integrations/       # litellm、Langfuse、Hatchet 等集成
│   └── pyproject.toml
├── owlclaw-mcp/            # MCP Server（OpenClaw 通道）
├── examples/
├── docs/
├── tests/
├── pyproject.toml          # workspace 根配置
├── LICENSE                 # MIT
└── README.md
```

**注意变化**：不再有独立的持久执行包。Hatchet 集成放在 `owlclaw/integrations/hatchet.py` 中，集中隔离。原因见决策5。

### 4.5 决策5：Hatchet 作为持久执行基础设施

**最终选择：Hatchet（MIT）**

基础层代码不应该频繁改动，也不应该承担许可证风险。经过 Hatchet / Restate / Temporal 的严格对比：

| 维度 | **Hatchet** ✅ | Restate | Temporal |
|------|------------|---------|---------|
| 许可证 | **MIT** | BSL（Server） | MIT |
| Cron 支持 | **一等公民，内建** | 需自己实现 | Schedule |
| 部署 | Docker（Server + PostgreSQL） | 单二进制 | Docker（Server + PostgreSQL） |
| 生产规模 | **1亿+ 任务/天** | 较新，3.4k stars | 大量企业部署 |
| Python SDK | ✅ monorepo 内 | ✅ v0.14.2 | ✅ 成熟 |
| Durable Sleep | ✅ `aio_sleep_for` | ✅ `ctx.sleep` | ✅ `workflow.sleep` |
| 调度/延迟执行 | ✅ `schedule_task` | ✅ `service_send` | ✅ `start_workflow` |
| AI 中间件 | 无（我们自己做） | 有（但我们不需要） | 无 |
| 学习曲线 | 低（类 Celery） | 中 | 高 |

**选择 Hatchet 的理由**：

1. **MIT 许可证** —— 基础层零许可证风险，OwlClaw Cloud 未来商业化无障碍
2. **Cron 一等公民** —— OwlClaw 的第一个触发器就是 cron，Hatchet 内建支持，不需要自己实现
3. **生产验证** —— 每天 1 亿+ 任务，Aevy/Greptile/Moonhub 等生产案例
4. **共用 PostgreSQL** —— OwlClaw 本身需要 PostgreSQL（Ledger + Memory），Hatchet 共用同一实例，实际增加的部署复杂度只是一个 Hatchet Server 容器
5. **AI 中间件自己做** —— OwlClaw 的 Agent 运行时（身份、记忆、知识注入、function calling、治理过滤）本身就是 AI 中间件。我们需要的是底层的持久执行 + 调度 + cron，不多不少。Hatchet 提供的恰好是这个

**不选 Restate 的理由**：
- BSL 许可证是基础层的隐患（即使当前允许，未来条款可能变化，HashiCorp 前车之鉴）
- Cron 需要自己实现
- AI 中间件是 Restate 的卖点，但 OwlClaw 不需要（我们自己做 Agent 运行时）

**不选 Temporal 的理由**：
- 部署复杂度高（需要 Temporal Server + DB），对"已有成熟应用想快速接入"的用户是阻碍
- 学习曲线陡（workflow 范式）
- 但如果未来有企业用户需要 Temporal 的高级能力（Signal/Query/子工作流），可以作为 P2 支持

**集成方式**：Hatchet 调用集中在 `owlclaw/integrations/hatchet.py`，保持隔离。

### 4.6 决策6：集成边界

| 能力 | 自建 | 集成 | 理由 |
|------|------|------|------|
| Agent 运行时（身份/记忆/知识/决策） | ✅ | | 核心价值 |
| 能力注册 + Skills 挂载 | ✅ | | 核心价值 |
| 能力可见性过滤（治理） | ✅ | | 核心价值 |
| 事件触发器统一层 | ✅ | | 核心价值 |
| Agent 内建工具（schedule/memory） | ✅ | | 核心价值 |
| Skills 格式 | | ✅ Agent Skills 规范 | Anthropic 开源标准 |
| 持久执行 | | ✅ Hatchet（MIT） | 直接集成，共用 PostgreSQL |
| LLM 客户端 | | ✅ litellm | 统一 100+ 模型 |
| LLM 调用 tracing | | ✅ Langfuse | 不重复造轮子 |
| 分布式追踪 | | ✅ OpenTelemetry | 标准协议 |
| 对话通道 | | ✅ MCP（OpenClaw） | 标准协议 |
| 向量存储 | | ✅ 业务应用自己选 | OwlClaw 只定义接口 |

---

## 五、OwlClaw 架构设计（v3 — Agent 自驱动）

### 5.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           外部通道                                       │
│                                                                          │
│  ┌──────────────┐         ┌──────────────────────────────┐              │
│  │  OpenClaw     │◄─MCP──►│  OwlClaw MCP Server          │              │
│  │  (对话入口)   │         │  (暴露能力 + 控制 + 状态)     │              │
│  └──────────────┘         └──────────────┬───────────────┘              │
│                                          │                               │
└──────────────────────────────────────────┼──────────────────────────────┘
                                           │
┌──────────────────────────────────────────┼──────────────────────────────┐
│                        业务应用层         │                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐│  ┌──────────┐               │
│  │ mionyee  │  │ 风控系统  │  │ CRM系统  ││  │ 其他应用  │               │
│  │ (交易)   │  │          │  │          ││  │          │               │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘│  └────┬─────┘               │
│       │              │              │      │       │                     │
│       └──────────────┴──────────────┴──────┴───────┘                     │
│                              │                                           │
│                    OwlClaw Python SDK                                    │
│                    (pip install owlclaw)                                 │
│                                                                          │
│     注册方式:                                                            │
│     ├── @app.capability(knowledge="docs/entry_monitor.md")              │
│     ├── @app.state(name="market_state")                                 │
│     └── app.trigger(from_cron(...) / from_webhook(...) / ...)           │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     OwlClaw Agent 基础设施                               │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Agent 运行时 (Agent Runtime)                                     │   │
│  │                                                                    │   │
│  │  ┌─ 身份 (Identity) ─────────────────────────────────────────┐   │   │
│  │  │  SOUL.md    → Agent 的角色定位和行为准则                    │   │   │
│  │  │  IDENTITY.md → Agent 管理的应用、能力范围、约束             │   │   │
│  │  └────────────────────────────────────────────────────────────┘   │   │
│  │                                                                    │   │
│  │  ┌─ 记忆 (Memory) ──────────────────────────────────────────┐   │   │
│  │  │  短期: 当前 run 的上下文（事件 + 状态 + 最近动作）         │   │   │
│  │  │  长期: MEMORY.md + 向量搜索（跨 run 的经验和教训）         │   │   │
│  │  └────────────────────────────────────────────────────────────┘   │   │
│  │                                                                    │   │
│  │  ┌─ 知识 (Knowledge) ───────────────────────────────────────┐   │   │
│  │  │  每个 capability 附带的业务知识文档（Markdown）             │   │   │
│  │  │  → 注入 system prompt，引导 Agent 理解业务语义             │   │   │
│  │  │  → 类似 OpenClaw 的 Skills，但面向业务能力而非对话技能     │   │   │
│  │  └────────────────────────────────────────────────────────────┘   │   │
│  │                                                                    │   │
│  │  ┌─ 决策 (Decision via Function Calling) ───────────────────┐   │   │
│  │  │  Agent 通过 LLM function calling 从可见的工具中选择动作    │   │   │
│  │  │  可见工具 = 业务能力 + 内建工具 - 治理过滤                 │   │   │
│  │  │  → 不是外部循环替 Agent 决策                               │   │   │
│  │  │  → 是 Agent 自己看到工具列表后自主选择                     │   │   │
│  │  └────────────────────────────────────────────────────────────┘   │   │
│  │                                                                    │   │
│  │  ┌─ 内建工具 (Built-in Tools) ─────────────────────────────┐   │   │
│  │  │  schedule_once(delay, focus)  → 自我调度（一次性）         │   │   │
│  │  │  schedule_cron(expr, focus)   → 自我调度（周期性）         │   │   │
│  │  │  cancel_schedule(id)          → 取消已调度的任务           │   │   │
│  │  │  remember(content)            → 写入长期记忆               │   │   │
│  │  │  recall(query)                → 搜索长期记忆               │   │   │
│  │  │  query_state(name)            → 查询业务状态               │   │   │
│  │  │  log_decision(reasoning)      → 记录决策理由               │   │   │
│  │  └────────────────────────────────────────────────────────────┘   │   │
│  └──────────────────────────┬───────────────────────────────────────┘   │
│                             │                                            │
│  ┌──────────────────────────▼───────────────────────────────────────┐   │
│  │  治理层 (Governance Layer) — 能力可见性过滤                       │   │
│  │                                                                    │   │
│  │  Agent 看到的工具列表不是全集，而是经过多层过滤后的子集：          │   │
│  │                                                                    │   │
│  │  全部注册能力                                                      │   │
│  │    → 约束过滤（trading_hours_only → 非交易时间不可见）            │   │
│  │    → 预算过滤（月预算用完 → 高成本能力不可见）                    │   │
│  │    → 熔断过滤（连续失败 → 暂时不可见）                            │   │
│  │    → 限流过滤（频率超限 → 暂时不可见）                            │   │
│  │    → 角色过滤（Agent 角色权限范围内的能力）                        │   │
│  │    = Agent 实际可见的工具列表                                      │   │
│  │                                                                    │   │
│  │  + 执行后记录（Ledger）：每次 function call 执行都记录             │   │
│  │  + AI 路由（Router）：task_type → 模型选择                        │   │
│  │  + Langfuse 集成：自动 tracing                                    │   │
│  └──────────────────────────┬───────────────────────────────────────┘   │
│                             │                                            │
│  ┌──────────────────────────▼───────────────────────────────────────┐   │
│  │  事件触发层 (Trigger Layer) — 唤醒 Agent                          │   │
│  │                                                                    │   │
│  │  什么时候 Agent 会被唤醒（产生一次 agent run）：                   │   │
│  │                                                                    │   │
│  │  1. 自我调度触发 → Agent 之前调用 schedule_once/schedule_cron     │   │
│  │  2. Heartbeat 触发 → 周期性检查 HEARTBEAT.md，有事才调 LLM       │   │
│  │  3. 事件触发 → from_cron/from_webhook/from_queue/from_db/from_api │   │
│  │  4. 外部触发 → MCP 调用 / CLI 命令 / API 请求                    │   │
│  │  5. Signal 触发 → 人工介入（暂停/恢复/强制执行）                  │   │
│  │                                                                    │   │
│  │  所有触发统一进入 → Agent Run → LLM 决策 → 执行                   │   │
│  └──────────────────────────┬───────────────────────────────────────┘   │
│                             │                                            │
│  ┌──────────────────────────▼───────────────────────────────────────┐   │
│  │  持久执行层 (Durable Execution) — Hatchet（MIT）                  │   │
│  │                                                                    │   │
│  │  直接集成 Hatchet：                                                │   │
│  │  ├── @hatchet.task()          → 持久化任务（崩溃恢复 + 重试）     │   │
│  │  ├── ctx.aio_sleep_for(delay) → 持久化定时（进程重启继续计时）    │   │
│  │  ├── schedule_task(delay)     → 延迟执行 / 自我调度               │   │
│  │  ├── cron trigger             → 内建 Cron 一等公民                │   │
│  │  └── Dashboard                → 内建可视化 + 监控                 │   │
│  │                                                                    │   │
│  │  共用 PostgreSQL（OwlClaw Ledger + Memory + Hatchet）             │   │
│  └──────────────────────────┬───────────────────────────────────────┘   │
│                             │                                            │
│  ┌──────────────────────────▼───────────────────────────────────────┐   │
│  │  集成层 (Integration Layer)                                       │   │
│  │  - LLM: litellm (统一 100+ 模型)                                  │   │
│  │  - Tracing: Langfuse / OpenTelemetry                              │   │
│  │  - 持久执行: Hatchet（MIT，共用 PostgreSQL）                      │   │
│  │  - 存储: SQLAlchemy + PostgreSQL（ledger、memory、hatchet）       │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.2 核心概念

#### 5.2.1 Agent = 身份 + 记忆 + 知识 + 工具 + 自我调度

这是 v3 架构的核心模型。OwlClaw 的 Agent 不是一个无状态函数，而是一个**有身份、有记忆、有知识的持续实体**。

**身份（Identity）**：

```markdown
<!-- SOUL.md — Agent 的角色定位 -->
你是 mionyee-trading 的 AI 交易助手。

## 行为准则
- 所有交易决策必须由你（AI）做出，禁止硬编码规则
- 在交易时间内，你需要主动监控市场状态并寻找机会
- 每次决策后，反思结果并更新你的经验
- 当你不确定时，选择保守策略（不操作比错误操作好）
- 非交易时间，你应该进行知识整理和策略评估

## 你管理的应用
- mionyee 股票分析系统（1164个Python文件，48个原始cron任务）
- 你的职责是替代原来的cron调度，用你的判断来决定什么时候做什么
```

```markdown
<!-- IDENTITY.md — Agent 的能力范围 -->
## 我的能力
- check_entry_opportunity: 检查入场机会（交易时间内）
- execute_entry: 执行建仓（需要入场机会数据）
- morning_decision: 盘前决策（09:30-09:45）
- knowledge_feedback: 知识反馈生成（盘后）
- ... (更多能力)

## 我的约束
- 月度AI调用预算: ¥500
- 单次交易金额上限: ¥50,000
- 连续失败3次后暂停该能力30分钟
```

**记忆（Memory）**：

```python
# Agent 的记忆系统
class AgentMemory:
    """
    短期记忆: 当前 run 的上下文
    长期记忆: MEMORY.md + 向量搜索（跨 run 持久化）
    
    参考 OpenClaw 的 memory-tool.ts:
    - Agent 通过 remember() 工具主动写入记忆
    - Agent 通过 recall() 工具搜索历史记忆
    - 记忆自动带时间戳和上下文标签
    """
    
    async def remember(self, content: str, tags: list[str] = None):
        """Agent 主动记住某件事"""
        # 写入 MEMORY.md + 向量索引
        ...
    
    async def recall(self, query: str, limit: int = 5) -> list[str]:
        """Agent 搜索相关记忆"""
        # 向量搜索 + 时间衰减
        ...
    
    def get_recent_context(self, max_tokens: int = 2000) -> str:
        """获取最近的上下文（注入 prompt）"""
        ...
```

**知识（Knowledge）—— 采用 Agent Skills 规范**：

OwlClaw 采用 Anthropic 发起的 Agent Skills 开放规范（agentskills.io，2025年12月发布）作为知识文档格式。每个 capability 对应一个 Skill 文件夹：

```
mionyee/capabilities/entry-monitor/
├── SKILL.md                    # 遵循 Agent Skills 规范
├── references/
│   └── trading-rules.md        # 交易规则参考
└── scripts/
    └── check_signals.py        # 辅助脚本
```

```markdown
<!-- SKILL.md -->
---
name: entry-monitor
description: 检查持仓股票的入场机会，当价格到达入场区间时识别建仓时机。
metadata:
  author: mionyee-team
  version: "1.0"
owlclaw:
  task_type: trading_decision
  constraints:
    trading_hours_only: true
    cooldown_seconds: 300
---

# 入场机会检查 — 使用指南

## 什么时候应该调用这个能力
- 交易时间内（09:30-15:00），当市场有波动时
- 大盘出现急跌后的反弹信号
- 个股到达你之前设定的目标价位

## 什么时候不应该调用
- 非交易时间
- 刚执行过（5分钟内），除非市场出现剧烈变化
- 当天已经建仓3次以上（风控限制）

## 调用后如何解读结果
- opportunities 为空 → 降低检查频率
- opportunities 非空 → 评估质量，决定是否调用 execute_entry

## 与其他能力的关系
- 发现机会后，通常接着调用 execute_entry
- 波动大时，先调用 query_state("market_state") 确认市场阶段

详细交易规则见 [references/trading-rules.md](references/trading-rules.md)
```

**渐进式加载**（Agent Skills 规范的核心设计）：
1. 启动时只加载 frontmatter（~100 tokens/skill）—— Agent 知道有哪些能力
2. 触发时按上下文选择性加载完整指令 —— 只注入相关的 Skills
3. references/ 按需加载 —— 只在 Agent 需要深入了解时才读取

**与 Agent Skills 生态的兼容**：OwlClaw 的 Skills 可以被其他支持 Agent Skills 规范的产品使用，反之亦然。OwlClaw 的 `owlclaw:` 扩展字段对其他产品透明（它们只读标准字段）。

#### 5.2.2 Agent Run 的生命周期

Agent 不是一个永远运行的循环。它是**事件驱动**的：有事才醒，醒了就做，做完就安排下次，然后休眠。

```
┌─────────────────────────────────────────────────────────┐
│                    Agent Run 生命周期                      │
│                                                           │
│  触发事件                                                 │
│    │                                                      │
│    ▼                                                      │
│  组装 System Prompt                                       │
│    ├── SOUL.md（身份）                                    │
│    ├── IDENTITY.md（能力范围）                             │
│    ├── 最近记忆（recall 相关上下文）                       │
│    ├── 当前状态（query_state 快照）                        │
│    ├── 触发事件描述（"heartbeat 检查" / "cron 触发" / ...) │
│    └── 相关能力的知识文档（按触发上下文选择性注入）         │
│    │                                                      │
│    ▼                                                      │
│  LLM Function Calling                                     │
│    ├── 可见工具 = 业务能力 + 内建工具 - 治理过滤           │
│    │                                                      │
│    │  LLM 自主选择：                                      │
│    │  ├── 调用业务能力（check_entry_opportunity）          │
│    │  ├── 调用多个能力（连续 function call）               │
│    │  ├── 自我调度（schedule_once(300, "检查入场")）       │
│    │  ├── 记住经验（remember("今天急跌后反弹信号准确")）   │
│    │  ├── 什么都不做（"当前无需操作"）                     │
│    │  └── 或以上的任意组合                                 │
│    │                                                      │
│    ▼                                                      │
│  执行 + 治理记录                                          │
│    ├── 每个 function call 都经过治理层                     │
│    ├── 执行结果返回给 LLM                                 │
│    ├── LLM 可以继续调用更多工具（多轮 function calling）   │
│    └── 直到 LLM 认为本次 run 完成                         │
│    │                                                      │
│    ▼                                                      │
│  Run 结束                                                 │
│    ├── 所有执行记录写入 Ledger                             │
│    ├── Langfuse trace 完成                                │
│    └── Agent 休眠，等待下一次触发                          │
└─────────────────────────────────────────────────────────┘
```

**与 v2 OODA 循环的关键区别**：

| 维度 | v2 OODA 循环 | v3 Agent Run |
|------|-------------|-------------|
| 决策者 | 框架代码（`AutonomousLoop.run()`） | LLM 自己（function calling） |
| 步骤 | 固定 6 步（O-O-D-A-R-S） | LLM 自由组合任意工具调用 |
| LLM 调用 | 每次循环至少 2 次（Decide + Reflect） | 仅在触发时 1 次（可能多轮） |
| 调度 | 框架在 Reflect 后调用 `engine.sleep()` | Agent 自己调用 `schedule_once()` 工具 |
| 无事时 | 仍然执行 Observe + Orient + Decide（浪费） | Heartbeat 检查，无事不调 LLM（零成本） |
| 灵活性 | 只能在 6 步中选择 | 可以一次 run 中做任意多件事 |

#### 5.2.3 Heartbeat — 零成本的主动性

从 OpenClaw 学到的最精妙的机制。

**问题**：Agent 如何在没有外部事件时保持"主动性"？v2 的答案是 OODA 循环不断轮询。但这意味着即使什么都没发生，每次循环也要调用 LLM。

**OpenClaw 的答案**：Heartbeat。

```python
# owlclaw/agent/heartbeat.py
class HeartbeatRunner:
    """
    周期性检查是否有待处理的事情。
    
    关键设计：如果没有待处理的事情，不调用 LLM。
    这意味着 Agent 在空闲时的成本是零。
    
    参考 OpenClaw 的 heartbeat-runner.ts:
    - 默认每 30 分钟运行一次
    - 检查 HEARTBEAT.md 文件
    - 如果文件为空或无可操作内容 → 跳过，不调 LLM
    - 如果有内容 → 触发一次 Agent Run
    """
    
    def __init__(self, agent: Agent, interval_minutes: int = 30):
        self.agent = agent
        self.interval = interval_minutes
    
    async def tick(self):
        # 1. 收集待处理事件（不调用 LLM）
        pending_events = await self._collect_pending()
        
        # 2. 如果没有待处理的事件 → 跳过
        if not pending_events:
            return  # 零成本！
        
        # 3. 有事件 → 触发 Agent Run
        await self.agent.run(
            trigger="heartbeat",
            context=f"以下是待处理的事件：\n{pending_events}",
        )
    
    async def _collect_pending(self) -> str | None:
        """收集待处理事件（纯内部状态检查，零外部 I/O）
        
        边界定义（参考 OpenClaw heartbeat-runner.ts 的 6 层过滤）：
        - ✅ 内存中的事件队列（待处理事件）
        - ✅ 调度表（到期的 schedule）
        - ✅ 状态变更标志（dirty flag，不是重新查询外部状态）
        - ❌ 不调用外部 API（行情、数据库重查询）
        - ❌ 不做网络请求
        - ❌ 不读取大文件
        """
        items = []
        
        # 检查内存中的状态变更标志（不是重新查询外部状态）
        for state in self.agent.states:
            if state.dirty_flag:  # 内存标志，非外部查询
                items.append(f"- 状态变化: {state.name}")
        
        # 检查到期的调度（内存中的调度表）
        for schedule in self.agent.pending_schedules:
            if schedule.is_due():
                items.append(f"- 到期调度: {schedule.focus}")
        
        # 检查未处理的外部事件（内存中的事件队列）
        for event in self.agent.unprocessed_events:
            items.append(f"- 未处理事件: {event.description}")
        
        return "\n".join(items) if items else None
```

**成本对比**：

| 场景 | v2 OODA 循环 | v3 Heartbeat |
|------|-------------|-------------|
| 交易日盘中（6小时） | ~720 次 LLM 调用（每30s一次循环） | ~12 次 Heartbeat 检查 + 按需 LLM 调用 |
| 非交易日 | ~2880 次 LLM 调用（循环不停） | 48 次 Heartbeat 检查，0 次 LLM 调用 |
| 月度估算（22个交易日） | ~80,000 次 LLM 调用 | ~500 次 LLM 调用（仅有事时） |

**这不是小优化，是量级差异。** v2 的 OODA 循环在非交易日也在不断调用 LLM 做 Decide（"现在该做什么？" → "什么都不做"），这是纯粹的浪费。v3 的 Heartbeat 在非交易日检查到"没有待处理事件"后直接跳过，LLM 调用次数为零。

#### 5.2.4 能力注册与 Skills 挂载

```python
from owlclaw import OwlClaw

app = OwlClaw("mionyee-trading")

# ── 挂载业务应用的 Skills 目录 ──
# Skills 遵循 Agent Skills 规范（SKILL.md）
# OwlClaw 自动发现、加载 metadata、注册为 capability
app.mount_skills("./capabilities/")

# ── 注册 capability 的 handler（与 Skill 关联）──
@app.handler("entry-monitor")  # 对应 capabilities/entry-monitor/SKILL.md
async def check_entry_opportunity(session) -> dict:
    monitor_service = get_entry_monitor_service()
    return await monitor_service.check_entry_opportunities(
        session=session, user_id=DEFAULT_USER_ID
    )

@app.handler("execute-entry")
async def execute_entry(opportunity: dict, session) -> dict:
    execution_service = get_entry_execution_service()
    return await execution_service.execute_entry(opportunity, session)

# ── 注册状态 ──
@app.state(name="market_state")
async def get_market_state() -> dict:
    return {
        "is_trading_time": is_trading_time(),
        "phase": get_current_market_phase(),
        "volatility": get_current_volatility(),
    }

# ── 配置 Agent ──
app.configure(
    soul="docs/SOUL.md",
    identity="docs/IDENTITY.md",
    heartbeat_interval_minutes=30,
)

app.run()
```

**Skill 和 handler 的分离**是关键设计：
- **Skill（SKILL.md）** 定义"是什么、什么时候用、怎么理解结果" —— 业务知识
- **handler（Python 函数）** 定义"怎么执行" —— 业务逻辑
- 两者通过 `name` 关联，但可以独立维护和版本控制

#### 5.2.5 治理 = 能力可见性过滤 + 执行记录

v2 的治理是 `policy_tick → execute → record` 三步协议，在 OODA 循环的 Governance 步骤中执行。

v3 的治理更自然：**Agent 看到的工具列表本身就是经过治理过滤的**。

```python
# owlclaw/governance/visibility.py
class CapabilityVisibilityFilter:
    """
    多层过滤，决定 Agent 在当前 run 中能看到哪些工具。
    
    参考 OpenClaw 的 policy filtering:
    - Profile Policy → Provider Policy → Global Policy → Agent Policy
    - 每层都可以增加或移除工具
    
    OwlClaw 的过滤层：
    """
    
    def filter(self, all_capabilities: list, context: RunContext) -> list:
        visible = all_capabilities.copy()
        
        # 1. 约束过滤 — 静态规则
        visible = [c for c in visible 
                   if self._check_constraints(c, context)]
        # 例：trading_hours_only=True 的能力在非交易时间不可见
        
        # 2. 预算过滤 — 成本控制
        visible = [c for c in visible 
                   if self._check_budget(c, context)]
        # 例：月预算用完后，高成本能力不可见
        
        # 3. 熔断过滤 — 故障保护
        visible = [c for c in visible 
                   if self._check_circuit_breaker(c)]
        # 例：连续失败3次的能力暂时不可见
        
        # 4. 限流过滤 — 频率控制
        visible = [c for c in visible 
                   if self._check_rate_limit(c)]
        # 例：5分钟内已调用过的能力不可见（cooldown）
        
        # 5. 角色过滤 — 权限控制（企业版）
        # visible = [c for c in visible 
        #            if self._check_role(c, context.agent_role)]
        
        return visible
```

**为什么这比 v2 的 policy_tick 更好**：

| 维度 | v2 policy_tick | v3 可见性过滤 |
|------|---------------|-------------|
| 时机 | Agent 已经做出决策后才检查 | Agent 做决策前就看不到不该用的工具 |
| 体验 | Agent 选了一个能力，被拒绝，浪费一次 LLM 调用 | Agent 根本不会选不可用的能力 |
| 实现 | 需要在 OODA 循环中插入 Governance 步骤 | 自然融入 function calling 的工具列表构建 |
| 灵活性 | 只能拒绝/通过 | 可以动态调整工具列表（加/减/替换） |

**成本模型和预算控制的具体设计**：

| 维度 | 设计 |
|------|------|
| 预算粒度 | 按 Agent 实例（月度总预算）+ 按 capability（单次成本上限） |
| 成本来源 | LLM 调用（litellm cost tracking）+ Hatchet 任务执行（自定义计量） |
| 成本计算 | Ledger 自动累计每次 run 的 LLM token 成本，实时更新月度已用额度 |
| 超限行为 | **分级降级**：80% → 降级到便宜模型；100% → 高成本能力不可见，仅保留只读查询类能力 |
| 告警 | 50%/80%/100% 三级告警（通过 Hatchet 任务触发通知） |

```python
# 预算过滤的具体逻辑
def _check_budget(self, capability, context) -> bool:
    monthly_used = self.ledger.get_monthly_cost(context.agent_id)
    monthly_limit = context.agent_config.monthly_budget
    
    usage_ratio = monthly_used / monthly_limit
    
    if usage_ratio >= 1.0:
        # 预算用完：只保留零成本能力（如 recall、query_state）
        return capability.estimated_cost == 0
    elif usage_ratio >= 0.8:
        # 预算紧张：降级到便宜模型（在 LLM 调用时自动切换）
        context.model_override = "gpt-4o-mini"  # 降级
        return True
    else:
        return True
```

**执行记录（Ledger）仍然保留**：每次 function call 执行都自动记录到 Ledger，包括：
- 调用的能力、参数、结果
- LLM 模型、token 用量、成本
- 延迟、是否重试
- Agent 的决策理由（如果 Agent 调用了 `log_decision` 工具）

#### 5.2.6 OpenClaw 通道（MCP Bridge）

与 v2 相同，但现在 MCP Server 暴露的不只是业务能力，还包括 Agent 的状态和控制：

```python
# owlclaw-mcp/server.py
class OwlClawMCPServer:
    def get_tools(self) -> list:
        tools = []
        
        # 1. 业务能力（自动从注册的 capability 生成）
        for cap in self.app.visible_capabilities():
            tools.append(mcp_tool_from_capability(cap))
        
        # 2. Agent 状态查询
        tools.append({"name": "owlclaw_status", 
                       "description": "查看 Agent 当前状态、最近活动、待处理事件"})
        tools.append({"name": "owlclaw_memory", 
                       "description": "搜索 Agent 的历史记忆和经验"})
        
        # 3. Agent 控制
        tools.append({"name": "owlclaw_pause", "description": "暂停 Agent 自主调度"})
        tools.append({"name": "owlclaw_resume", "description": "恢复 Agent 自主调度"})
        tools.append({"name": "owlclaw_trigger", 
                       "description": "立即触发一次 Agent Run"})
        
        # 4. 治理查询
        tools.append({"name": "owlclaw_ledger", "description": "查看执行记录"})
        tools.append({"name": "owlclaw_budget", "description": "查看预算使用情况"})
        
        return tools
```

**通过 OpenClaw 对话控制 OwlClaw 管理的业务应用**：
```
用户: "mionyee 今天做了什么交易决策？"
OpenClaw → owlclaw_ledger → 返回今天的决策记录

用户: "暂停自动交易，我想手动操作一下"
OpenClaw → owlclaw_pause → Agent 暂停自主调度

用户: "帮我看看现在有没有入场机会"
OpenClaw → owlclaw_trigger("检查入场机会") → Agent Run → 返回结果
```

---

### 5.3 业务应用接入策略 — 不只是 Cron

> Cron 只是传统业务应用的一种入口。OwlClaw 要解决的是：**让任何已有的业务触发点都能成为唤醒 Agent 的事件**。

#### 5.3.1 业务应用的六类触发入口

调研了 Dapr Bindings（50+ 集成）、企业集成模式（65种）、以及 2026 年事件驱动 AI Agent 的最新实践后，总结出成熟业务应用的六类触发入口：

| 类型 | 典型场景 | 传统做法 | OwlClaw 接入后 |
|------|---------|---------|---------------|
| **定时任务（Cron）** | mionyee 的48个定时任务 | APScheduler/Celery Beat | 事件触发 Agent Run，Agent 自主决定后续 |
| **Webhook/回调** | 支付通知、Git Push | Flask/FastAPI handler | 事件触发 Agent Run，Agent 理解语义后决策 |
| **消息队列/事件流** | Kafka、RabbitMQ | Consumer 固定逻辑 | 事件触发 Agent Run，Agent 自主决策 |
| **数据库变更** | PostgreSQL NOTIFY、CDC | 触发器 + 固定逻辑 | 事件触发 Agent Run，Agent 判断影响 |
| **API 调用** | REST/GraphQL | 固定 request-response | 事件触发 Agent Run，Agent 智能响应 |
| **文件/存储事件** | S3 事件、FTP | 文件监听 + 固定流程 | 事件触发 Agent Run，Agent 决定处理方式 |

**在 v3 架构下，所有触发入口的处理模式是统一的**：

```
任何触发事件 → 事件触发层 → Agent Run → LLM function calling → 执行
                                ↑
                    Agent 看到的工具列表已经过治理过滤
                    Agent 有身份、记忆、知识来辅助决策
                    Agent 可以自我调度后续动作
```

#### 5.3.2 统一的触发器设计（owlclaw.triggers）

v3 中不再叫 `compat`（兼容层），而是 `triggers`（触发器），因为它们不是"兼容旧系统"的权宜之计，而是 Agent 感知外部世界的正式通道：

```python
from owlclaw import OwlClaw
from owlclaw.triggers import cron, webhook, queue, db_change, api_call

app = OwlClaw("mionyee-trading")

# ── 定时触发 ──
# 不是"把 cron handler 注册为 capability"
# 而是"每60秒产生一个事件，Agent 自己决定要不要做什么"
app.trigger(cron(
    expression="*/60 * * * * *",
    event_name="periodic_check",
    description="周期性检查（盘中每60秒）",
    constraints={"trading_hours_only": True},
))

# ── Webhook 触发 ──
app.trigger(webhook(
    path="/webhook/payment",
    method="POST",
    event_name="payment_callback",
    description="支付回调事件",
))

# ── 消息队列触发 ──
app.trigger(queue(
    source="kafka",
    topic="market-data",
    event_name="market_data_update",
    description="行情数据更新事件",
))

# ── 数据库变更触发 ──
app.trigger(db_change(
    source="postgresql",
    channel="position_changes",
    event_name="position_changed",
    description="持仓变化事件",
))

# ── API 调用触发 ──
app.trigger(api_call(
    path="/api/v1/analysis",
    method="POST",
    event_name="analysis_request",
    description="外部分析请求",
))
```

**注意区别**：触发器只产生事件，不绑定 handler。Agent 收到事件后，自己通过 function calling 从注册的 capability 中选择要执行什么。这与 v2 的 `from_cron(handler=...)` 根本不同 —— v2 仍然是"事件 → 固定 handler"的思路，只是在外面包了一层 Agent；v3 是"事件 → Agent 自主决策 → 选择 capability"。

**Fallback 机制仍然保留**（渐进式迁移）：

```python
# Day 1: 保留原始 handler 作为 fallback
app.trigger(cron(
    expression="*/60 * * * * *",
    event_name="periodic_check",
    fallback=position_entry_monitor_handler,  # Agent 不可用时执行原逻辑
))

# Week 2: 去掉 fallback，完全由 Agent 接管
app.trigger(cron(
    expression="*/60 * * * * *",
    event_name="periodic_check",
))
```

#### 5.3.3 Cron 迁移的具体策略（最常见场景）

**层次一：批量注册触发器 + 保留 fallback（Day 1）**

```python
for task in DEFAULT_TASKS:
    app.trigger(cron(
        expression=task["cron_expression"],
        event_name=task["name"],
        description=task.get("description", task["name"]),
        fallback=task["handler"],
    ))
```

**层次二：AST 扫描器（自动生成注册代码）**

```bash
owlclaw scan --source apscheduler --target ./capabilities/
```

扫描器做什么：
1. AST 分析 —— 解析 Python 源码，找到所有定时任务定义
2. 装饰器识别 —— `@require_trading_time` → capability 的 `constraints`
3. 依赖分析 —— 追踪函数的 import 和调用链
4. 代码生成 —— 生成 capability 注册 + 知识文档骨架

**层次三：AI 辅助迁移工具**

```bash
owlclaw migrate --repo /path/to/mionyee --output ./migration_report.md
```

用 LLM 分析每个 handler 的业务语义，自动生成：
- capability 注册代码
- 知识文档（Markdown）
- state 定义
- constraints
- 迁移报告（绿色/黄色/红色分级）

#### 5.3.4 迁移路径

```
Day 1:  触发器 + fallback → 零改动接入，原逻辑兜底
        ↓
Week 1: owlclaw scan → 自动生成 capability + 知识文档骨架
        ↓
Week 2: 逐步关闭 fallback，让 Agent 接管
        ↓
Month 1: owlclaw migrate → AI 优化知识文档和 capability 定义
        ↓
Steady: Agent 完全自主，触发器仅作为事件源
```

---

### 5.4 开源与商业化策略

#### 5.4.1 许可证：MIT（核心）+ 商业许可（企业功能）

参考 Langfuse 的模式（21,648 GitHub stars）：

| 层 | 许可证 | 内容 |
|----|--------|------|
| **owlclaw**（核心包） | MIT | Agent 运行时、能力注册、治理、触发器 |
| **owlclaw-enterprise** | 商业许可 | RBAC、多租户、审计日志、SSO |
| **OwlClaw Cloud** | SaaS | 托管引擎 + 控制台 + 企业支持 |

#### 5.4.2 开源策略的关键原则

1. **核心能力永远开源** —— Agent 运行时、治理、触发器、MCP 通道
2. **企业功能商业化** —— RBAC、多租户、审计、SSO
3. **托管服务是主要收入** —— OwlClaw Cloud
4. **示例和文档是增长引擎** —— mionyee 接入 OwlClaw 的完整示例

---

## 六、MVP 范围定义

### 6.1 MVP 目标

**用 mionyee 的3个典型任务验证 OwlClaw 的 Agent 自驱动模型**：
1. `position_entry_monitor`（高频盘中任务）
2. `morning_decision`（定时盘前任务）
3. `knowledge_feedback`（盘后知识任务）

**验证标准**：
- Agent 能通过 function calling 自主选择执行哪个 capability
- Agent 能通过 `schedule_once` 工具自我调度下次检查
- Heartbeat 在无事时不调用 LLM（零成本验证）
- 每次执行都有治理记录（Ledger）
- 知识文档能有效引导 Agent 的决策质量

### 6.2 MVP 模块清单

| 模块 | 优先级 | 说明 |
|------|--------|------|
| `owlclaw.agent.runtime` | P0 | Agent 运行时（身份加载、记忆、function calling） |
| `owlclaw.agent.heartbeat` | P0 | Heartbeat 机制（无事不调 LLM） |
| `owlclaw.agent.tools` | P0 | 内建工具（schedule_once、remember、recall、query_state） |
| `owlclaw.capabilities.skills` | P0 | Skills 挂载（Agent Skills 规范，从应用目录加载 SKILL.md） |
| `owlclaw.capabilities.registry` | P0 | 能力注册（@handler、@state 装饰器） |
| `owlclaw.governance.visibility` | P0 | 能力可见性过滤（约束/预算/熔断/限流） |
| `owlclaw.governance.ledger` | P0 | 执行记录 |
| `owlclaw.governance.router` | P0 | task_type → 模型路由 |
| `owlclaw.triggers.cron` | P0 | Cron 触发器 |
| `owlclaw.integrations.hatchet` | P0 | Hatchet 直接集成（MIT，持久执行 + cron + 调度） |
| `owlclaw.integrations.llm` | P0 | litellm 集成 |
| `owlclaw.triggers.webhook` | P1 | Webhook 触发器 |
| `owlclaw.triggers.queue` | P1 | 消息队列触发器 |
| `owlclaw.integrations.langfuse` | P1 | Langfuse tracing |
| `owlclaw-mcp` | P1 | MCP Server（OpenClaw 通道，只读查询为主） |
| `owlclaw.cli.scan` | P1 | AST 扫描器（自动生成 SKILL.md 骨架） |
| `owlclaw.cli.migrate` | P2 | AI 辅助迁移工具 |

### 6.3 MVP 不做的

| 不做 | 理由 |
|------|------|
| 多 Agent 协作 | MVP 只需要单 Agent |
| RBAC / 多租户 | 企业版 |
| Web UI / 控制台 | 用 Langfuse + Temporal UI |
| 沙箱 / Docker 隔离 | 业务应用自己管执行环境 |
| 对话入口 | 交给 OpenClaw（MCP 通道 P1） |

### 6.4 技术栈

| 层 | 选型 | 理由 |
|----|------|------|
| 主语言 | Python ≥ 3.10 | 目标用户生态 |
| 持久执行 | **Hatchet**（MIT，1亿+任务/天） | 直接集成，共用 PostgreSQL |
| Skills 格式 | Agent Skills 规范（SKILL.md） | Anthropic 开源标准 |
| LLM 客户端 | litellm | 统一 100+ 模型 |
| 数据库 | SQLAlchemy + PostgreSQL | Ledger + Memory 持久化 |
| 追踪 | Langfuse + OpenTelemetry | 开源标准 |
| MCP | mcp Python SDK | OpenClaw 通道 |
| 配置 | YAML + Pydantic | 类型安全 |
| 包管理 | pyproject.toml + uv | 现代 Python |
| 许可证 | MIT（OwlClaw 核心） | 对接入方最友好 |

---

## 七、从 mionyee-agent 继续 vs OwlClaw 重新开始

### 7.1 结论：在 OwlClaw 上重新开始

1. **目标不同**：mionyee-agent 对标 OpenClaw（对话式），OwlClaw 面向业务应用
2. **语言不同**：TypeScript vs Python
3. **架构不同**：run loop + tools + skills vs Agent Runtime + Capabilities + Governance
4. **包袱不同**：5个🔴差距 vs 从零开始做对

### 7.2 mionyee-agent 的归宿

不废弃。设计模式（治理钩子、工具策略、事件生命周期）已记录在 `DEEP_ANALYSIS_AND_DISCUSSION.md` 中，OwlClaw 以 Python 重新实现。

---

## 八、风险评估与红军审视

### 8.1 OwlClaw 的真实风险

1. **AI 决策质量** —— Agent 判断"现在该做什么"需要足够好的 Skills 文档和上下文管理。如果 AI 判断错误，比 cron 更差。
   - **缓解**：MVP 保留 cron fallback，逐步过渡。决策质量对比测试（见 8.4）。

2. **接入成本** —— 即使有触发器和扫描工具，迁移仍然是大量工作。
   - **缓解**：fallback 机制 + AST 扫描 + AI 辅助迁移。MVP 只迁移 3 个任务。

3. **市场定位验证** —— "让成熟应用接入 Agent 能力"是否是真实需求？
   - **缓解**：先服务好 mionyee，开源后看社区反馈。examples 必须包含非交易场景。

4. **安全风险** —— Agent 执行业务操作（如建仓），Prompt Injection 可能导致危险行为。
   - **缓解**：见 8.5 安全模型。

5. **Agent 错误恢复** —— Agent 做了错误决策、进入死循环、记忆被污染。
   - **缓解**：见 8.6 错误恢复策略。

### 8.2 红军视角：对 v3 架构的自我批判

写完上面的架构后，我站在红军（对手/批评者）的角度来审视：

#### 批判 1：Agent 自驱动 ≠ Agent 做得好

**红军说**：你把 OODA 循环换成了 function calling，本质上只是把"框架替 Agent 做决策"变成了"让 LLM 自己做决策"。但 LLM 的 function calling 质量高度依赖 prompt engineering。如果知识文档写得不好，或者 system prompt 太长导致 LLM 迷失，Agent 的决策质量可能还不如 v2 的结构化 OODA 循环。

**回应**：
- 这是真实风险。v2 的 OODA 循环虽然死板，但至少步骤明确、可预测。v3 的 function calling 更灵活，但也更不可控。
- **缓解措施**：
  1. 知识文档是核心资产，需要像写代码一样维护和测试
  2. MVP 阶段对比测试：同一场景下 v3 Agent 决策 vs v2 OODA 决策 vs 原始 cron，量化决策质量
  3. 保留 fallback 机制，Agent 决策质量不达标时退化为原逻辑
  4. 治理层的可见性过滤本身就是一种"结构化约束" —— Agent 不是完全自由的，它只能从过滤后的工具列表中选择

#### 批判 2：Heartbeat 的"零成本"是理想化的

**红军说**：你说非交易日 Heartbeat 检查到"没有待处理事件"就跳过，LLM 调用为零。但 `_collect_pending()` 本身需要查询状态、检查调度、扫描事件，这些都有 I/O 成本。而且，如果业务应用的状态查询本身就很重（比如查数据库），Heartbeat 的"零 LLM 成本"并不意味着"零成本"。

**回应**：
- 说得对。"零成本"应该更准确地说是"零 LLM 调用成本"。I/O 成本确实存在。
- **缓解措施**：
  1. `_collect_pending()` 应该只做轻量检查（内存中的标志位、最近事件队列），不做重查询
  2. 状态查询应该有缓存层，不是每次 Heartbeat 都查数据库
  3. Heartbeat 间隔可配置，非交易日可以设为更长（如 2 小时）

#### 批判 3：知识文档 = 维护负担

**红军说**：你从 OpenClaw 学了 Skills 的概念，给每个 capability 附带知识文档。但 OpenClaw 的 Skills 是社区维护的通用技能（如"如何使用 Git"），而 OwlClaw 的知识文档是业务特定的（如"什么时候该检查入场机会"）。这意味着：
1. 每个业务应用都要自己写知识文档，这是额外的工作量
2. 知识文档和业务逻辑可能不同步（代码改了但文档没更新）
3. 没有社区可以帮你维护这些文档

**回应**：
- 这是一个真实的痛点。知识文档的维护成本不能忽视。
- **缓解措施**：
  1. `owlclaw migrate` 工具可以从代码注释和函数签名自动生成知识文档骨架
  2. 知识文档应该有版本控制，和代码放在一起（不是分开维护）
  3. 可以加一个"知识文档健康检查"：对比 capability 的参数签名和知识文档的描述，发现不一致时告警
  4. 长期来看，可以用 LLM 自动从执行历史中更新知识文档（Agent 的 Reflect 阶段可以产出知识更新建议）

#### 批判 4：Hatchet 的部署比 Restate 重

**红军说**：你选了 Hatchet 而不是 Restate，但 Hatchet 需要 Docker Compose（Server + PostgreSQL + 可选 RabbitMQ），比 Restate 的单二进制重。对于"已有成熟应用想快速接入"的用户，部署门槛是否太高？

**回应**：
- 部署确实比 Restate 重，但可接受。
- **理由**：
  1. OwlClaw 本身需要 PostgreSQL（Ledger + Memory），Hatchet 共用同一实例，不额外增加 DB
  2. Hatchet 支持 `SERVER_MSGQUEUE_KIND=postgres`，可以不用 RabbitMQ，进一步简化
  3. Hatchet Lite 镜像可用于开发和低量场景
  4. MIT 许可证的长期价值远大于部署的短期不便
  5. 对于真正的生产用户，Docker Compose 不是障碍

#### 批判 5：与 OpenClaw 的 MCP 通道可能是鸡肋

**红军说**：你设想用户通过 OpenClaw 对话来控制 OwlClaw 管理的业务应用。但：
1. 真正的业务用户（交易员、运维）不会通过对话来管理关键业务系统
2. 对话的延迟和不确定性不适合需要快速响应的场景
3. MCP 通道增加了架构复杂度，但使用频率可能很低

**回应**：
- 部分同意。MCP 通道不是核心功能，而是一个"锦上添花"的通道。
- **调整**：
  1. MCP 通道保持 P1 优先级，不影响核心开发
  2. MCP 的主要价值不是"对话控制业务"，而是"让 OpenClaw 用户能查询 OwlClaw 的状态和记录" —— 这是一个只读的、低频的使用场景，更合理
  3. 真正的业务控制（暂停/恢复/强制执行）应该通过 CLI 或 API，不依赖 MCP

#### 批判 6：mionyee 作为唯一验证场景的局限性

**红军说**：整个架构都是围绕 mionyee（股票交易系统）设计的。你的 capability 示例是交易相关的，知识文档是交易相关的，触发器场景是交易相关的。如果 OwlClaw 真的要做通用的"业务应用 Agent 底座"，你需要证明它在非交易场景下也能工作。

**回应**：
- 完全同意。这是开源前必须解决的问题。
- **缓解措施**：
  1. examples 目录必须包含至少 2 个非交易场景：
     - 一个简单的（如：定时任务替代 —— 把一个 cron 驱动的数据清理脚本接入 OwlClaw）
     - 一个中等复杂的（如：webhook 驱动的工单处理 —— 接收 Zendesk webhook，Agent 决定分配给谁）
  2. 架构文档中的示例代码应该同时展示交易和非交易场景

### 8.3 红军审视后的架构调整

| 批判 | 调整 |
|------|------|
| Agent 决策质量不可控 | MVP 必须包含决策质量对比测试（见 8.4） |
| Heartbeat "零成本"理想化 | `_collect_pending()` 只做轻量内存检查，状态查询有缓存 |
| 知识文档维护负担 | 采用 Agent Skills 规范 + `owlclaw scan` 自动生成 SKILL.md 骨架 |
| Hatchet 部署比 Restate 重 | 共用 PostgreSQL + Hatchet Lite 开发模式 + MIT 长期价值 > 短期不便 |
| MCP 通道可能鸡肋 | MCP 定位为"只读查询通道"，业务控制走 CLI/API |
| mionyee 场景局限 | examples 必须包含 2+ 个非交易场景 |

### 8.4 Agent 测试和评估策略（之前遗漏）

Agent 的决策质量不可验证，就没有企业敢用。MVP 必须包含：

**评估指标**：
| 指标 | 定义 | 目标 |
|------|------|------|
| 决策准确率 | Agent 决策 vs 历史最优决策的一致性 | ≥ 80% |
| Fallback 触发率 | Agent 无法决策，退化为原逻辑的比例 | ≤ 20% |
| 响应延迟 | 从事件触发到 Agent 完成决策的时间 | P95 < 10s |
| LLM 成本 | 每次 Agent Run 的 LLM 调用成本 | < ¥0.5/run |
| 无效调度率 | Agent 自我调度后发现无事可做的比例 | ≤ 30% |

**测试方法**：
1. **历史回放测试** —— 用 mionyee 的历史交易数据，回放过去 30 天的事件，对比 Agent 决策 vs 实际 cron 决策
2. **Shadow Mode** —— 生产环境中 Agent 和 cron 同时运行，Agent 的决策只记录不执行，对比两者的决策差异
3. **A/B 测试** —— Shadow Mode 验证通过后，逐步让 Agent 接管部分任务，对比实际效果

### 8.5 安全模型（之前遗漏）

Agent 执行业务操作（如建仓），安全是关键：

**1. Prompt Injection 防护**：
- Agent 的 system prompt 包含 Skills 知识文档，外部输入（webhook payload、API 请求体）不应直接注入 prompt
- **措施**：外部输入经过 sanitization 后作为 `user` 角色消息传入，不混入 `system` prompt
- **措施**：高风险 capability（如 execute_entry）需要二次确认（Agent 调用后，治理层要求人工审批）

**2. 能力执行的权限边界**：
- 每个 capability 的 `constraints` 定义了硬性边界（如 `max_daily_calls: 50`、`max_amount: 50000`）
- 这些约束在治理层的可见性过滤中强制执行，Agent 无法绕过

**3. 敏感数据保护**：
- Agent 的记忆（MEMORY.md）和 Ledger 中可能包含敏感业务数据
- **措施**：记忆和 Ledger 存储在 PostgreSQL 中，遵循应用的数据安全策略
- **措施**：MCP 通道暴露的数据应经过脱敏处理

### 8.6 错误恢复策略（之前遗漏）

**1. 错误决策回滚**：
- OwlClaw 不做业务层回滚（这是业务应用的职责）
- OwlClaw 提供：完整的决策记录（Ledger）+ Agent 的决策理由（log_decision）+ 能力的执行结果
- 业务应用根据这些信息自行决定是否回滚

**2. 死循环检测**：
- 治理层的限流过滤自然防止死循环（`cooldown_seconds` + `max_daily_calls`）
- 额外措施：如果 Agent 连续 N 次 run 都没有执行任何 capability（只做了 schedule_once），触发告警并暂停自我调度

**3. 记忆污染清理**：
- Agent 的 `remember()` 工具写入的记忆带时间戳和上下文标签
- 提供 `owlclaw memory prune` CLI 命令，可以按时间范围或标签清理记忆
- 严重情况下可以重置 MEMORY.md（Agent 会从 Skills 知识文档重新学习）

### 8.7 多实例协调（之前遗漏）

如果业务应用部署多个实例（高可用），Agent 的协调由 Hatchet 保证：
- Hatchet 的任务队列天然支持单消费者模式 —— 同一个任务只会被一个 worker 执行
- Agent 的 Heartbeat 和自我调度通过 Hatchet 的 cron 和 schedule 实现，天然去重
- 多实例场景下，OwlClaw worker 注册到同一个 Hatchet Server，Hatchet 负责任务分发

### 8.8 版本升级和迁移（之前遗漏）

- **Skills 格式升级**：采用 Agent Skills 规范，跟随规范版本演进。OwlClaw 的 `owlclaw:` 扩展字段向后兼容
- **Agent 记忆版本兼容**：记忆条目带 `version` 字段，新版 Agent 可以选择忽略旧版记忆
- **治理规则热更新**：可见性过滤规则从配置文件（YAML）加载，支持 `owlclaw reload` 不重启更新

---

## 九、下一步行动

### Phase 0：仓库初始化
1. 清理 OwlClaw 仓库
2. 建立包结构（owlclaw / owlclaw-mcp）
3. pyproject.toml + MIT LICENSE + README
4. 配置 CI（GitHub Actions: lint + test）

### Phase 1：Agent 核心（MVP）
5. 实现 Skills 挂载（Agent Skills 规范，从应用目录加载 SKILL.md）
6. 实现 Agent 运行时（SOUL.md 身份加载、记忆系统、Skills 知识注入）
7. 实现 function calling 决策循环（基于 litellm）
8. 实现内建工具（schedule_once、remember、recall、query_state）
9. 实现 Heartbeat 机制
10. 实现能力注册（@handler + @state 装饰器）
11. 实现治理层（能力可见性过滤 + Ledger）
12. 实现 Cron 触发器
13. 直接集成 Hatchet（`owlclaw/integrations/hatchet.py`，MIT，共用 PostgreSQL）
14. 用 mionyee 的 3 个任务做端到端验证
15. 决策质量对比测试：v3 Agent vs 原始 cron，量化对比

### Phase 2：扩展 + 可观测
16. 实现 Webhook / Queue 触发器
17. 集成 Langfuse（tracing）
18. 实现 `owlclaw.cli.scan`（AST 扫描器，自动生成 SKILL.md 骨架）
19. 实现 `owlclaw-mcp`（MCP Server，只读查询为主）
20. 编写非交易场景 examples（至少 2 个）

### Phase 3：开源发布
21. PyPI 发布 owlclaw + owlclaw-mcp
22. GitHub 开源（MIT）
23. mionyee 完整接入示例
24. `owlclaw migrate` AI 辅助迁移工具
25. 社区反馈收集
26. 根据社区需求评估是否需要 Temporal 支持

---

## 十、总结

OwlClaw v3 的核心理念可以用两句话概括：

> **不要控制 Agent，赋能 Agent。**
> **不要重造轮子，组合轮子。**

OwlClaw 不是又一个 Agent 框架。它是一个**组合层**，把成熟的开源能力（Hatchet 的持久执行、Agent Skills 的知识规范、litellm 的模型统一、Langfuse 的可观测、OpenClaw 的对话通道）快速组合起来，解决一个没人解决的问题：

**让成熟的业务系统获得 AI 自主能力，而不需要重写。**

OwlClaw 自建的是没人做的：业务应用接入层、治理层、Agent 运行时。
OwlClaw 集成的是已经做好的：持久执行、LLM、可观测、对话、Skills 规范。

---

> **文档版本**: v3.2（Hatchet MIT 替代 Restate + 安全/测试/恢复策略补全）
> **创建时间**: 2026-02-10
> **前置文档**: `DEEP_ANALYSIS_AND_DISCUSSION.md`
> **文档维护**: 本文档应随架构决策变化持续更新。
