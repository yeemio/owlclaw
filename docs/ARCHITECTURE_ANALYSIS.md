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
4. **最终决策**：MVP 选择 **Hatchet（MIT）**。理由：MIT 零风险 + Cron 一等公民 + 生产验证（1亿+任务/天）+ 复用宿主 PG、database 级隔离。详见决策5

### 2.4 市场生态关系分析

#### 2.4.1 两个维度看 AI Agent 生态

AI Agent 生态不是简单的上下分层，而是由两个正交的能力维度构成：

```
                        编排能力（怎么做）
                        LangChain · LangGraph · CrewAI · AutoGen
                        ↓ 调用 LLM · 编排工具链 · 管理对话流 · RAG 检索
                        ↓
    ┌───────────────────┼───────────────────────────────────────┐
    │                   │                                       │
    │   只有编排         │   编排 + 自驱 = 完整的自主 Agent        │
    │   (等人来问)       │   (自己决定什么时候做什么)               │
    │                   │                                       │
    │   LangChain 单独   │   LangChain + OwlClaw                │
    │                   │                                       │
    ├───────────────────┼───────────────────────────────────────┤
    │                   │                                       │
    │   什么都没有       │   只有自驱                              │
    │                   │   (有心跳但没手脚)                      │
    │                   │                                       │
    │                   │   OwlClaw 单独（用 litellm 做基础调用） │
    │                   │                                       │
    └───────────────────┼───────────────────────────────────────┘
                        ↑
                        ↑ 自主触发 · 治理边界 · 持久执行 · 业务接入 · 知识体系
                        自驱能力（什么时候做、该不该做、做了之后怎么办）
                        OwlClaw
```

**编排能力**（LangChain 系列解决的问题）：
- 怎么调用 LLM
- 怎么检索文档（RAG）
- 怎么编排工具链
- 怎么管理多步骤流程（LangGraph 状态机）

**自驱能力**（OwlClaw 解决的问题）：
- Agent 什么时候该运行（Cron/Webhook/Heartbeat 自主触发）
- Agent 的边界是什么（治理层：可见性过滤、预算、限流）
- Agent 崩溃了怎么办（Hatchet 持久执行）
- Agent 怎么理解业务上下文（Skills 知识体系）
- Agent 的决策怎么追溯（Ledger 执行记录）

**这两个维度不是竞争关系，是同一个 Agent 的两半。**

#### 2.4.2 生态位互补：LangChain 给手脚，OwlClaw 给大脑和心跳

| 维度 | LangChain / LangGraph | OwlClaw | 组合效果 |
|------|----------------------|---------|---------|
| 触发方式 | 用户请求触发 | 自主触发（Cron/Webhook/Heartbeat） | Agent 既能响应请求，也能自主行动 |
| 运行模式 | 请求-响应 | 持续运行、自主决策 | Agent 是一个长期存活的自主实体 |
| 生命周期 | 一次调用 | 长期存活（有身份、有记忆） | Agent 能积累经验、持续优化 |
| 编排能力 | 强（Chain/Graph/RAG/Tool） | 不重造（集成 litellm 或 LangChain） | 复用已有编排投资 |
| 治理 | 弱（LangSmith 闭源） | 强（可见性过滤/Ledger/预算/限流） | 生产级安全边界 |
| 持久执行 | 弱（LangGraph 检查点） | 强（Hatchet，1亿+任务/天） | 崩溃自动恢复 |
| 业务接入 | 无（假设从零开始） | 核心（@handler/@state 注册已有函数） | 已有系统零改造接入 |
| 知识体系 | RAG（检索增强生成） | Skills（Agent Skills 规范 + 渐进式加载） | 结构化业务知识 + 非结构化文档检索 |

**典型场景**：

用户用 LangChain 做了一个 RAG chain，能回答业务问题。但它只能等人来问。

接上 OwlClaw 后：
- Agent **自己决定**什么时候该主动去查（Heartbeat + Cron 触发）
- Agent **自己判断**查出的结果是否需要通知相关人（function calling 决策）
- Agent **被约束**一天最多查 50 次、每次成本不超过 ¥0.5（治理层）
- Agent **崩溃后自动恢复**，不丢失执行进度（Hatchet 持久执行）
- Agent **记住**上次查过什么、结论是什么（记忆系统）
- 所有决策**可追溯**（Ledger 记录）

**LangChain 的 chain 成为 OwlClaw 的 capability handler，OwlClaw 的 Agent 通过 function calling 决定什么时候调用它。**

#### 2.4.3 标准接入：OwlClaw 对编排框架的集成策略

OwlClaw 不与编排框架对立，而是提供**标准接入**，让用户已有的编排投资直接升级为自主 Agent：

| 编排框架 | 接入方式 | 示例 |
|---------|---------|------|
| **LangChain chain** | 注册为 capability handler | `@app.handler` 包装 `chain.ainvoke()` |
| **LangGraph 工作流** | 注册为 capability handler | `@app.handler` 包装 `graph.ainvoke()` |
| **CrewAI crew** | 注册为 capability handler | `@app.handler` 包装 `crew.kickoff()` |
| **OpenAI Agent SDK** | 作为 LLM 调用后端 | OwlClaw Agent 运行时可选用 OpenAI Agent SDK |
| **任意 Python 函数** | 直接注册 | `@app.handler` 注册已有业务函数 |

```python
# 示例：LangChain chain 作为 OwlClaw capability
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA

# 用户已有的 LangChain RAG chain
rag_chain = RetrievalQA.from_chain_type(
    llm=ChatOpenAI(), retriever=vectorstore.as_retriever()
)

# 一行代码注册为 OwlClaw capability
@app.handler(name="query_knowledge_base", knowledge="skills/knowledge-query/SKILL.md")
async def query_kb(question: str) -> str:
    return await rag_chain.ainvoke(question)

# 现在 OwlClaw 的 Agent 可以自主决定什么时候调用这个 RAG chain
# 不再需要等人来问
```

#### 2.4.4 真正的竞品：谁也在做"自驱能力"

OwlClaw 的竞品不是编排框架（LangChain），而是那些也在解决"自驱能力"的产品：

| 竞品 | 定位 | 自驱能力 | 治理 | 业务接入 | 许可证 | 与 OwlClaw 的差异 |
|------|------|---------|------|---------|--------|-----------------|
| **Restate AI Loops** | 持久执行 + AI Agent | 持久执行强，无自主调度 | 无 | 无 | **BSL** | OwlClaw 有治理 + Skills + 自主调度 + MIT |
| **MuleSoft Agent Fabric** | 企业 Agent 治理 | Agent 发现/注册 | 强 | 强（Salesforce 生态） | **闭源** | OwlClaw 是 MIT 开源、轻量 SDK |
| **Microsoft Foundry** | 云托管 Agent 基础设施 | 托管部署 | 强 | Azure 生态 | **闭源** | OwlClaw 云无关、可自托管 |
| **Solace Agent Mesh** | 事件驱动 Agent 编排 | 事件触发 | 中 | 企业集成 | **商业** | OwlClaw 是 SDK 而非中间件 |
| **Letta (MemGPT)** | 有状态 Agent（记忆核心） | 有状态，无自主调度 | 无 | 无 | MIT | OwlClaw 有治理 + 业务接入 + 持久执行 |

**结论**：

1. **没有一个开源产品同时提供**：自主调度 + 治理 + 业务接入 + Skills 知识体系 + 持久执行 + 编排框架标准接入。这是 OwlClaw 的差异化空间
2. **最接近的是 Restate**：持久执行做得最好，但缺治理、缺业务知识注入、缺自主调度，且 BSL 许可证限制 Cloud 商业化
3. **企业级竞品（MuleSoft、Microsoft、Solace）都是闭源商业产品**：OwlClaw 作为 MIT 开源方案，填补了开源社区的空白
4. **Letta 在记忆层面最强**：OwlClaw 的记忆系统可参考其分层架构，但 OwlClaw 的核心价值在自驱 + 治理 + 业务接入

#### 2.4.5 OwlClaw 的定位总结

```
┌─────────────────────────────────────────────────────────────────┐
│                    一个完整的自主 Agent                           │
│                                                                  │
│  ┌──────────────────────┐    ┌──────────────────────────────┐   │
│  │  编排能力（手和脚）    │    │  自驱能力（大脑和心跳）        │   │
│  │                      │    │                              │   │
│  │  LangChain / LangGraph│    │  ★ OwlClaw                  │   │
│  │  CrewAI / AutoGen     │    │                              │   │
│  │  OpenAI Agent SDK     │    │  • 自主触发（Cron/Webhook/   │   │
│  │                      │    │    Heartbeat）               │   │
│  │  • LLM 调用          │◄──►│  • 治理（可见性/Ledger/预算） │   │
│  │  • RAG 检索          │    │  • 持久执行（Hatchet）        │   │
│  │  • 工具编排          │    │  • 业务接入（@handler/@state）│   │
│  │  • 多步骤流程        │    │  • Skills 知识体系           │   │
│  │                      │    │  • 身份 + 记忆               │   │
│  └──────────────────────┘    └──────────────────────────────┘   │
│         ↑ 标准接入                                               │
│         ↑ OwlClaw 提供编排框架的标准集成接口                       │
└─────────────────────────────────────────────────────────────────┘
```

**一句话定位**：

> **LangChain 给了 Agent 手和脚（编排能力），OwlClaw 给了 Agent 大脑和心跳（自驱能力）。两者组合，才是一个完整的生产级自主 Agent。OwlClaw 提供编排框架的标准接入，让用户已有的编排投资直接升级。**

### 2.5 关键市场洞察

