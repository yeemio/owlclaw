# OwlClaw 定位：Business System Intelligence

> **版本**: v1.0.0 (2026-02-25)
> **定位**: OwlClaw 的产品定位、差异化价值和生态关系的唯一真源

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

## 三、生态位关系

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

## 四、共享标准

OwlClaw 不发明新格式，复用已有的开放标准：

| 标准 | 来源 | OwlClaw 的使用方式 |
|------|------|------------------|
| **Agent Skills 规范** | agentskills.io（Anthropic 发起） | SKILL.md 格式，OwlClaw 的 `owlclaw:` 字段是兼容扩展 |
| **MCP 协议** | Anthropic 开源 | OwlClaw MCP Server 暴露业务能力为通用 Agent 协议接口 |
| **OpenTelemetry** | CNCF 标准 | 分布式追踪标准 |

---

## 五、核心价值排序

基于红军审视和市场分析，OwlClaw 的核心价值按优先级排序：

1. **业务接入层**（核心壁垒）：scan → migrate → SKILL.md → Declarative Binding，让已有系统零代码接入 AI 能力
2. **治理层**（企业门槛）：可见性过滤 + Ledger 审计 + 预算控制 + 熔断限流，满足企业合规需求
3. **Skills 知识体系**（差异化）：SKILL.md 让业务开发者用自然语言描述业务规则，Agent 自动理解
4. **持久执行**（集成能力）：通过 Hatchet（MIT）实现，崩溃恢复 + 调度 + cron
5. **编排框架标准接入**（生态杠杆）：LangChain/LangGraph/CrewAI 的 chain/workflow 一行代码注册为 capability

---

## 六、一句话定位

> **LangChain 给了 Agent 手和脚（编排能力），OwlClaw 给了 Agent 大脑和心跳（自驱能力）。OwlClaw 让已有的业务系统获得 AI 自主能力，无需重写一行业务代码。**

---

## 七、增长飞轮

```
业务开发者写 SKILL.md（描述已有接口）
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

**维护者**: yeemio
**下次审核**: 2026-03-15
