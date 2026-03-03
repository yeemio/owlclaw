# audit-fix-high — 任务清单

---

## Task 0：H1 Heartbeat 事件源补全

- [x] 0.1 实现 `_check_schedule_events()`：接入 Hatchet 调度状态查询
- [x] 0.2 修正 `_check_database_events()`：使用 Runtime 实际写入的状态值（`"error"` 需重试场景）
- [x] 0.3 为 webhook / queue / external_api 添加配置开关和文档说明
- [x] 0.4 新增 schedule 事件源单元测试（mock Hatchet client）
- [x] 0.5 更新 heartbeat 文档注释，标注各事件源实现状态

## Task 1：H2 成本追踪实现

- [x] 1.1 在 `integrations/llm.py` 的 `acompletion` 中提取 token usage 并计算成本
- [x] 1.2 定义 `CostInfo` dataclass（prompt_tokens, completion_tokens, total_cost）
- [x] 1.3 修改 Runtime `_record_ledger()` 传入真实 `estimated_cost`
- [x] 1.4 确保 mock_mode 下成本为 0
- [x] 1.5 新增测试：LLM 调用后 Ledger 记录包含非零成本
- [x] 1.6 新增测试：BudgetConstraint 基于真实成本触发限制

## Task 2：H3 Embedding 隔离修复

- [x] 2.1 在 `integrations/llm.py` 添加 `aembedding()` 门面函数
- [x] 2.2 重构 `agent/memory/embedder_litellm.py` 使用门面
- [x] 2.3 验证 `owlclaw/agent/memory/` 中无直接 `import litellm`
- [x] 2.4 现有 embedding 测试通过

## Task 3：H4 Console Governance 前端映射修复

- [x] 3.1 修复 `useApi.ts` 中 CircuitBreaker 数据映射（`capability_name` → `name`）
- [x] 3.2 修复 `useApi.ts` 中 VisibilityMatrix 数据映射（按 agent_id 分组）
- [x] 3.3 新增/修复契约测试覆盖这两个映射
- [x] 3.4 重新构建前端静态资源（`npm run build`）

## Task 4：H5 治理 fail-policy 配置

- [x] 4.1 在 `VisibilityFilter` 添加 `fail_policy` 参数（默认 `"open"`）
- [x] 4.2 实现 fail-close 逻辑：评估器异常时隐藏 capability
- [x] 4.3 新增测试：fail-open 策略（默认行为不变）
- [x] 4.4 新增测试：fail-close 策略
- [x] 4.5 在配置系统中暴露 `governance.fail_policy` 配置项

## Task 5：回归验证 + 文档更新

- [x] 5.1 运行完整测试套件确认无回归
- [x] 5.2 更新 `docs/ARCHITECTURE_ANALYSIS.md`：Heartbeat 接口对齐、governance 扩展模块补充
- [x] 5.3 更新架构审计对齐表（SPEC_TASKS_SCAN 的架构对齐审计节）
