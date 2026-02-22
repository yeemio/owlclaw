# Agent Memory 系统实现任务

## 文档联动

- requirements: `.kiro/specs/agent-memory/requirements.md`
- design: `.kiro/specs/agent-memory/design.md`
- tasks: `.kiro/specs/agent-memory/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`

## 任务列表

### Phase 1：MVP（解锁 remember/recall 基本流程）

- [x] **Task 1**: 创建 `owlclaw/agent/memory/` 模块结构
  - 创建 `__init__.py`, `models.py`, `store.py`, `embedder.py`, `stm.py`, `snapshot.py`, `service.py`
  - 定义 `MemoryEntry` dataclass 和 `SecurityLevel` enum
  - 定义 `MemoryStore` 和 `EmbeddingProvider` 抽象基类
  - 定义 `MemoryConfig` Pydantic 模型

- [x] **Task 2**: 实现 `PgVectorStore`
  - 创建 Alembic migration：`memory_entries` 表 + pgvector 扩展 + HNSW 索引
  - 实现 `save()`: INSERT + embedding 写入
  - 实现 `search()`: 向量余弦距离查询 + 时间衰减 + 标签过滤 + archived 过滤
  - 实现 `get_recent()`: 按 created_at 降序 + 时间窗口
  - 实现 `archive()` / `delete()` / `count()`
  - 确保所有查询带 `tenant_id` + `agent_id` 条件

- [x] **Task 3**: 实现 `LiteLLMEmbedder`
  - 通过 `litellm.aembedding()` 生成单条 embedding
  - 实现 `embed_batch()` 批量生成（分批调用，每批 ≤ 100）
  - 实现 LRU Cache（默认 1000 条）
  - 处理 API 错误（重试 3 次，指数退避）
  - 集成 Langfuse span 记录 embedding 调用

- [x] **Task 4**: 实现 `InMemoryStore` + `RandomEmbedder`（mock_mode）
  - `InMemoryStore`: 字典存储 + 暴力余弦相似度搜索
  - `RandomEmbedder`: 固定种子随机向量（确保测试可复现）
  - 验证完整的 remember → recall 流程在 mock_mode 下工作

- [x] **Task 5**: 实现 `STMManager`
  - 实现固定区（trigger + focus + injected instructions）
  - 实现滑动区（function call 历史，保留最近 3 轮）
  - 实现 token 计数（tiktoken 或近似计算）
  - 实现 `_compress_if_needed()`: 超出限制时压缩中间轮次
  - 实现 `inject()`: Signal 指令注入
  - 实现 `to_prompt_section()`: 输出结构化 Markdown 片段

- [x] **Task 6**: 实现 `SnapshotBuilder`
  - 实现语义搜索 top-K 召回
  - 实现最近时间窗口召回
  - 实现 pinned 标签召回
  - 实现去重 + token 裁剪
  - 输出 `MemorySnapshot` 对象（含 prompt 片段 + 来源记忆 ID 列表）

- [x] **Task 7**: 实现 `MemoryService`（Façade）
  - 组装 store + embedder + config
  - 实现 `remember()`: content → embed → save + Ledger 记录
  - 实现 `recall()`: query → embed → search + 更新 accessed_at/access_count + Ledger 记录
  - 实现 `create_stm()` 和 `build_snapshot()` 代理
  - 实现工厂方法 `MemoryService.from_config(config)` 自动选择后端

- [x] **Task 8**: 单元测试（Phase 1）
  - `test_memory_entry.py`: MemoryEntry 创建、序列化
  - `test_stm_manager.py`: 添加/压缩/注入/输出
  - `test_snapshot_builder.py`: 各种条件下的快照构建
  - `test_time_decay.py`: 时间衰减函数的数学正确性
  - `test_inmemory_store.py`: mock_mode 完整流程
  - `test_memory_service.py`: Façade 的集成逻辑
  - 目标覆盖率：> 90%

- [ ] **Task 9**: 集成测试（Phase 1）
  - `test_pgvector_store.py`: 使用 testcontainers 启动 PostgreSQL + pgvector
  - 测试 save → search 完整流程
  - 测试时间衰减排序
  - 测试标签过滤
  - 测试 archive 后不出现在搜索结果中
  - 测试 tenant_id 隔离

### Phase 2：生命周期管理 + 安全

- [ ] **Task 10**: 实现 `MemoryLifecycleManager`
  - 实现自动归档：超过 max_entries 时归档最旧且低访问量的记忆
  - 实现自动清理：超过 retention_days 且低访问量的记忆删除
  - 集成 Hatchet cron（每日凌晨运行）
  - 记录归档/清理事件到 Ledger

- [ ] **Task 11**: 实现 CLI 命令
  - `owlclaw memory list --agent <name>`: 列出记忆（分页、标签过滤）
  - `owlclaw memory prune --agent <name> --before <date> --tags <tags>`: 按条件清理
  - `owlclaw memory reset --agent <name> --confirm`: 重置所有记忆
  - `owlclaw memory stats --agent <name>`: 显示统计信息（总数、存储大小、标签分布）

- [ ] **Task 12**: 实现安全分类
  - 自动安全分类规则引擎（关键词 + 正则）
  - 集成 DataMasker：confidential/restricted 记忆的输出脱敏
  - MCP 通道脱敏拦截器
  - Langfuse tracing 脱敏过滤

### Phase 3：高级功能

- [ ] **Task 13**: 实现 `QdrantStore`
  - Qdrant 集合创建/管理
  - 向量 CRUD 操作
  - 与 PgVectorStore 相同的接口契约
  - 数据迁移工具（pgvector ↔ Qdrant）

- [ ] **Task 14**: 实现 `TFIDFEmbedder`（降级后端）
  - 基于 scikit-learn 的 TF-IDF 向量化
  - 作为 embedding API 不可用时的自动降级
  - 维度可配置（默认 256）

- [ ] **Task 15**: 实现 Compaction（记忆合并）
  - 同标签记忆超过阈值时触发
  - 使用 LLM 生成合并摘要（降级为截断拼接）
  - 原始记忆归档，摘要作为新记忆写入
  - 合并事件记录到 Ledger

- [ ] **Task 16**: 性能测试
  - 使用 pytest-benchmark 测量 recall 延迟
  - 准备 1M 条记忆的测试数据集
  - 验证 P95 < 200ms 的性能目标
  - HNSW 索引参数调优

- [ ] **Task 17**: 降级集成测试
  - 模拟 pgvector 不可用 → 验证全文搜索降级
  - 模拟 embedding API 不可用 → 验证 TF-IDF 降级
  - 模拟 PostgreSQL 不可用 → 验证 MEMORY.md 降级
  - 验证降级事件正确记录到 Ledger

- [ ] **Task 18**: 文档
  - 更新 README 的 Memory 章节
  - 编写 Memory 配置指南（owlclaw.yaml memory 段落）
  - 编写向量后端选择指南（pgvector vs Qdrant vs InMemory）
  - 编写记忆生命周期管理最佳实践