1. **编排 vs 自驱是两个正交维度**：当前 AI Agent 生态几乎全部聚焦在编排能力（怎么做），自驱能力（什么时候做、该不该做）是被忽视的维度。OwlClaw 填补的是这个空白

2. **Brownfield 是真实需求**：企业不会为了用 AI 重写系统。它们需要的是在已有系统上"接入"AI 自主能力。OwlClaw 的 @handler/@state 注册模式和编排框架标准接入，让已有投资（业务代码 + LangChain 编排）直接升级

3. **治理是企业采用的门槛**：Gartner 预测 40% 的 AI Agent 项目会因成本失控和风险管控不足而失败。OwlClaw 的治理层（可见性过滤、Ledger、预算、限流）直接解决这个问题

4. **MIT 开源的战略价值**：在自驱能力这个维度，Restate 是 BSL，MuleSoft/Microsoft/Solace 是闭源商业产品。OwlClaw 作为 MIT 开源方案，是社区唯一的选择

5. **生态位互补创造网络效应**：OwlClaw 不与 LangChain 竞争，而是让 LangChain 用户的已有投资增值。LangChain 生态越大，OwlClaw 的潜在用户越多

### 2.6 红军审视（Red Team Analysis）

> 以下是对 OwlClaw 定位和架构策略的**对抗性审视**。目的不是否定方向，而是提前暴露盲区、假设风险和潜在致命伤，以便在早期做出防御性设计。

#### 攻击面 1：LangGraph 正在侵蚀"自驱能力"维度

**威胁等级**：🔴 高

**事实**：
- LangGraph 已具备 PostgreSQL 持久化检查点（`PostgresSaver`），支持崩溃恢复
- LangGraph Platform 提供 1-click 部署、水平扩展、有状态 Agent 记忆
- LangGraph 的 Cron 调度能力正在发展（通过 LangGraph Cloud）
- LangSmith 提供可观测性（虽然闭源，但用户可能不在乎）

**我们说"LangGraph 持久执行弱"——这个判断正在过时。** LangGraph 的检查点机制虽然不如 Hatchet 的 1 亿+任务/天级别，但对 80% 的用户场景已经够用。如果 LangGraph 继续补齐调度和治理能力，OwlClaw 的"自驱能力"差异化空间会被压缩。

**防御措施**：
1. OwlClaw 的核心壁垒不应仅仅是"持久执行"（这是 Hatchet 的能力，不是我们的），而应是**业务接入层 + 治理层 + Skills 知识体系**的组合——这是 LangGraph 的架构基因里没有的
2. 持续跟踪 LangGraph Platform 的路线图，尤其是治理和调度方面的进展
3. 在文档和定位中，降低对"持久执行"的强调，提升对"业务接入"和"治理"的强调

#### 攻击面 2：Restate 正在快速补齐 AI Agent 能力

**威胁等级**：🟡 中高

**事实**：
- Restate 2025 年底推出了 Restate Cloud（托管服务）
- Restate 与 Vercel AI SDK、OpenAI Agents SDK 的官方集成已发布
- Restate 的 Serverless 原生设计（推送模式，无需 worker 池）在部署简洁性上优于 Hatchet
- Restate 的 BSL 许可证虽然限制 Cloud 商业化，但不影响自托管用户

**我们说"Restate 缺治理、缺业务知识注入"——但 Restate 可能不需要自己做这些。** 如果 Restate 与 LangChain 生态深度集成（它已经在做），用户可以用 LangChain 做编排 + Restate 做持久执行 + 自己写治理逻辑。这个组合可能比"学习一个新的 OwlClaw 框架"更有吸引力。

**防御措施**：
1. OwlClaw 的治理层必须做到**开箱即用**，而不是"理论上可以做"——用户不会为了治理能力学一个新框架，除非它真的零配置就能用
2. Skills 知识体系是 Restate 没有也不会做的差异化——必须做到极致
3. 关注 Restate 的许可证变化（BSL → MIT 的可能性）

#### 攻击面 3："Brownfield"定位可能是一个陷阱

**威胁等级**：🟡 中

**事实**：
- 86% 的企业需要升级技术栈才能部署 AI Agent（Arion Research 2025）
- 42% 的企业需要接入 8+ 数据源
- 遗留系统的 API 通常为人类工作流设计，不适合 Agent 自动访问
- 遗留系统有大量未文档化的定制和最小测试覆盖

**"让已有系统获得 AI 自主能力"听起来很美，但实际接入的摩擦力可能远超预期。** `@handler` 注册一个函数很简单，但让 Agent 真正理解一个复杂业务系统的上下文、边界条件、异常处理——这不是一个装饰器能解决的。Skills 知识文档（SKILL.md）是正确的方向，但编写高质量的 SKILL.md 本身就是一个巨大的工程。

**防御措施**：
1. MVP 阶段不要试图解决所有 Brownfield 问题——先聚焦在"已有 Python 业务函数 + 已有 LangChain 编排"这个最小切入点
2. `owlclaw.cli.scan`（AST 扫描器自动生成 SKILL.md 骨架）的优先级应该提高——降低 SKILL.md 的编写门槛是关键
3. 提供 Brownfield 接入的最佳实践文档和渐进式接入指南

#### 攻击面 4：OpenAI/Anthropic 可能直接做 Agent 基础设施

**威胁等级**：🔴 高（长期）

**事实**：
- OpenAI 已发布 Agents SDK，包含 Handoffs、Guardrails、Tracing
- OpenAI 的 Responses API 正在替代 Assistants API，内置工具调用、代码执行
- Anthropic 发起了 Agent Skills 规范和 MCP 协议
- 模型厂商有最强的 function calling 能力和最大的开发者基数

**如果 OpenAI 在 Agents SDK 中加入持久执行、调度和治理，OwlClaw 的整个定位都会被颠覆。** 模型厂商做基础设施的优势是：它们控制着 function calling 的实现层，可以做到最深度的优化。

**防御措施**：
1. **模型无关是生命线**——OwlClaw 通过 litellm 支持 100+ 模型，这是对抗模型厂商锁定的核心武器
2. **业务接入层是模型厂商不会做的**——OpenAI 不会帮你把已有的 Java 业务系统接入 Agent，这是 OwlClaw 的安全区
3. **治理层的企业级需求（合规、审计、预算）是模型厂商不擅长的**——它们的商业模式是卖 token，不是帮企业省 token

#### 攻击面 5：95% 的 AI Agent 项目失败——OwlClaw 的用户可能根本不存在

**威胁等级**：🟡 中

**事实**：
- MIT 研究：近 95% 的企业 Agentic AI 试点从未进入生产
- 主要原因：脆弱性、缺乏治理、扩展性差、供应商锁定
- 开源 AI 基础设施创业公司（如 Wing Cloud）已有关闭案例——社区热爱不等于可持续收入

**OwlClaw 声称解决的问题（治理、持久执行、业务接入）确实是 AI Agent 失败的核心原因。但问题是：企业可能还没走到需要这些能力的阶段。** 大多数企业还在"AI Agent 是什么"的阶段，还没到"我的 Agent 需要治理"的阶段。市场可能还没准备好。

**防御措施**：
1. **不要等市场成熟再出发**——先用 mionyee 自己的场景验证，积累真实的生产经验
2. **MVP 必须能在 30 分钟内跑起来**——如果用户不能快速看到价值，他们不会等
3. **先做"能用"，再做"好用"**——治理层可以从简单的预算限制开始，不需要一步到位做完整的 RBAC

#### 攻击面 6："生态位互补"可能是一厢情愿

**威胁等级**：🟡 中

**事实**：
- LangChain 的 Python 下载量已超过 OpenAI SDK，生态在快速扩张
- LangChain 正在构建自己的 Platform（LangGraph Platform + LangSmith），向全栈演进
- LangChain 有企业连接器（SAP、Salesforce、ServiceNow），正在进入 Brownfield 领域

**我们假设 LangChain 会停留在"编排"层，但 LangChain 的战略是成为全栈 Agent 平台。** 如果 LangChain 认为 OwlClaw 解决的问题有价值，它可能直接做——而不是等着和 OwlClaw "互补"。LangChain 有更大的开发者基数、更多的融资、更强的品牌。

**防御措施**：
1. **速度是唯一的壁垒**——在 LangChain 补齐这些能力之前，OwlClaw 必须在"自驱 + 治理 + 业务接入"这个组合上建立先发优势和用户口碑
2. **不要把 LangChain 当作唯一的生态伙伴**——同时支持 CrewAI、OpenAI Agents SDK、甚至裸 function calling，降低对单一生态的依赖
3. **考虑成为 LangChain 的插件/扩展**——如果 LangChain 生态足够大，作为其插件可能比独立框架更容易获得用户

#### 攻击面 7：Hatchet 依赖是单点风险

**威胁等级**：🟡 中

**事实**：
- OwlClaw 的持久执行完全依赖 Hatchet（MIT）
- Hatchet 是一个相对小众的项目，社区规模远小于 Temporal
- 如果 Hatchet 停止维护或改变许可证，OwlClaw 的持久执行能力将受到严重影响
- Restate 的 Serverless 原生设计在某些场景下比 Hatchet 的 worker 模式更优

**防御措施**：
1. `owlclaw/integrations/hatchet.py` 的隔离设计是正确的——确保持久执行的抽象层足够干净，未来可以替换为 Temporal 或 Restate
2. 关注 Hatchet 的社区健康度和维护频率
3. 在架构文档中明确标注 Hatchet 是"当前选择"而非"唯一选择"

#### 红军审视总结

