# Agent Memory 系统需求文档

## 文档联动

- requirements: `.kiro/specs/agent-memory/requirements.md`
- design: `.kiro/specs/agent-memory/design.md`
- tasks: `.kiro/specs/agent-memory/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`

## 简介

本文档定义 OwlClaw Agent Memory 子系统的独立需求。Memory 是 Agent 从"无状态函数"跃升为"有经验的自主实体"的关键基础设施。

**定位**：Agent Memory 是 `owlclaw.agent.memory` 模块，为 Agent Runtime 和 Agent Tools 提供统一的记忆存储、检索、生命周期管理能力。它是 `remember()` 和 `recall()` 工具的底层实现，也是 Agent Run 短期上下文的管理者。

**与其他 Spec 的关系**：
- `agent-runtime` 的需求 2（短期记忆）和需求 3（长期记忆）定义了"要什么"
- `agent-tools` 的需求 4（remember）和需求 5（recall）定义了"Agent 怎么用"
- **本 Spec 定义"怎么建"** —— 存储架构、向量索引、生命周期管理、性能优化、降级策略

## 术语表

- **Short_Term_Memory (STM)**: 单次 Agent Run 的上下文缓冲区，Run 结束即清理
- **Long_Term_Memory (LTM)**: 跨 Run 持久化的经验库，支持语义检索
- **Memory_Entry**: 一条记忆记录，包含 content、embedding、tags、timestamp、version、security_level
- **Embedding**: 记忆内容的向量表示，用于语义搜索
- **Time_Decay**: 时间衰减因子，越老的记忆相关性得分越低
- **Memory_Compaction**: 当记忆条目过多时，自动合并/归档旧记忆
- **Memory_Snapshot**: Agent Run 启动时预加载的相关长期记忆子集
- **Vector_Backend**: 向量存储后端（pgvector / Qdrant / 内存模式）
- **Security_Classification**: 记忆的安全分类（public / internal / confidential / restricted）

## 需求

### FR-1：短期记忆（STM）管理

**用户故事**：作为 Agent Runtime，我需要在单次 Run 中维护连贯的上下文，使 Agent 的多轮 function calling 不丢失前文信息。

#### 验收标准

1. WHEN Agent Run 启动时，THE System SHALL 创建独立的 STM 实例（隔离不同 Run）
2. THE STM SHALL 自动收集以下信息：
   - 触发事件（trigger type + payload）
   - focus 标签（如果存在）
   - 每轮 function call 的输入和输出
   - LLM 的中间响应
3. THE STM SHALL 维护 token 计数，默认上限 2000 tokens
4. WHEN token 超出限制时，THE System SHALL 执行滑动窗口压缩：
   - 保留触发事件和 focus（固定区）
   - 保留最近 3 轮 function call（滑动区）
   - 中间轮次压缩为摘要（1 句话/轮）
5. THE STM SHALL 以结构化 JSON 形式提供给 prompt 组装器
6. WHEN Agent Run 结束时，THE System SHALL 清理 STM 实例
7. THE STM SHALL 支持 `inject()` 方法，允许 Signal 触发器注入临时指令

### FR-2：长期记忆（LTM）持久化存储

**用户故事**：作为 Agent，我需要将重要的经验和教训持久保存，跨越多次 Run 积累智慧。

#### 验收标准

1. THE System SHALL 将每条记忆存储为 `memory_entries` 表中的一行，字段包括：
   - `id` (UUID, PK)
   - `agent_id` (VARCHAR, FK → agents)
   - `tenant_id` (VARCHAR, 多租户隔离)
   - `content` (TEXT, 最大 2000 字符)
   - `embedding` (VECTOR, 维度由模型决定)
   - `tags` (JSONB, 标签数组)
   - `security_level` (ENUM: public/internal/confidential/restricted, 默认 internal)
   - `version` (INTEGER, 记忆格式版本号)
   - `created_at` (TIMESTAMPTZ)
   - `accessed_at` (TIMESTAMPTZ, 最后被 recall 命中的时间)
   - `access_count` (INTEGER, 被 recall 命中的次数)
   - `archived` (BOOLEAN, 是否已归档)
2. THE System SHALL 在写入时同时生成 embedding 并存入向量列
3. THE System SHALL 使用 Alembic 管理 memory_entries 表的迁移
4. THE System SHALL 通过 `tenant_id` + `agent_id` 确保记忆隔离

### FR-3：向量检索（Semantic Recall）

**用户故事**：作为 Agent，我需要通过语义搜索找到与当前情境最相关的历史经验，而非精确关键词匹配。

#### 验收标准

1. THE System SHALL 支持可插拔的向量后端：
   - **pgvector**（默认，零额外依赖）：利用宿主 PostgreSQL 的 pgvector 扩展
   - **Qdrant**（高性能选项）：独立部署的向量数据库
   - **InMemory**（mock_mode）：内存字典 + 余弦相似度，开发测试用
