# Agent Memory 系统设计文档

## 概述

Agent Memory 子系统采用**双层架构**（STM + LTM），通过可插拔的向量后端和多级降级策略，为 Agent 提供从"无状态"到"有经验"的核心基础设施。

## 架构概览

```
┌─────────────────────────────────────────────────────────┐
│                    Agent Runtime                         │
│                                                         │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────┐ │
│  │  STM Manager │    │ LTM Manager  │    │  Snapshot  │ │
│  │  (per-Run)   │    │  (singleton) │    │  Builder   │ │
│  └──────┬───────┘    └──────┬───────┘    └─────┬──────┘ │
│         │                   │                   │        │
│  ┌──────┴───────────────────┴───────────────────┴──────┐ │
│  │              MemoryService (Façade)                  │ │
│  └──────────────────────┬──────────────────────────────┘ │
│                         │                                │
│  ┌──────────────────────┴──────────────────────────────┐ │
│  │              MemoryStore (Abstract)                  │ │
│  │  ┌──────────┐ ┌──────────┐ ┌────────────────────┐  │ │
│  │  │ PgVector │ │  Qdrant  │ │ InMemory (mock)    │  │ │
│  │  │  Store   │ │  Store   │ │ Store              │  │ │
│  │  └──────────┘ └──────────┘ └────────────────────┘  │ │
│  └─────────────────────────────────────────────────────┘ │
│                         │                                │
│  ┌──────────────────────┴──────────────────────────────┐ │
│  │            EmbeddingProvider (Abstract)              │ │
│  │  ┌──────────┐ ┌──────────┐ ┌────────────────────┐  │ │
│  │  │ LiteLLM  │ │  TF-IDF  │ │ Random (mock)      │  │ │
│  │  │ Embedder │ │ Fallback │ │ Embedder           │  │ │
│  │  └──────────┘ └──────────┘ └────────────────────┘  │ │
│  └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. MemoryEntry（数据模型）

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4
from typing import Optional

class SecurityLevel(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"

@dataclass
class MemoryEntry:
    id: UUID = field(default_factory=uuid4)
    agent_id: str = ""
    tenant_id: str = ""
    content: str = ""
    embedding: Optional[list[float]] = None
    tags: list[str] = field(default_factory=list)
    security_level: SecurityLevel = SecurityLevel.INTERNAL
    version: int = 1
    created_at: datetime = field(default_factory=datetime.utcnow)
    accessed_at: Optional[datetime] = None
    access_count: int = 0
    archived: bool = False
```

### 2. MemoryStore（存储抽象）

```python
from abc import ABC, abstractmethod

class MemoryStore(ABC):
    @abstractmethod
    async def save(self, entry: MemoryEntry) -> UUID: ...

    @abstractmethod
    async def search(
        self,
        agent_id: str,
        tenant_id: str,
        query_embedding: list[float],
        limit: int = 5,
        tags: list[str] | None = None,
        include_archived: bool = False,
    ) -> list[tuple[MemoryEntry, float]]: ...

    @abstractmethod
    async def get_recent(
        self,
        agent_id: str,
        tenant_id: str,
        hours: int = 24,
        limit: int = 5,
    ) -> list[MemoryEntry]: ...

    @abstractmethod
    async def archive(self, entry_ids: list[UUID]) -> int: ...

    @abstractmethod
    async def delete(self, entry_ids: list[UUID]) -> int: ...

    @abstractmethod
    async def count(self, agent_id: str, tenant_id: str) -> int: ...
```

**三种实现**：

| 实现 | 依赖 | 搜索方式 | 适用场景 |
|------|------|----------|----------|
| `PgVectorStore` | PostgreSQL + pgvector | HNSW ANN | 生产（默认） |
| `QdrantStore` | Qdrant Server | HNSW ANN | 高性能/大规模 |
| `InMemoryStore` | 无 | 暴力余弦相似度 | mock_mode / 测试 |

### 3. EmbeddingProvider（向量生成抽象）

```python
class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed(self, text: str) -> list[float]: ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]: ...

    @property
    @abstractmethod
    def dimensions(self) -> int: ...
```

**三种实现**：

| 实现 | 依赖 | 维度 | 适用场景 |
|------|------|------|----------|
| `LiteLLMEmbedder` | litellm + API Key | 1536/3072 | 生产（默认） |
| `TFIDFEmbedder` | scikit-learn | 可配置 | 降级模式 |
| `RandomEmbedder` | 无 | 可配置 | mock_mode / 测试 |

### 4. STMManager（短期记忆管理器）