| 攻击面 | 威胁 | 核心风险 | 关键防御 |
|--------|------|---------|---------|
| LangGraph 补齐自驱 | 🔴 高 | 差异化空间被压缩 | 聚焦业务接入 + 治理 + Skills，而非持久执行 |
| Restate 快速进化 | 🟡 中高 | 更轻量的替代方案 | 治理开箱即用 + Skills 做到极致 |
| Brownfield 摩擦力 | 🟡 中 | 接入比想象的难 | 最小切入点 + AST 扫描器 + 渐进式指南 |
| 模型厂商下场 | 🔴 高（长期） | 整个定位被颠覆 | 模型无关 + 业务接入 + 企业治理 |
| 市场未成熟 | 🟡 中 | 用户还没准备好 | 自己先用 + 30 分钟上手 + 先能用再好用 |
| 互补是一厢情愿 | 🟡 中 | LangChain 自己做 | 速度先发 + 多生态支持 + 考虑插件模式 |
| Hatchet 单点风险 | 🟡 中 | 依赖方出问题 | 隔离层 + 可替换设计 |

#### 红军审视结论

**OwlClaw 的定位方向是正确的，但有三个需要立即行动的调整**：

1. **重新排序核心价值**：从"持久执行 + 治理 + 业务接入"调整为**"业务接入 + 治理 + Skills 知识体系"**。持久执行是集成来的（Hatchet），不是我们的核心壁垒；业务接入层和治理层才是别人不做也做不好的
2. **加速 MVP 交付**：窗口期有限。LangGraph Platform 和 Restate Cloud 都在快速演进。OwlClaw 必须在 2026 年内有可用的生产级 MVP，否则差异化空间会被蚕食
3. **准备 Plan B**：如果"独立框架"的路走不通（用户不愿学新框架），要准备好转型为"LangChain/LangGraph 的治理和业务接入插件"——这个定位虽然小，但更容易存活

### 2.7 产品愿景：Markdown 即 AI 能力

#### 2.7.1 核心洞察：AI 能力的消费方式正在转变

当前 AI Agent 生态有一个巨大的隐含假设——**"你得有 AI 开发团队"**。LangChain 要你写 Python，LangGraph 要你设计状态机，CrewAI 要你编排多 Agent 协作。这些框架再好，面向的都是 AI 开发者。

但现实是：

```
AI 开发者          ■                           （万级，会写 LangChain）
业务开发者         ■■■■■■■■■■■■■■              （百万级，会写业务代码）
业务人员           ■■■■■■■■■■■■■■■■■■■■■■■■■■  （千万级，懂业务但不写代码）
```

**绝大多数企业不可能为了用 AI 去组建 AI 开发团队。** 它们有业务开发团队，有运维团队，有业务人员——这些人最了解自己的业务，但不会写 LangChain。

OwlClaw 的愿景是：**让这些人也能让业务系统获得 AI 自主能力。**

#### 2.7.2 "Markdown 即 AI 能力"范式

这个范式的核心思想来自 OpenClaw 的成功验证：

- OpenClaw 用 **SOUL.md** 让非技术用户定义 Agent 人格 → 182K GitHub stars
- Agent Skills 规范用 **SKILL.md** 让开发者定义 Agent 技能 → 已成为开源标准（agentskills.io）
- GitHub 提出 **Spec-Driven Development**——用 Markdown 写规格，AI 编译成代码
- AgentUse 框架用 **.agentuse Markdown 文件** 定义自主 Agent，无需 SDK

**OwlClaw 把这个范式推到业务领域**：业务开发者用 SKILL.md 描述业务接口，OwlClaw 的 Agent 自动理解并使用。

```
传统路径（需要 AI 团队）：
  业务需求 → 招 AI 团队 → 学 LangChain → 写 RAG → 写 Agent → 调试 → 部署
  时间：3-6 个月 | 成本：50-200 万/年

OwlClaw 路径（只需业务开发者）：
  业务需求 → 写 SKILL.md（描述已有接口）→ 装 OwlClaw → Agent 自动工作
  时间：1-3 天 | 成本：接近零（MIT 开源 + 自有 LLM 成本）
```

#### 2.7.3 具体场景：SKILL.md 如何让业务系统"活"起来

**场景 1：ERP 库存预警**

业务开发者只需写一个 SKILL.md：

```markdown
---
name: inventory-monitor
description: >
  监控库存水平，发现异常时预警。当库存低于安全库存、
  或消耗速度异常加快时使用此技能。
---

## 可用工具
- get_inventory_levels(warehouse_id): 获取指定仓库的库存水平
- get_consumption_rate(product_id, days): 获取产品近 N 天的日均消耗
- get_safety_stock(product_id): 获取产品的安全库存线
- send_alert(recipient, message): 发送预警通知

## 业务规则
- 库存 < 安全库存的 120% 时，提前预警（留出补货时间）
- 日均消耗突然增加 50% 以上，可能是促销或异常，需要确认
- 周末和节假日不发预警（非工作时间）
- 同一产品 24 小时内最多预警一次（避免轰炸）

## 决策指引
- 优先关注高价值产品（单价 > ¥1000）
- 季节性产品（如空调、暖气）在换季前 1 个月加强监控
- 不要对样品和赠品库存做预警
```

业务开发者写这个文档**不需要任何 AI 知识**。他只需要描述：有哪些接口、什么时候该用、业务规则是什么。OwlClaw 的 Agent 拿到这个 SKILL.md 后，通过 function calling 自主决定什么时候查库存、查哪个仓库、是否需要预警。

**场景 2：CRM 客户流失分析**

```markdown
---
name: churn-detection
description: >
  分析客户行为数据，识别可能流失的客户。当需要评估客户健康度、
  或发现客户活跃度下降时使用此技能。
---

## 可用工具
- get_customer_activity(customer_id, days): 获取客户近 N 天的活跃数据
- get_customer_segment(customer_id): 获取客户分层（VIP/普通/试用）
- get_renewal_date(customer_id): 获取客户续约日期
- create_task(owner, description, due_date): 创建跟进任务

## 流失信号
- 登录频率下降 > 60%（对比前 30 天）
- 核心功能使用率下降 > 40%
- 续约日期在 30 天内且未有续约意向
- 最近 7 天有多次客服投诉

## 决策指引
- VIP 客户出现任何一个流失信号就创建跟进任务
- 普通客户出现 2 个以上流失信号才创建任务
- 试用客户不做流失分析（由市场团队负责）
- 跟进任务分配给客户的专属客户经理
```

**场景 3：财务异常检测**

```markdown
---
name: financial-anomaly
description: >
  监控财务数据，发现异常交易和趋势偏差。当需要检查
  收支异常、预算超支、或可疑交易时使用此技能。
---

## 可用工具
- get_daily_transactions(date, category): 获取指定日期和类别的交易
- get_budget_status(department, month): 获取部门月度预算使用情况
- get_historical_average(category, months): 获取类别的历史月均值
- flag_transaction(transaction_id, reason): 标记可疑交易

## 异常规则
- 单笔交易 > 月均值的 5 倍 → 标记为可疑
- 部门月度支出 > 预算的 80% 且月份未过半 → 预警
- 同一供应商单日多笔交易（可能拆单规避审批）→ 标记
- 非工作时间的大额交易 → 标记

## 合规要求
- 所有标记操作必须记录原因
- 不要自动拒绝或撤销任何交易，只标记和通知
- 涉及高管的交易标记后通知审计部门而非直属上级
```

**关键观察**：这三个场景中，业务开发者写的都是**他们已经知道的东西**——业务规则、接口说明、决策逻辑。他们不需要学 AI，不需要学 prompt engineering，不需要理解 function calling。**SKILL.md 就是他们的母语。**

#### 2.7.4 增长飞轮

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│    ┌──────────┐     ┌──────────────┐     ┌───────────────┐         │
│    │ 业务开发者 │────►│ 写 SKILL.md   │────►│ Agent 自动工作 │         │
│    │ 描述业务   │     │ 描述已有接口   │     │ 产生业务价值   │         │
│    └──────────┘     └──────────────┘     └───────┬───────┘         │
│         ▲                                         │                 │
│         │                                         ▼                 │
│    ┌────┴─────────┐                      ┌───────────────┐         │
│    │ 更多企业加入   │◄─────────────────────│ 口碑传播       │         │
│    │ 更多行业覆盖   │                      │ "零代码接 AI"  │         │
│    └────┬─────────┘                      └───────────────┘         │
│         │                                                           │
│         ▼                                                           │
│    ┌──────────────────────────────────────────────────────┐        │
│    │                    OwlHub                             │        │
│    │                                                      │        │
│    │  行业 Skills 模板积累 → 同行业企业直接复用             │        │
│    │  电商 Skills · 金融 Skills · 制造 Skills · SaaS Skills │        │
│    │                                                      │        │
│    │  ┌─────────┐  ┌─────────┐  ┌─────────┐             │        │
│    │  │ 发布     │  │ 发现     │  │ 安装     │             │        │
│    │  │ SKILL.md │→│ 搜索/推荐 │→│ 一键使用  │             │        │
│    │  └─────────┘  └─────────┘  └─────────┘             │        │
│    │                                                      │        │
│    │  网络效应：每多一个 Skill，所有同行业用户受益           │        │
│    └──────────────────────────────────────────────────────┘        │
│         │                                                           │
│         ▼                                                           │
│    ┌──────────────────────────────────────────────────────┐        │
│    │  数据飞轮                                             │        │
│    │                                                      │        │
│    │  Agent 运行数据 → Skills 质量评分 → 推荐优质 Skills    │        │
│    │  Agent 决策记录 → 优化业务规则 → 更新 SKILL.md         │        │
│    └──────────────────────────────────────────────────────┘        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**三层飞轮**：