2. THE recall 实现 SHALL 执行以下流程：
   a. 将 query 文本转换为 embedding
   b. 执行 ANN（Approximate Nearest Neighbor）搜索
   c. 应用时间衰减：`final_score = similarity * decay_factor(age)`
   d. 应用标签过滤（如果指定）
   e. 返回 top-K 结果（默认 5，最大 20）
3. THE System SHALL 支持 HNSW 索引（pgvector）或等效索引（Qdrant）
4. THE System SHALL 在 recall 命中时更新 `accessed_at` 和 `access_count`
5. THE recall 延迟 SHALL < 200ms（P95，1M 条记忆规模）

### FR-4：Embedding 生成

**用户故事**：作为系统，我需要将文本内容转换为高质量的向量表示，以支持语义搜索。

#### 验收标准

1. THE System SHALL 通过 litellm 统一调用 embedding 模型
2. THE System SHALL 支持以下 embedding 模型：
   - `text-embedding-3-small`（默认，1536 维，成本低）
   - `text-embedding-3-large`（3072 维，精度高）
   - 自定义模型（通过 litellm 配置）
3. THE System SHALL 支持批量 embedding 生成（优化 API 调用）
4. THE System SHALL 缓存常用查询的 embedding（LRU Cache，默认 1000 条）
5. WHEN embedding 模型不可用时，THE System SHALL 降级为 TF-IDF 关键词匹配
6. THE System SHALL 在 mock_mode 下使用随机向量（固定种子，可复现）

### FR-5：记忆生命周期管理

**用户故事**：作为系统管理员，我需要管理记忆的增长，防止无限膨胀，同时保留最有价值的经验。

#### 验收标准

1. THE System SHALL 支持以下生命周期策略：
   - **自动归档**：超过 `max_entries`（默认 10000）时，将最旧且访问最少的记忆标记为 archived
   - **自动清理**：超过 `retention_days`（默认 365 天）且 `access_count < 3` 的记忆自动删除
   - **手动清理**：`owlclaw memory prune` CLI 支持按时间/标签/安全级别清理
   - **重置**：`owlclaw memory reset --agent <name>` 清空所有记忆（Agent 从零学习）
2. THE System SHALL 支持记忆合并（Compaction）：
   - 当同一标签下记忆超过阈值时，自动生成合并摘要
   - 摘要由 LLM 生成（可降级为截断拼接）
   - 原始记忆标记为 archived，摘要作为新记忆写入
3. THE System SHALL 记录生命周期事件到 Ledger（归档、删除、合并）

### FR-6：Memory Snapshot（Run 启动预加载）

**用户故事**：作为 Agent Runtime，我需要在 Run 启动时快速获取与当前事件最相关的历史记忆子集，而非加载全部记忆。

#### 验收标准

1. WHEN Agent Run 启动时，THE System SHALL 根据触发事件和 focus 自动生成 Memory Snapshot
2. THE Snapshot SHALL 包含：
   - 与触发事件语义最相关的 top-3 记忆
   - 最近 24 小时内创建的记忆（最多 5 条）
   - 被标记为 "pinned" 的记忆（永远加载）
3. THE Snapshot 总 token 数 SHALL 不超过 500 tokens（默认）
4. THE Snapshot SHALL 注入到 system prompt 的 "Recent Experience" 段落
5. Agent 仍可通过 recall() 工具按需搜索更多记忆

### FR-7：安全分类与脱敏

**用户故事**：作为安全工程师，我需要确保敏感业务数据在记忆系统中得到适当保护。

#### 验收标准

1. THE System SHALL 支持记忆条目的安全分类（security_level）
2. WHEN 记忆的 security_level 为 confidential 或 restricted 时：
   - MCP 通道查询 SHALL 返回脱敏内容（掩码处理）
   - Langfuse tracing SHALL 不记录原始内容
   - CLI 查询 SHALL 显示 "[CONFIDENTIAL]" 标记
3. THE System SHALL 支持自动安全分类（基于关键词规则 + 正则匹配）
4. THE System SHALL 与 security spec 的 DataMasker 组件集成

### FR-8：降级与容错

**用户故事**：作为系统管理员，我需要记忆系统在部分组件不可用时仍能基本运行。

#### 验收标准

1. WHEN 向量数据库不可用时，THE System SHALL 降级为：
   - remember() → 仅写入 PostgreSQL（无 embedding）
   - recall() → 全文搜索（PostgreSQL `ts_vector`）+ 时间排序
2. WHEN embedding 模型不可用时，THE System SHALL 降级为：
   - remember() → 写入内容 + TF-IDF 向量
   - recall() → TF-IDF 相似度匹配
3. WHEN PostgreSQL 不可用时，THE System SHALL：
   - remember() → 写入本地文件（MEMORY.md 兼容格式）
   - recall() → 返回空列表 + 警告日志
4. THE System SHALL 记录所有降级事件到日志和 Ledger

### FR-9：mock_mode 支持