```python
class STMManager:
    """每个 Agent Run 创建一个实例，Run 结束后销毁"""

    def __init__(self, max_tokens: int = 2000):
        self._fixed_zone: dict       # 触发事件 + focus（不可压缩）
        self._sliding_zone: list     # function call 历史（滑动窗口）
        self._injected: list[str]    # Signal 注入的临时指令
        self._token_count: int = 0

    def add_trigger(self, trigger_type: str, payload: dict, focus: str | None): ...
    def add_function_call(self, name: str, args: dict, result: dict): ...
    def add_llm_response(self, content: str): ...
    def inject(self, instruction: str): ...
    def to_prompt_section(self) -> str: ...
    def _compress_if_needed(self): ...
```

**压缩策略**：
1. 固定区（触发事件 + focus + 注入指令）：永不压缩
2. 滑动区（function call 历史）：保留最近 3 轮完整记录
3. 超出部分：由 LLM 生成 1 句话摘要（降级为截断）

### 5. SnapshotBuilder（Run 启动预加载）

```python
class SnapshotBuilder:
    """构建 Agent Run 启动时的记忆快照"""

    async def build(
        self,
        agent_id: str,
        tenant_id: str,
        trigger_event: str,
        focus: str | None,
        max_tokens: int = 500,
    ) -> MemorySnapshot:
        # 1. 语义搜索：与触发事件最相关的 top-3
        semantic_hits = await self.store.search(
            agent_id, tenant_id,
            await self.embedder.embed(trigger_event),
            limit=3,
        )
        # 2. 时间窗口：最近 24h 的记忆（最多 5 条）
        recent = await self.store.get_recent(agent_id, tenant_id, hours=24, limit=5)
        # 3. 固定记忆：pinned 标签
        pinned = await self.store.search(
            agent_id, tenant_id,
            query_embedding=None,  # 无语义过滤
            tags=["pinned"],
        )
        # 4. 去重 + token 裁剪
        return self._assemble(semantic_hits, recent, pinned, max_tokens)
```

### 6. MemoryService（Façade）

```python
class MemoryService:
    """对外统一接口，Agent Tools 和 Runtime 都通过此接口操作记忆"""

    def __init__(
        self,
        store: MemoryStore,
        embedder: EmbeddingProvider,
        config: MemoryConfig,
    ): ...

    # ── Agent Tools 调用 ──
    async def remember(
        self, agent_id: str, tenant_id: str,
        content: str, tags: list[str] | None = None,
    ) -> UUID: ...

    async def recall(
        self, agent_id: str, tenant_id: str,
        query: str, limit: int = 5, tags: list[str] | None = None,
    ) -> list[RecallResult]: ...

    # ── Runtime 调用 ──
    def create_stm(self, max_tokens: int = 2000) -> STMManager: ...

    async def build_snapshot(
        self, agent_id: str, tenant_id: str,
        trigger_event: str, focus: str | None = None,
    ) -> MemorySnapshot: ...

    # ── 生命周期管理 ──
    async def compact(self, agent_id: str, tenant_id: str) -> CompactionResult: ...
    async def prune(
        self, agent_id: str, tenant_id: str,
        before: datetime | None = None,
        tags: list[str] | None = None,
        min_access_count: int = 0,
    ) -> int: ...
    async def reset(self, agent_id: str, tenant_id: str) -> int: ...
```

### 7. MemoryLifecycleManager

```python
class MemoryLifecycleManager:
    """通过 Hatchet cron 定期运行的生命周期管理任务"""

    async def run_maintenance(self, agent_id: str, tenant_id: str):
        count = await self.store.count(agent_id, tenant_id)

        if count > self.config.max_entries:
            await self._archive_excess(agent_id, tenant_id, count)

        await self._delete_expired(agent_id, tenant_id)

        if await self._needs_compaction(agent_id, tenant_id):
            await self._compact_tag_groups(agent_id, tenant_id)
```

## 时间衰减算法

```python
import math

def time_decay(age_hours: float, half_life_hours: float = 168.0) -> float:
    """
    指数衰减函数。
    half_life_hours=168 (7天): 7天前的记忆权重衰减到 0.5
    """
    return math.exp(-0.693 * age_hours / half_life_hours)

def final_score(similarity: float, age_hours: float) -> float:
    """最终排序分 = 语义相似度 × 时间衰减"""
    return similarity * time_decay(age_hours)
```

## 数据库 Schema