1. **产品飞轮**：写 SKILL.md → Agent 工作 → 产生价值 → 口碑传播 → 更多用户
2. **生态飞轮**：用户发布 Skills → OwlHub 积累 → 同行业复用 → 接入门槛持续降低
3. **数据飞轮**：Agent 运行数据 → Skills 质量评分 → 推荐优化 → Agent 决策更准

**天花板对比**：

| 维度 | OpenClaw ClawHub | OwlClaw OwlHub |
|------|-----------------|----------------|
| Skills 类型 | 通用技能（Git、代码审查、写作） | 业务技能（库存、财务、CRM、HR...） |
| Skills 数量天花板 | 有限（通用操作就那么多） | **无限**（每个行业、每个业务流程） |
| 用户群体 | 开发者 | 业务开发者 + 业务人员 |
| 商业价值 | 低（通用技能难以差异化收费） | **高**（行业 Skills 有明确商业价值） |
| 网络效应 | 中（通用 Skills 复用率有限） | **强**（同行业 Skills 高度可复用） |

#### 2.7.5 OwlHub：业务 Skills 生态平台

OwlHub 是 OwlClaw 的业务 Skills 注册中心，类似 OpenClaw 的 ClawHub，但面向业务领域。

**注册中心架构模型选择**：

经过对 npm（数据库 Web 服务）、Homebrew（Git 仓库索引）、Terraform Registry（GitHub + 协议）、ClawHub（Convex + 向量搜索）的研究，OwlHub 采用**渐进式架构**：

| 阶段 | 架构 | 说明 |
|------|------|------|
| **Phase 1（MVP）** | **GitHub 仓库索引** | 类似 Homebrew-tap 模式。一个 `owlclaw/owlhub` 仓库，Skills 以目录形式存放，通过 PR 提交和审核。CLI `owlclaw skill install <name>` 直接从 GitHub 拉取。零基础设施成本 |
| **Phase 2（社区）** | **静态站点 + GitHub API** | 在 GitHub 仓库基础上，加一个静态站点（GitHub Pages / Cloudflare Pages）提供浏览、搜索、分类。向量搜索用 OpenAI embeddings + 本地索引。仍然零服务器成本 |
| **Phase 3（规模）** | **数据库 Web 服务** | 当 Skills 数量超过 1000 或需要高级功能（评分、推荐、私有 Skills）时，迁移到数据库后端（PostgreSQL + pgvector）。支持 OwlClaw Cloud 的企业私有 Skills 仓库 |

**Phase 1 MVP 详细设计**：

```
owlclaw/owlhub (GitHub 仓库)
├── registry/
│   ├── index.json                    # Skills 索引（名称、描述、版本、分类）
│   ├── ecommerce/                    # 电商行业
│   │   ├── inventory-monitor/
│   │   │   ├── SKILL.md
│   │   │   └── metadata.json         # 版本、作者、标签、兼容性
│   │   ├── order-anomaly/
│   │   │   ├── SKILL.md
│   │   │   └── metadata.json
│   │   └── ...
│   ├── finance/                      # 金融行业
│   │   ├── financial-anomaly/
│   │   ├── budget-monitor/
│   │   └── ...
│   ├── saas/                         # SaaS 行业
│   │   ├── churn-detection/
│   │   ├── usage-analytics/
│   │   └── ...
│   └── general/                      # 通用（跨行业）
│       ├── data-quality-check/
│       ├── report-generator/
│       └── ...
├── templates/                        # SKILL.md 模板
│   ├── basic.md                      # 基础模板
│   ├── monitoring.md                 # 监控类模板
│   ├── analysis.md                   # 分析类模板
│   └── workflow.md                   # 工作流类模板
├── CONTRIBUTING.md                   # 贡献指南
└── README.md
```

**CLI 集成**：

```bash
# 浏览可用 Skills
owlclaw skill search "inventory"
owlclaw skill search --category ecommerce

# 安装 Skill（从 OwlHub 拉取到项目的 skills/ 目录）
owlclaw skill install ecommerce/inventory-monitor

# 从模板创建新 Skill
owlclaw skill init --template monitoring my-custom-monitor

# 发布 Skill 到 OwlHub（通过 GitHub PR）
owlclaw skill publish my-custom-monitor

# 验证 SKILL.md 格式合规性
owlclaw skill validate skills/my-skill/SKILL.md
```

**metadata.json 格式**：

```json
{
  "name": "inventory-monitor",
  "version": "1.0.0",
  "author": "company-name",
  "category": "ecommerce",
  "tags": ["inventory", "monitoring", "alert", "warehouse"],
  "owlclaw_version": ">=0.1.0",
  "tools_required": [
    "get_inventory_levels",
    "get_consumption_rate",
    "get_safety_stock",
    "send_alert"
  ],
  "tools_schema": {
    "get_inventory_levels": {
      "description": "获取指定仓库的库存水平",
      "parameters": {
        "warehouse_id": {"type": "string", "description": "仓库 ID"}
      },
      "returns": {"type": "object", "description": "库存水平数据"}
    }
  },
  "triggers_recommended": ["cron:0 9 * * 1-5", "heartbeat:30m"],
  "governance_hints": {
    "max_daily_runs": 50,
    "max_cost_per_run": 0.5
  }
}
```

**关键设计决策**：

1. **SKILL.md 遵循 Agent Skills 规范（agentskills.io）**——不发明新格式，复用已有的开源标准。OwlHub 的 metadata.json 是对标准的扩展，不是替代
2. **tools_schema 是可选的**——如果业务开发者只写了 SKILL.md 中的文字描述，Agent 仍然可以工作（通过 function calling 的参数推断）。tools_schema 提供更精确的类型信息，提升 Agent 决策质量
3. **triggers_recommended 和 governance_hints 是建议**——安装 Skill 后，用户可以根据自己的需求调整触发频率和治理参数
4. **GitHub PR 审核流程**——所有公开 Skills 必须经过社区审核（格式合规、无恶意内容、描述清晰），保证生态质量

#### 2.7.6 SKILL.md 模板体系

降低 SKILL.md 编写门槛是引爆的关键。OwlClaw 提供分类模板。

**实现说明**：模板库位于 `owlclaw/templates/skills/`，包含 TemplateRegistry、TemplateRenderer、TemplateValidator、TemplateSearcher。15 个模板（monitoring/analysis/workflow/integration/report 各 3 个）存放于 `owlclaw/templates/skills/templates/`。详见 `docs/templates/user-guide.md` 与 `docs/templates/template-development.md`。

| 模板类型 | 适用场景 | 核心结构 |
|---------|---------|---------|
| **monitoring** | 监控预警类（库存、性能、安全） | 可用工具 + 预警规则 + 阈值 + 通知策略 |
| **analysis** | 数据分析类（销售、客户、财务） | 可用工具 + 分析维度 + 异常定义 + 报告格式 |
| **workflow** | 流程自动化类（审批、通知、同步） | 可用工具 + 流程步骤 + 条件分支 + 异常处理 |
| **integration** | 系统集成类（数据同步、格式转换） | 源系统工具 + 目标系统工具 + 映射规则 |
| **report** | 报告生成类（日报、周报、月报） | 数据源工具 + 报告结构 + 生成频率 + 分发列表 |

**模板示例（monitoring 类）**：

```markdown
---
name: [your-skill-name]
description: >
  [一句话描述：监控什么、什么时候触发、触发后做什么]
---

## 可用工具
- [tool_name](param1, param2): [工具描述]
- [tool_name](param1): [工具描述]

## 监控规则
- [条件 1] → [动作 1]
- [条件 2] → [动作 2]

## 阈值配置
- [指标名]: [正常范围] / [预警阈值] / [严重阈值]

## 通知策略
- 预警级别 → 通知 [角色]，方式 [邮件/消息/...]
- 严重级别 → 通知 [角色]，方式 [电话/紧急消息/...]
- 同一问题 [N] 小时内不重复通知

## 排除条件
- [什么情况下不触发]（如节假日、维护窗口）
```

#### 2.7.7 商业模式演进

| 阶段 | 模式 | 收入来源 |
|------|------|---------|
| **Phase 1：开源增长** | MIT 开源，OwlHub 免费 | 无（积累用户和 Skills 生态） |
| **Phase 2：Cloud 服务** | OwlClaw Cloud（托管部署 + 私有 OwlHub） | 订阅费：按 Agent 数量 / 按 Skill 运行次数 |
| **Phase 3：企业版** | 私有 Skills 仓库 + 高级治理 + SLA | 企业订阅：按租户 / 按部署规模 |
| **Phase 4：生态变现** | 行业 Skills 认证 + 付费 Skills + 咨询 | 平台抽成 + 认证费 + 咨询服务 |

**MIT 许可证的战略价值**：业务系统集成 OwlClaw 后，OwlClaw 的代码成为业务系统的一部分。MIT 许可证意味着：
- 不影响业务系统的许可证（GPL 会"传染"）
- 不需要开源业务系统的代码
- 不需要向 OwlClaw 付费（除非选择 Cloud/Enterprise）
- **这是业务软件公司最能接受的许可证**

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
  focus:                             # Focus 标签（v4.1）
    - inventory_monitor              # 当触发器的 focus 匹配时才加载
    - trading_decision
  risk_level: medium                 # 风险等级：low / medium / high / critical
  requires_confirmation: false       # 是否需要人工二次确认（high/critical 默认 true）
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
4. **数据层归属 OwlClaw** —— 复用宿主 PostgreSQL，组件间 database 级隔离。详见 `docs/DATABASE_ARCHITECTURE.md`
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
| 持久执行 | | ✅ Hatchet（MIT） | 直接集成，独立 database（详见 `DATABASE_ARCHITECTURE.md`） |
| LLM 客户端 | | ✅ litellm | 统一 100+ 模型 |
| LLM 调用 tracing | | ✅ Langfuse | 不重复造轮子 |
| 分布式追踪 | | ✅ OpenTelemetry | 标准协议 |
| 对话通道 | | ✅ MCP（OpenClaw） | 标准协议 |
| 向量存储 | | ✅ 业务应用自己选 | OwlClaw 只定义接口 |
| 编排框架接入 | | ✅ LangChain/LangGraph/CrewAI | 标准 capability handler 接入，详见决策8 |
| Skills 生态（OwlHub） | ✅ | | Skills 注册/发现/分发平台，详见决策10 |
| Skills CLI 工具 | ✅ | | `owlclaw skill` 子命令（init/validate/search/install/publish） |
| SKILL.md 模板库 | ✅ | | 分类模板（monitoring/analysis/workflow/integration/report） |