**用户故事**：作为开发者，我需要在无外部依赖的环境下开发和测试记忆相关功能。

#### 验收标准

1. WHEN `mock_mode=True` 时，THE System SHALL 使用 InMemory 向量后端
2. THE InMemory 后端 SHALL 支持完整的 remember/recall 流程
3. THE InMemory 后端 SHALL 使用固定种子随机向量（测试可复现）
4. THE InMemory 后端 SHALL 在进程退出时丢失数据（内存模式）
5. THE System SHALL 可选支持 SQLite 持久化（`mock_mode=True, persist=True`）

## 非功能性需求

### 性能

| 指标 | 目标 | 条件 |
|------|------|------|
| remember() 延迟 | P95 < 100ms | 含 embedding 生成（异步写入） |
| recall() 延迟 | P95 < 200ms | 1M 条记忆，pgvector HNSW |
| Snapshot 生成 | P95 < 300ms | 含向量搜索 + 组装 |
| embedding 缓存命中率 | > 60% | 稳态运行 |

### 可靠性

- 记忆写入成功率 > 99.9%（含降级）
- 记忆数据不丢失（PostgreSQL 持久化保证）
- 支持向量后端的无缝切换（pgvector ↔ Qdrant）

### 存储

- 单条记忆 ≈ 2KB（content）+ 6KB（embedding 1536d float32）≈ 8KB
- 10000 条记忆 ≈ 80MB（可接受）
- 支持归档和清理策略控制存储增长

## 依赖

- **owlclaw.integrations.llm** — embedding 生成（litellm）
- **owlclaw.db** — PostgreSQL 访问、Alembic 迁移
- **pgvector** — PostgreSQL 向量扩展（可选，推荐）
- **qdrant-client** — Qdrant 向量数据库客户端（可选）
- **owlclaw.governance.ledger** — 生命周期事件记录
- **owlclaw.security.data_masker** — 敏感数据脱敏

## 约束

- 记忆表必须在 OwlClaw 自己的数据库中（owlclaw_db），不侵入宿主应用数据库
- 所有记忆操作必须带 `tenant_id`（从 Day 1 支持多租户）
- embedding 维度在初始化后不可变更（需要重建索引）
- 向量后端的切换需要数据迁移（提供迁移工具）
- memory_entries 表的 DDL 必须通过 Alembic 管理

## 验收测试场景

### 场景 1：完整的 remember → recall 流程

```
GIVEN Agent "mionyee-trading" 运行在 pgvector 后端
WHEN Agent 调用 remember("急跌后反弹信号2小时内有效", tags=["trading", "lesson"])
THEN memory_entries 表新增一行，embedding 非空
AND recall("市场暴跌后的反弹规律") 返回该条记忆
AND 相关性分数 > 0.7
```

### 场景 2：时间衰减排序

```
GIVEN 存在两条语义相似的记忆：A（30天前）、B（1天前）
WHEN Agent 调用 recall("相关查询")
THEN B 排在 A 前面（时间衰减使 B 的最终得分更高）
```

### 场景 3：Memory Snapshot 预加载

```
GIVEN Agent 有 1000 条记忆
WHEN Agent Run 启动，触发事件为 "cron: hourly_check"
THEN Snapshot 包含 ≤ 8 条记忆（3 语义相关 + 5 最近）
AND Snapshot 总 token ≤ 500
AND Snapshot 出现在 system prompt 的 "Recent Experience" 段落
```

### 场景 4：降级到全文搜索

```
GIVEN pgvector 扩展不可用
WHEN Agent 调用 remember("some content")
THEN 内容成功写入 memory_entries（embedding 列为 NULL）
AND recall("content") 使用 PostgreSQL ts_vector 全文搜索返回结果
AND 日志记录降级警告
```

### 场景 5：mock_mode 开发体验

```
GIVEN app = OwlClaw("test", mock_mode=True)
WHEN Agent 调用 remember("test memory")
AND Agent 调用 recall("test")
THEN 返回 "test memory"
AND 无需 PostgreSQL/pgvector/embedding API
```

### 场景 6：记忆生命周期管理

```
GIVEN Agent 有 12000 条记忆（超过默认 10000 上限）
WHEN 生命周期管理任务运行
THEN 最旧且 access_count 最低的 2000+ 条记忆被标记为 archived
AND Ledger 记录归档事件
AND recall() 不返回 archived 记忆
```

## 参考

- OwlClaw 架构文档 `docs/ARCHITECTURE_ANALYSIS.md` §5.2.1（Agent = 身份 + 记忆 + 知识 + 工具 + 自我调度）
- agent-runtime spec 需求 2（短期记忆）和需求 3（长期记忆）
- agent-tools spec 需求 4（remember）和需求 5（recall）
- OpenClaw 的 memory-tool.ts 实现
- Letta (MemGPT) 的分层记忆架构
- pgvector 文档（PostgreSQL 向量扩展）