```sql
-- Alembic migration: create memory_entries table
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE memory_entries (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id        VARCHAR(255) NOT NULL,
    tenant_id       VARCHAR(255) NOT NULL,
    content         TEXT NOT NULL CHECK (char_length(content) <= 2000),
    embedding       vector(1536),  -- 维度由配置决定
    tags            JSONB DEFAULT '[]'::jsonb,
    security_level  VARCHAR(20) DEFAULT 'internal'
                    CHECK (security_level IN ('public','internal','confidential','restricted')),
    version         INTEGER DEFAULT 1,
    created_at      TIMESTAMPTZ DEFAULT now(),
    accessed_at     TIMESTAMPTZ,
    access_count    INTEGER DEFAULT 0,
    archived        BOOLEAN DEFAULT FALSE,

    CONSTRAINT fk_agent FOREIGN KEY (agent_id, tenant_id)
        REFERENCES agents(agent_id, tenant_id)
);

-- 向量索引（HNSW，适合 recall 查询）
CREATE INDEX idx_memory_embedding ON memory_entries
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- 常规索引
CREATE INDEX idx_memory_agent ON memory_entries (agent_id, tenant_id);
CREATE INDEX idx_memory_created ON memory_entries (created_at DESC);
CREATE INDEX idx_memory_tags ON memory_entries USING gin (tags);
CREATE INDEX idx_memory_archived ON memory_entries (archived) WHERE NOT archived;
```

## 降级策略矩阵

| 组件故障 | remember() 降级 | recall() 降级 | 影响 |
|----------|----------------|---------------|------|
| pgvector 不可用 | 写入行（embedding=NULL） | PostgreSQL ts_vector 全文搜索 | 检索质量降低 |
| Embedding API 不可用 | TF-IDF 向量 | TF-IDF 相似度 | 检索质量降低 |
| PostgreSQL 不可用 | 写入 MEMORY.md 本地文件 | 返回空列表 + 警告 | 记忆丢失风险 |
| 全部不可用 | 返回成功（静默丢弃） | 返回空列表 | Agent 无记忆运行 |

## 配置模型

```yaml
# owlclaw.yaml 中的 memory 配置段
memory:
  vector_backend: pgvector          # pgvector | qdrant | inmemory
  embedding_model: text-embedding-3-small
  embedding_dimensions: 1536
  stm_max_tokens: 2000
  snapshot_max_tokens: 500
  snapshot_semantic_limit: 3
  snapshot_recent_hours: 24
  snapshot_recent_limit: 5
  time_decay_half_life_hours: 168   # 7天半衰期
  max_entries: 10000
  retention_days: 365
  compaction_threshold: 50          # 同标签记忆超过此数触发合并
  embedding_cache_size: 1000

  # Qdrant 特有配置（vector_backend=qdrant 时生效）
  qdrant:
    url: http://localhost:6333
    collection_name: owlclaw_memory
```

## 与其他模块的集成

```
agent-runtime (§5.2.1)
  │
  ├─ 初始化 → MemoryService.create_stm() → STMManager
  ├─ Run 启动 → MemoryService.build_snapshot() → MemorySnapshot → system prompt
  ├─ Run 中 → STMManager.add_function_call() → 维护上下文
  └─ Run 结束 → STMManager 销毁

agent-tools (remember/recall)
  │
  ├─ remember() → MemoryService.remember() → MemoryStore.save()
  └─ recall() → MemoryService.recall() → MemoryStore.search()

triggers-signal (instruct)
  │
  └─ instruct → STMManager.inject() → 注入临时指令到固定区

governance-ledger
  │
  └─ 所有记忆操作 → Ledger.record()

security-data_masker
  │
  └─ recall() 结果 → DataMasker.mask() → 脱敏输出（MCP/Langfuse）

configuration
  │
  └─ MemoryConfig ← owlclaw.yaml.memory
```

## 测试策略

| 层级 | 覆盖 | 工具 |
|------|------|------|
| 单元测试 | MemoryEntry、时间衰减、STM 压缩、SnapshotBuilder | pytest + InMemoryStore |
| 集成测试 | PgVectorStore CRUD + 向量搜索 | pytest + testcontainers (PostgreSQL + pgvector) |
| 降级测试 | 各种故障注入下的降级行为 | pytest + mock |
| 性能测试 | 1M 条记忆下的 recall 延迟 | pytest-benchmark |
| E2E 测试 | Agent Run → remember → 新 Run → recall → 使用经验 | 集成测试套件 |

## 实现优先级

| 阶段 | 内容 | 依赖 |
|------|------|------|
| Phase 1 (MVP) | MemoryEntry + PgVectorStore + LiteLLMEmbedder + MemoryService.remember/recall | owlclaw.db, litellm |
| Phase 1 (MVP) | STMManager + SnapshotBuilder | 无外部依赖 |
| Phase 1 (MVP) | InMemoryStore + RandomEmbedder (mock_mode) | 无外部依赖 |
| Phase 2 | MemoryLifecycleManager + CLI (prune/reset) | Hatchet cron |
| Phase 2 | 安全分类 + DataMasker 集成 | security spec |
| Phase 3 | QdrantStore + TFIDFEmbedder (降级) | qdrant-client, scikit-learn |
| Phase 3 | Compaction（LLM 摘要合并） | litellm |