### 4.7 决策7：接入协议语言无关

**OwlClaw 的目标用户是"成熟业务系统"，而成熟业务系统的技术栈不限于 Python —— Java、.NET、Go、TypeScript 都有可能。因此，接入协议必须语言无关。**

**核心原则**：Python SDK 是接入协议的第一个便利封装，不是唯一的接入方式。

| 层 | 语言绑定 | 说明 |
|----|----------|------|
| **Agent Runtime** | Python（实现语言） | 引擎内部实现，用什么语言写不影响用户 |
| **接入协议** | 语言无关（HTTP/gRPC/MCP） | 业务应用通过协议注册能力、推送状态、接收调用 |
| **Python SDK** | Python | 协议的 Python 封装（`@app.handler()`、`@app.state()` 是语法糖） |
| **未来 SDK** | Java / .NET / Go / TS | 协议的其他语言封装（P3） |

**跨语言接入的两条现有路径**：

1. **MCP 协议** —— MCP 是语言无关的（JSON-RPC over stdio/HTTP）。任何语言的应用只要能发 HTTP 请求，就能通过 OwlClaw MCP Server 与 Agent 交互
2. **Hatchet 多语言 SDK** —— Hatchet 有 Go、TypeScript、Python SDK。业务应用可以用自己的语言注册 Hatchet worker，OwlClaw Agent 通过 Hatchet 调度这些 worker

**对开发的约束**：

- Capability 的注册和调用在内部必须基于协议层（数据结构 + 序列化），Python SDK 的装饰器只是协议的语法糖
- 禁止在协议层泄漏 Python 特有的概念（如 `Callable`、`inspect`、装饰器元数据）—— 协议层只传递 JSON Schema + handler endpoint
- Skills 的 SKILL.md 格式本身就是语言无关的（YAML + Markdown），这是正确的
- 未来设计 HTTP API 时，接口定义应先于 SDK 封装（API-first）

**MVP 阶段不需要实现多语言 SDK**，但架构设计必须保证不把 Python 特有的东西烧进协议层。具体来说：
- `CapabilityRegistry` 内部可以用 Python 的 `Callable`、`inspect`
- 但对外暴露的能力描述（传给 Agent Runtime 的工具列表）必须是纯数据结构（dict/JSON Schema），不依赖 Python 对象

### 4.8 决策8：编排框架生态标准接入

**OwlClaw 与 LangChain 等编排框架是生态位互补关系，不是竞争关系。OwlClaw 必须提供编排框架的标准接入接口。**

**核心原则**：编排框架给 Agent 手和脚（怎么做），OwlClaw 给 Agent 大脑和心跳（什么时候做、该不该做）。两者组合才是完整的自主 Agent。

#### 接入层次

| 层次 | 接入方式 | 说明 | 优先级 |
|------|---------|------|--------|
| **Capability 接入** | 编排框架的 chain/agent/workflow 注册为 OwlClaw 的 capability handler | 最核心的接入方式。用户已有的 LangChain chain、LangGraph 工作流、CrewAI crew 通过 `@app.handler` 注册后，OwlClaw Agent 可自主决定何时调用 | P0（MVP） |
| **LLM 后端接入** | OwlClaw Agent 运行时支持 LangChain 作为 LLM 调用层（除 litellm 外的可选后端） | 让已深度使用 LangChain 的用户复用已有的 model 配置、callback、tracing | P2 |
| **工具生态接入** | 通过 Composio 或 LangChain Tools 扩展 OwlClaw Agent 的工具库 | 让 Agent 能调用 850+ 外部工具（Gmail、Slack、Jira 等） | P2 |

#### Capability 接入示例

```python
# ── LangChain chain 作为 capability ──
from langchain.chains import RetrievalQA

rag_chain = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)

@app.handler(name="query_knowledge_base", knowledge="skills/kb-query/SKILL.md")
async def query_kb(question: str) -> str:
    return await rag_chain.ainvoke(question)

# ── LangGraph 工作流作为 capability ──
from langgraph.graph import StateGraph

approval_graph = StateGraph(ApprovalState)
# ... build graph ...
approval_app = approval_graph.compile()

@app.handler(name="run_approval_workflow", knowledge="skills/approval/SKILL.md")
async def approval(request: dict) -> dict:
    return await approval_app.ainvoke(request)

# ── CrewAI crew 作为 capability ──
from crewai import Crew

research_crew = Crew(agents=[...], tasks=[...])

@app.handler(name="research_topic", knowledge="skills/research/SKILL.md")
async def research(topic: str) -> str:
    return research_crew.kickoff(inputs={"topic": topic})
```

**关键设计约束**：

1. **OwlClaw 不依赖任何编排框架** —— litellm 是默认 LLM 后端，LangChain 是可选的。`pip install owlclaw` 不会拉入 LangChain 依赖
2. **编排框架接入通过 capability handler 实现** —— 这是已有的 @handler 机制，不需要新的抽象层。任何可调用的 Python 函数都能注册为 capability
3. **LangChain LLM 后端是可选扩展** —— 通过 `pip install owlclaw[langchain]` 安装，提供 `LangChainLLMBackend` 适配器
4. **文档和 examples 必须包含编排框架集成示例** —— 至少覆盖 LangChain chain、LangGraph workflow 两个场景

### 4.9 数据库架构

数据库是 OwlClaw 的基石，其完整架构设计见独立文档：**`docs/DATABASE_ARCHITECTURE.md`**（数据库架构唯一真源）。

**核心设计要点**：

- **复用宿主 PostgreSQL** —— OwlClaw 不自行部署 PostgreSQL 实例，在宿主已有的 PostgreSQL 上创建 database，降低接入门槛
- **组件间 database 级隔离** —— owlclaw / hatchet / langfuse 各自独立 database，权限、migration、备份均独立
- **tenant_id 从 Day 1 存在** —— 所有 OwlClaw 表从第一天起包含 `tenant_id`（Self-hosted 默认 `'default'`），为 Cloud 多租户预留
- **各组件独立管理 migration** —— OwlClaw 用 Alembic，Hatchet / Langfuse 用各自内建 migration
- **运维通过 CLI 统一入口** —— `owlclaw db init / migrate / status / backup / check` 等子命令

**部署模式演进**：Self-hosted（单租户）→ OwlClaw Cloud（RLS 多租户）→ Enterprise（Database-per-tenant）

详细内容包括：数据模型与表结构、Schema 迁移策略、`owlclaw db` CLI 设计、连接管理、性能指南、灾备与高可用、Self-hosted 到 Cloud 的迁移路径。请参阅 `docs/DATABASE_ARCHITECTURE.md`。

### 4.10 决策10：Skills 生态与 OwlHub

**OwlClaw 的核心增长引擎不是代码，是 Skills 生态。SKILL.md 是业务开发者接入 AI 能力的零代码入口，OwlHub 是 Skills 的发现和分发平台。**

#### 核心原则

1. **SKILL.md 遵循 Agent Skills 规范（agentskills.io）**——不发明新格式，复用开源标准。OwlHub 的 metadata.json 是扩展，不是替代
2. **渐进式架构**——Phase 1 用 GitHub 仓库（零成本），Phase 2 加静态站点，Phase 3 迁移到数据库后端
3. **CLI 优先**——`owlclaw skill` 子命令是 Skills 生态的主要交互方式，Web 界面是补充
4. **质量优于数量**——通过 PR 审核、格式验证、社区评分保证 Skills 质量

#### CLI 子命令设计

| 命令 | 功能 | 优先级 |
|------|------|--------|
| `owlclaw skill init --template <type> <name>` | 从模板创建新 Skill | P0（MVP） |
| `owlclaw skill validate <path>` | 验证 SKILL.md 格式合规性 | P0（MVP） |
| `owlclaw skill search <query>` | 搜索 OwlHub 中的 Skills | P1 |
| `owlclaw skill install <name>` | 从 OwlHub 安装 Skill 到项目 | P1 |
| `owlclaw skill publish <path>` | 发布 Skill 到 OwlHub（GitHub PR） | P1 |
| `owlclaw skill list` | 列出项目中已安装的 Skills | P0（MVP） |
| `owlclaw skill info <name>` | 查看 Skill 详情（描述、版本、评分） | P1 |

#### 与现有架构的关系

```
owlclaw skill init          owlclaw skill install
       │                           │
       ▼                           ▼
  skills/                    skills/
  └── my-skill/              └── inventory-monitor/   ← 从 OwlHub 安装
      └── SKILL.md               └── SKILL.md
       │                           │
       ▼                           ▼
  @app.handler(              @app.handler(
    knowledge=               knowledge=
    "skills/my-skill"        "skills/inventory-monitor"
  )                          )
       │                           │
       ▼                           ▼
  Agent Runtime: Skills 知识注入 → function calling 决策
```

Skills 生态不改变 OwlClaw 的核心架构——它是在现有的 `@app.handler(knowledge=...)` 机制之上，提供 Skills 的**创建、验证、发现、分发**能力。

#### 关键约束

1. **OwlHub 是可选的**——用户可以完全不用 OwlHub，自己写 SKILL.md 放在项目目录里，OwlClaw 照常工作
2. **`owlclaw skill` CLI 不依赖 OwlHub 服务**——`init`、`validate`、`list` 是纯本地操作；`search`、`install`、`publish` 需要网络但仅依赖 GitHub API（Phase 1）
3. **私有 Skills 不经过 OwlHub**——企业的业务 Skills 包含商业机密，永远不应上传到公开仓库。私有 Skills 就是项目目录里的 SKILL.md 文件
4. **模板是引爆的关键**——`owlclaw skill init --template monitoring my-alert` 必须能在 30 秒内生成一个可用的 SKILL.md 骨架，让业务开发者只需填写业务规则

### 4.11 决策11：Protocol-first（协议优先于语言 SDK）

**OwlClaw 面向所有业务系统，而不是仅面向 Python 业务系统。实现顺序必须遵循 Protocol-first：先协议契约，后语言封装。**

#### 背景

决策7已经明确“接入协议语言无关”，但执行过程中仍然容易滑向 “Python SDK-first”：

- 设计先出现 `@app.handler` / `@app.state` 语义，再补协议映射
- 对外样例主要是 Python，非 Python 接入路径（HTTP/gRPC/MCP）示例不足
- 新模块验收常以 Python 单测为主，缺少协议层契约测试

这会导致“定位是全语言，落地像 Python 专用框架”的认知偏差。

#### 决策内容

1. **协议层是产品面，不是实现细节**：HTTP/gRPC/MCP 的请求/响应 schema、错误码、版本策略是第一公民。
2. **Python SDK 是第一方封装，不是唯一入口**：装饰器 API 必须可映射为协议调用，不可反向定义协议。
3. **新能力按“契约 -> 适配器 -> SDK 语法糖”顺序交付**：禁止跳过契约直接做 Python API。

#### 强制约束（对开发与评审）

1. **契约先行**：任何新入口或能力（trigger/tool/capability 注册）必须先提交协议 schema（JSON Schema 或等价契约）和错误码表，再实现 Python 封装。
2. **契约测试必需**：验收至少包含一类“非 Python SDK 路径”测试（例如 HTTP/MCP 调用或协议层序列化/反序列化测试）。
3. **边界清晰**：协议层禁止泄漏 Python 特有语义（`Callable`、装饰器元数据、`inspect` 结构）；协议只传纯数据和 endpoint 元信息。
4. **文档双轨**：每个核心功能文档必须同时给出 Python SDK 示例 + 协议调用示例（curl/MCP JSON-RPC 至少一种）。

#### 里程碑调整（执行优先级）

1. **P1**：优先收口 `triggers-webhook` / `triggers-api` / `triggers-signal` 的协议化入口与契约测试。
2. **P2**：补齐跨语言示例（至少 TS/Java 中一种）与 SDK 无关的端到端样例。
3. **P3**：在协议稳定后扩展 Java/.NET/Go/TS SDK，避免 SDK 反向锁定协议。

### 4.12 决策12：Declarative Binding（声明式工具绑定）

**SKILL.md 不只是知识文档，也是可执行契约。通过声明式绑定（Binding），Agent 能直接调用存量系统的 API/队列/数据库，无需编写 Python 适配代码。**

#### 背景

OwlClaw 的产品愿景是"Markdown 即 AI 能力"（§2.7），SKILL.md 让业务开发者用自然语言描述业务规则，Agent 通过 function calling 自主决策。但当前的工具链存在一个断裂点：

```
SKILL.md 声明工具 → 需要 @handler Python 代码绑定实际 API → Agent 才能调用
```

这个 `@handler` 步骤要求编写 Python 适配代码，对存量系统（Java/Go/.NET/非 Python 技术栈）构成接入壁垒。红军审视（§2.6 攻击面 3）已指出："Brownfield 接入的摩擦力可能远超预期"。

同时，FastPath 提案（`docs/ZERO_CODE_FASTPATH_DECISION_PROPOSAL.md`）提出了"零代码接入存量系统"的需求，但其解法（HTTP Edge / LLM Proxy 新组件）偏离了 OwlClaw 的 SDK 定位。更自然的解法是：**让 SKILL.md 自身承载工具的接入信息，Agent 运行时根据声明自动完成调用。**

#### 业界参考

| 方案 | 机制 | 优点 | 局限 | OwlClaw 借鉴点 |
|------|------|------|------|---------------|
| **Dapr Bindings** | YAML 声明 binding 类型（HTTP/Kafka/PostgreSQL/...）+ sidecar 代理执行 | 40+ 绑定类型、成熟稳定、输入/输出双向 | 需要 Dapr sidecar（太重）；YAML 配置与业务知识分离 | binding 类型分类（HTTP/Queue/SQL）；credential 通过 secret store 引用 |
| **MCP Tools** | JSON Schema 声明工具签名 + Server 实现调用逻辑 | 标准化工具发现与调用协议；LLM 原生理解 | 工具实现仍需代码；无声明式绑定 | `inputSchema` 格式；工具发现协议 |
| **Terraform Provider** | HCL 声明资源 + Provider 实现 CRUD | 声明式基础设施管理；Provider 生态丰富 | 面向基础设施而非 API 调用 | Provider 注册机制；声明式 + 可扩展的架构 |
| **Anthropic 指导** | "找到最简单的方案，只在需要时增加复杂度" | 避免过度工程化 | — | MVP 先做 HTTP binding，按需扩展 |

**关键设计取舍**：Dapr 把 binding 做成独立的基础设施层（sidecar），OwlClaw 把 binding 嵌入 SKILL.md 的 metadata——**知识与接入合一，一个文件描述"做什么"和"怎么连"**。这是 OwlClaw 相对于 Dapr 的差异化：不需要额外的基础设施组件，SKILL.md 就是全部。

#### 决策内容

1. **SKILL.md 的 `metadata.json` 扩展 `binding` 字段**：每个工具可声明其接入方式（HTTP/Queue/SQL/gRPC），Agent 运行时根据 binding 自动完成调用，无需 `@handler` 代码。
2. **binding 是可选的**：有 binding 的工具走声明式调用；无 binding 的工具走传统 `@handler` 注册。两种模式共存，渐进式迁移。
3. **binding 执行器是可插拔的**：`owlclaw/capabilities/bindings/` 下按类型实现执行器（HTTPBinding、QueueBinding、SQLBinding），新类型通过注册机制扩展。
4. **credential 不写入 SKILL.md**：敏感信息通过环境变量引用（`${VAR_NAME}`），运行时从 `owlclaw.config` 或环境变量解析。参考 Dapr 的 secretKeyRef 模式。

#### Binding Schema 设计

**通用结构**（所有 binding 类型共享）：

```json
{
  "tool_name": {
    "description": "工具描述",
    "parameters": { "...JSON Schema..." },
    "returns": { "...JSON Schema..." },
    "binding": {
      "type": "http | queue | sql | grpc",
      "mode": "active | shadow",
      "timeout_ms": 5000,
      "retry": { "max_attempts": 3, "backoff_ms": 1000 },
      "...type-specific fields..."
    }
  }
}
```

**HTTP Binding**（面向 REST API，最常用）：

```json
{
  "get_inventory_levels": {
    "description": "获取指定仓库的库存水平",
    "parameters": {
      "warehouse_id": { "type": "string", "description": "仓库 ID" }
    },
    "binding": {
      "type": "http",
      "method": "GET",
      "url": "${ERP_BASE_URL}/api/v1/inventory/{warehouse_id}",
      "headers": {
        "Authorization": "Bearer ${ERP_API_TOKEN}",
        "Content-Type": "application/json"
      },
      "response_mapping": {
        "path": "$.data",
        "error_path": "$.error.message",
        "status_codes": { "200": "success", "404": "not_found", "429": "rate_limited" }
      }
    }
  }
}
```

设计要点：
- URL 支持路径参数模板（`{warehouse_id}`），运行时从工具参数中替换
- Headers 支持环境变量引用（`${ERP_API_TOKEN}`）
- `response_mapping` 提取响应中的有效数据，避免将整个 HTTP 响应传给 LLM
- `status_codes` 映射 HTTP 状态码到语义化错误，便于 Agent 理解和重试

**Queue Binding**（面向消息队列，用于异步场景和 shadow 模式）：

```json
{
  "submit_order": {
    "description": "提交订单到处理队列",
    "parameters": {
      "order_id": { "type": "string" },
      "items": { "type": "array" }
    },
    "binding": {
      "type": "queue",
      "provider": "kafka | rabbitmq | redis",
      "mode": "active",
      "connection": "${KAFKA_BROKER_URL}",
      "topic": "orders.submit",
      "format": "json",
      "headers_mapping": {
        "correlation_id": "{order_id}",
        "source": "owlclaw-agent"
      }
    }
  }
}
```

设计要点：
- `provider` 复用 `owlclaw/integrations/queue_adapters/` 已有的适配器（Kafka 已完成）
- `mode: shadow` 时只消费不 ack，用于旁路观察（对应 FastPath 的 Queue Mirror 需求）
- `headers_mapping` 注入追踪信息，便于 Ledger 审计

**SQL Binding**（面向数据库查询，只读场景）：

```json
{
  "get_daily_transactions": {
    "description": "获取指定日期和类别的交易记录",
    "parameters": {
      "date": { "type": "string", "format": "date" },
      "category": { "type": "string" }
    },
    "binding": {
      "type": "sql",
      "connection": "${FINANCE_DB_URL}",
      "query": "SELECT id, amount, description, created_at FROM transactions WHERE date = :date AND category = :category ORDER BY created_at DESC LIMIT 100",
      "read_only": true,
      "parameter_mapping": {
        "date": ":date",
        "category": ":category"
      }
    }
  }
}
```

设计要点：
- **强制参数化查询**：禁止字符串拼接，所有参数通过 `parameter_mapping` 绑定（防 SQL 注入）
- `read_only: true` 为默认值，写操作需要显式声明且受 `risk_level` 约束
- 连接字符串走环境变量，不写入 SKILL.md

#### 执行模式：active vs shadow

| 模式 | 行为 | 用途 |
|------|------|------|
| `active` | 正常调用目标系统，返回真实结果 | 生产运行 |
| `shadow` | 调用目标系统但不产生副作用（HTTP GET 正常执行；POST/PUT/DELETE 只记录不发送；Queue 只消费不 ack；SQL 只读） | 零代码对比验证、接入前评估 |

shadow 模式直接解决了 FastPath 提案的核心需求——"不影响现网主链路，先看到可量化效果"。shadow 执行的结果写入 Ledger，通过 `e2e-validation` 已有的 report_generator 生成对比报告。

#### 与现有架构的集成

```
                    SKILL.md
                    ├── 业务知识（自然语言）    → Agent prompt 注入
                    ├── tools_schema            → function calling 工具列表
                    │   └── binding（可选）      → 声明式调用
                    ├── triggers_recommended    → 触发时机建议
                    ├── governance_hints        → 治理边界
                    ├── focus                   → 按需加载
                    └── risk_level              → 安全等级

                         │
                         ▼
            ┌─── capabilities.skills ───┐
            │  Skills 加载器             │
            │  ├── 有 binding → 注册为   │
            │  │   BindingTool          │
            │  └── 无 binding → 需要    │
            │      @handler 注册        │
            └───────────┬───────────────┘
                        │
                        ▼
            ┌─── capabilities.bindings ─┐
            │  Binding 执行器注册表      │
            │  ├── HTTPBinding          │
            │  ├── QueueBinding         │
            │  ├── SQLBinding           │
            │  └── gRPCBinding（预留）   │
            └───────────┬───────────────┘
                        │
          ┌─────────────┼──────────────┐
          ▼             ▼              ▼
    governance     security       integrations
    ├── visibility  ├── sanitize   ├── queue_adapters/
    │   过滤        │   输入输出   │   (Kafka 已有)
    ├── ledger      ├── risk_level ├── llm/
    │   记录        │   确认流程   │   (litellm)
    └── budget      └── masking    └── hatchet/
        预算控制        数据脱敏       (持久执行)
```

**关键集成点**：

1. **capabilities.skills**：Skills 加载器检测 `tools_schema` 中是否有 `binding` 字段，有则自动注册为 BindingTool（无需 `@handler`），无则保持现有行为
2. **governance.visibility**：BindingTool 与 @handler 注册的工具一样受可见性过滤、预算限制、限流控制
3. **governance.ledger**：所有 binding 调用记录到 Ledger（请求参数、响应摘要、耗时、状态码），shadow 模式额外标记 `mode=shadow`
4. **security**：binding 的输入参数经过 InputSanitizer；SQL binding 强制参数化查询；`risk_level: high/critical` 的 binding 工具需要人工确认
5. **integrations.queue_adapters**：Queue binding 复用已有的 Kafka/RabbitMQ 适配器，不重复实现
6. **config**：环境变量引用（`${VAR_NAME}`）通过 `owlclaw.config` 统一解析，支持 `.env` 文件和系统环境变量

#### 强制约束

1. **credential 隔离**：binding 中的敏感信息（API Token、数据库密码）必须通过 `${ENV_VAR}` 引用，禁止明文写入 SKILL.md 或 metadata.json
2. **SQL 注入防护**：SQL binding 强制使用参数化查询（`:param` 占位符），运行时禁止字符串拼接。无 `parameter_mapping` 的 SQL binding 拒绝执行
3. **shadow 模式安全**：shadow 模式下，写操作（HTTP POST/PUT/DELETE、Queue produce with ack、SQL write）只记录意图到 Ledger，不实际执行
4. **binding 验证**：`owlclaw skill validate` 命令扩展 binding schema 验证（URL 格式、必填字段、环境变量引用格式）
5. **超时与重试**：所有 binding 调用必须有超时（默认 5000ms）和重试策略（默认 3 次指数退避），防止 Agent 因外部系统故障卡死

#### 里程碑

1. **P0（MVP）**：HTTP Binding 执行器 + shadow 模式 + Ledger 集成 + `owlclaw skill validate` binding 验证
2. **P1**：Queue Binding 执行器（复用 queue_adapters）+ SQL Binding 执行器（只读）+ 对比报告生成
3. **P2**：gRPC Binding + SQL 写操作（需 risk_level 约束）+ OwlHub binding 模板
4. **P3**：自定义 Binding 类型注册机制 + 社区贡献的 Binding 扩展

#### 与 FastPath 提案的关系

本决策取代 `docs/ZERO_CODE_FASTPATH_DECISION_PROPOSAL.md` 中的 HTTP Edge 和 LLM Proxy 方案。FastPath 提案的核心需求通过以下方式满足：

| FastPath 需求 | Declarative Binding 实现 |
|--------------|------------------------|
| Queue Mirror（shadow consumer） | Queue Binding + `mode: shadow` |
| Cron Shell（调度壳替换） | `triggers_recommended` + HTTP Binding 指向已有任务 API |
| HTTP Edge（网关旁路） | HTTP Binding + `mode: shadow` |
| LLM Proxy（透明代理） | 不在 binding 范围——属于 `integrations-llm` 的 proxy 模式（按需评估） |
| 标准对比报告 | shadow 模式数据 → Ledger → `e2e-validation` report_generator |
| mionyee 基准样板 | mionyee 的 SKILL.md + HTTP Binding 作为 reference implementation |

FastPath 提案状态更新为 `Resolved — 纳入决策 4.12 Declarative Binding`。

#### OpenClaw 对标分析补充（2026-02-24）

OpenClaw（22.3 万星）验证了"SKILL.md 即能力"的模式在市场上的成功。其核心机制是 Agent 通过 bash/curl 执行 SKILL.md 中描述的命令（隐式绑定），与 OwlClaw 的声明式绑定（显式绑定）形成互补。对标分析揭示了以下需要补充的设计点：

**1. SKILL.md 书写门槛**

OpenClaw 的最小 SKILL.md 只需 `name` + `description`，5 分钟上手。OwlClaw 的 SKILL.md 要求理解 `owlclaw:` 扩展字段（task_type、constraints、trigger、cron 表达式），门槛过高。

决策：所有 `owlclaw:` 扩展字段均为可选，只有 `name` + `description` + body 是必需的。`owlclaw skill init` 默认生成最小版本。

**2. Skill Prerequisites（加载前提条件）**

OpenClaw 的 `metadata.openclaw.requires`（env/bins/config/os）在加载时过滤不可用的 skill。OwlClaw 需要同样的机制——如果 binding 依赖的环境变量不存在，应在加载时就跳过，而不是等到 Agent 调用时才失败。

决策：在 `owlclaw:` 字段中增加 `prerequisites`（env/bins/config/python_packages/os），加载时检查。

**3. 简化 Tools 声明**

binding 的 `tools_schema` 使用完整 JSON Schema，对非技术用户门槛过高。

决策：支持简化 YAML 语法（`param: string`），运行时自动展开为 JSON Schema。

**4. 三种 Skill 执行模式共存**

| 模式 | 适用场景 | 执行方式 |
|------|---------|---------|
| **Declarative Binding** | 存量系统接入（HTTP/Queue/SQL） | 运行时根据 binding 声明自动调用 |
| **@handler** | 复杂业务逻辑 | Python 代码实现 |
| **Shell 指令** | 简单工具调用（curl/CLI） | Agent 读 body 中的命令示例，通过内建 shell 工具执行 |

三种模式共存，渐进式迁移：从 shell 指令（最简单）→ binding（零代码但结构化）→ @handler（最灵活）。

**5. Session Skill Snapshot + Token Budget**

- 会话开始时快照可用 Skills 列表，会话内保持稳定
- 每个 Skill 注入 prompt 的 token 开销透明化，纳入 governance budget 控制

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
│  │  PostgreSQL（owlclaw 库 + hatchet 库，详见 DATABASE_ARCHITECTURE.md）│   │
│  └──────────────────────────┬───────────────────────────────────────┘   │
│                             │                                            │
│  ┌──────────────────────────▼───────────────────────────────────────┐   │
│  │  集成层 (Integration Layer)                                       │   │
│  │  - LLM: litellm (统一 100+ 模型)                                  │   │
│  │  - Tracing: Langfuse / OpenTelemetry                              │   │
│  │  - 持久执行: Hatchet（MIT，独立 database，同一 PostgreSQL 实例）  │   │
│  │  - 存储: SQLAlchemy + PostgreSQL（owlclaw 库：ledger、memory）   │   │
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

v3 中不再叫 `compat`（兼容层），而是 `triggers`（触发器），因为它们不是"兼容旧系统"的权宜之计，而是 Agent 感知外部世界的正式通道。

**API 双模式（v4.1 决策）**：OwlClaw 提供两种等价的触发器注册方式，开发者按场景选择：

```python
from owlclaw import OwlClaw

app = OwlClaw("mionyee-trading")

# ── 方式一：装饰器风格（推荐：需要 fallback 的渐进式迁移场景） ──
# 被装饰的函数自动作为 fallback handler
@app.cron(
    expression="0 * * * *",
    event_name="hourly_check",
    focus="inventory_monitor",
    migration_weight=0.5,        # 50% Agent / 50% fallback
)
async def hourly_check():
    """Fallback: 固定逻辑"""
    await legacy_hourly_check()

@app.webhook(path="/webhook/payment", method="POST")
async def payment_handler(payload: dict):
    """Fallback: 固定处理"""
    await process_payment(payload)

# ── 方式二：函数调用风格（推荐：纯 Agent 决策场景，无 fallback） ──
# 触发器只产生事件，不绑定任何 handler
app.trigger(cron(
    expression="*/60 * * * * *",
    event_name="periodic_check",
    description="周期性检查（盘中每60秒）",
    constraints={"trading_hours_only": True},
))

app.trigger(webhook(
    path="/webhook/order",
    method="POST",
    event_name="order_callback",
))

app.trigger(db_change(
    source="postgresql",
    channel="position_changes",
    event_name="position_changed",
))

app.trigger(api_call(
    path="/api/v1/analysis",
    method="POST",
    event_name="analysis_request",
))
```

**两种方式的本质相同**：都是注册触发器 → 产生事件 → Agent 自主决策。装饰器风格是函数调用风格的语法糖，额外提供了 fallback handler 绑定，适用于从传统 cron/handler 渐进式迁移的场景。

**核心原则不变**：触发器只产生事件，不替 Agent 做决策。Agent 收到事件后，自己通过 function calling 从注册的 capability 中选择要执行什么。

**事件聚合**（v4.1 新增，适用于所有触发器类型）：

高频事件源（数据库变更、消息队列、webhook 重试）可通过聚合参数减少不必要的 Agent Run：

```python
app.trigger(db_change(
    channel="order_updates",
    event_name="order_changed",
    debounce_seconds=5,    # 窗口期内只触发一次（取最后一条）
    batch_size=10,         # 累积 10 条后统一触发
))
```

**Focus 机制**（v4.1 新增，适用于所有触发器类型）：

通过 `focus` 参数引导 Agent 只加载与当前任务相关的 Skills，减少 token 消耗、提升决策质量：

```python
@app.cron(expression="0 * * * *", focus="inventory_monitor")
# → Agent 只看到 SKILL.md frontmatter 中 focus 包含 "inventory_monitor" 的 Skills
```

**Fallback 与渐进式迁移**：

```python
# Day 1: migration_weight=0.0 → 100% fallback（零风险接入）
@app.cron(expression="0 * * * *", migration_weight=0.0)
async def task(): await legacy_logic()

# Week 1: migration_weight=0.1 → 10% Agent（小流量验证）
# Week 2: migration_weight=0.5 → 50% Agent（A/B 对比）
# Month 1: migration_weight=1.0 → 100% Agent（完全接管）
# Steady: 去掉 fallback，使用函数调用风格
app.trigger(cron(expression="0 * * * *", event_name="task"))
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
| 持久执行 | **Hatchet**（MIT，1亿+任务/天） | 直接集成，独立 database（详见 `DATABASE_ARCHITECTURE.md`） |
| Skills 格式 | Agent Skills 规范（SKILL.md） | Anthropic 开源标准 |
| LLM 客户端 | litellm | 统一 100+ 模型 |
| 数据库 | SQLAlchemy + PostgreSQL + Alembic | 复用宿主 PG + database 级隔离 + Alembic。详见 `DATABASE_ARCHITECTURE.md` |
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
  1. 复用宿主 PostgreSQL：OwlClaw 和 Hatchet 各自使用独立 database（详见 `DATABASE_ARCHITECTURE.md`），不额外增加 PostgreSQL 服务器
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
| Hatchet 部署比 Restate 重 | 复用宿主 PG + database 级隔离（详见 `DATABASE_ARCHITECTURE.md`）+ Hatchet Lite + MIT 长期价值 > 短期不便 |
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

### 8.9 Spec 洞察反哺架构（v4.1 新增）

在详细设计各模块 Spec 的过程中，涌现出以下 6 个跨模块通用洞察，已回写为架构级决策：

#### 8.9.1 渐进式迁移权重（migration_weight）

**来源**：triggers-cron Spec

传统 cron 任务迁移到 Agent 自主决策时，不应是"全有或全无"的切换。`migration_weight`（0.0–1.0）定义了 Agent 接管的比例：
- `0.0` → 100% fallback（Day 1 零风险接入）
- `0.1` → 10% Agent（小流量验证决策质量）
- `0.5` → 50%（A/B 对比 Agent vs fallback）
- `1.0` → 100% Agent（完全接管，可去掉 fallback）

**架构影响**：此机制写入触发器 API（§5.3.2），适用于所有触发器类型，不限于 cron。

#### 8.9.2 Focus 选择性加载机制

**来源**：triggers-cron Spec

Agent 每次 Run 不必加载所有 Skills 的完整指令。触发器通过 `focus` 参数声明本次事件的关注领域，Agent 运行时只加载 `SKILL.md` frontmatter 中 `owlclaw.focus` 包含匹配标签的 Skills。

**架构影响**：
- `SKILL.md` 的 `owlclaw:` 扩展字段增加 `focus: [tag1, tag2]`（§4.3）
- Agent 运行时的 Skills 加载器需根据 focus 过滤
- 减少 token 消耗、提升决策质量，尤其在 Skills 数量多（>10）的场景下效果显著

#### 8.9.3 零依赖开发模式（mock_mode）

**来源**：examples Spec

为降低 OwlClaw 上手门槛，所有 examples 和开发时可通过 `mock_mode=True` 运行，无需真实 LLM、Hatchet、PostgreSQL：

```python
app = OwlClaw("demo", mock_mode=True)
# → LLM: 返回预设响应 / echo
# → Hatchet: 内存任务队列
# → DB: SQLite 内存模式
# → Langfuse: 本地日志
```

**架构影响**：OwlClaw 核心需要抽象出依赖注入点，mock 实现作为内建组件提供，而非外部 monkeypatch。这影响 `owlclaw.runtime` 和 `owlclaw.integrations` 的接口设计。

#### 8.9.4 指令注入（Instruction Injection）

**来源**：triggers-signal Spec

运行中的 Agent 可通过 Signal 触发器接收临时人工指令，而不需要停止/重新部署：

```bash
owlclaw signal instruct --agent mionyee-trading \
  --message "今天大盘暴跌，所有买入操作暂停，只允许减仓"
```

**架构影响**：
- Agent 运行时需要一个 `pending_instructions` 队列
- 指令在下一次 Run 的 system prompt 中注入（作为临时 context）
- 执行后自动清除（或标记为已执行）
- 这是 Agent 自主性的必要补充 —— 在极端情况下人类需要快速介入

#### 8.9.5 能力风险等级（risk_level + requires_confirmation）

**来源**：security Spec

每个 SKILL.md 的 `owlclaw:` 扩展字段增加风险声明：

| risk_level | 行为 | 示例 |
|-----------|------|------|
| `low` | 直接执行 | 查询行情、读取持仓 |
| `medium` | 执行 + 记录到 Ledger | 修改止损价、更新策略参数 |
| `high` | 需要人工确认后执行 | 建仓、平仓 |
| `critical` | 需要双重确认（人工 + 审批流） | 大额交易、策略全局调整 |

**架构影响**：
- 治理层的可见性过滤需要读取 `risk_level`
- 高风险能力执行前发送通知（Webhook/消息推送）等待确认
- 这弥补了原架构中安全模型的粗粒度描述（§8.5），使安全策略可通过声明式配置而非硬编码实现

#### 8.9.6 事件聚合模式（Event Aggregation）

**来源**：triggers-db-change Spec

高频事件源产生的大量细粒度事件可通过两种策略聚合，避免过度触发 Agent Run：

- **Debounce（防抖）**：窗口期内只取最后一条事件，适合"最终状态"场景
- **Batch（批量）**：累积 N 条后统一发给 Agent，适合"批量处理"场景

**架构影响**：事件聚合不是 db_change 特有的，而是触发器框架的通用能力。所有触发器工厂函数（cron、webhook、queue、db_change、api_call）均可接收 `debounce_seconds` 和 `batch_size` 可选参数（§5.3.2 已更新）。

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
13. 直接集成 Hatchet（`owlclaw/integrations/hatchet.py`，MIT，独立 database）
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

### Langfuse Integration Status (2026-02-24)

- 新增 `owlclaw/integrations/langfuse.py` 作为隔离层，承载配置、采样、trace/span、token 成本、隐私脱敏与上下文传递能力。
- `AgentRuntime` 在每次 run 生命周期中设置并恢复 `TraceContext`，确保 LLM 与工具调用可以关联到同一 trace。
- `llm.acompletion()` 在存在 trace 上下文时自动记录 generation（成功/失败、token、成本、延迟）。
- 工具执行链路（含 built-in）会产出 Langfuse span 更新，且 Langfuse 不可用时保持降级不阻塞业务执行。

---

> **文档版本**: v4.4（v4.3 + §4.12 OpenClaw 对标补充：书写门槛、Prerequisites、简化语法、三种执行模式、Session Snapshot）
> **创建时间**: 2026-02-10
> **最后更新**: 2026-02-24
> **前置文档**: `DEEP_ANALYSIS_AND_DISCUSSION.md`
> **文档维护**: 本文档应随架构决策变化持续更新。

## LangChain Integration Update (2026-02-24)

- 新增 `owlclaw/integrations/langchain/` 适配层：config/schema/errors/trace/adapter/retry/privacy/version。
- `OwlClaw` 提供 `register_langchain_runnable` 与 `@app.handler(..., runnable=...)` 注册入口。
- 执行链路统一纳入治理校验、审计记录、隐私脱敏与流式输出转换。
- 依赖策略保持可选安装：`pip install "owlclaw[langchain]"`。
