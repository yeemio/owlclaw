# Tasks: Governance Layer

## 文档联动

- requirements: `.kiro/specs/governance/requirements.md`
- design: `.kiro/specs/governance/design.md`
- tasks: `.kiro/specs/governance/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


> **状态**：进行中  
> **预估工作量**：8-10 天  
> **最后更新**：2026-02-23  
> **执行原则**：本清单内所有任务均须专业、认真完成，不区分可选与必选。

---

## 进度概览

- **总任务数**：173
- **已完成**：173
- **进行中**：0
- **未开始**：0

---

## 1. Phase 1：核心基础设施（3 天）

### 1.1 创建 governance 包结构
- [x] 1.1.1 创建 owlclaw/governance/__init__.py
- [x] 1.1.2 创建 owlclaw/governance/visibility.py
- [x] 1.1.3 创建 owlclaw/governance/ledger.py
- [x] 1.1.4 创建 owlclaw/governance/router.py
- [x] 1.1.5 创建 owlclaw/governance/constraints/__init__.py

### 1.2 实现 VisibilityFilter 基类
- [x] 1.2.1 定义 FilterResult 数据类
- [x] 1.2.2 定义 ConstraintEvaluator 协议
- [x] 1.2.3 实现 VisibilityFilter 类
  - [x] 1.2.3.1 实现 register_evaluator 方法
  - [x] 1.2.3.2 实现 filter_capabilities 方法
  - [x] 1.2.3.3 实现并行评估逻辑
  - [x] 1.2.3.4 实现异常处理（fail-open）
- [x] 1.2.4 编写单元测试

### 1.3 实现 Ledger 基类和数据模型
- [x] 1.3.1 定义 LedgerRecord SQLAlchemy 模型
  - [x] 1.3.1.1 添加所有必需字段
  - [x] 1.3.1.2 添加 tenant_id 字段和索引（继承 Base）
  - [x] 1.3.1.3 添加其他索引（agent_id, capability_name, created_at）
- [x] 1.3.2 实现 Ledger 类
  - [x] 1.3.2.1 实现 __init__ 方法
  - [x] 1.3.2.2 实现 record_execution 方法（异步队列）
  - [x] 1.3.2.3 实现 start 和 stop 方法
- [x] 1.3.3 编写单元测试

### 1.4 实现 Router 基类
- [x] 1.4.1 定义 ModelSelection 数据类
- [x] 1.4.2 实现 Router 类
  - [x] 1.4.2.1 实现 __init__ 方法（加载配置）
  - [x] 1.4.2.2 实现 select_model 方法
  - [x] 1.4.2.3 实现 handle_model_failure 方法
  - [x] 1.4.2.4 实现异常处理（降级到 default_model）
- [x] 1.4.3 编写单元测试

---

## 2. Phase 2：约束评估器实现（3 天）

### 2.1 实现 BudgetConstraint
- [x] 2.1.1 创建 owlclaw/governance/constraints/budget.py
- [x] 2.1.2 实现 BudgetConstraint 类
  - [x] 2.1.2.1 实现 __init__ 方法
  - [x] 2.1.2.2 实现 `evaluate` 方法
  - [x] 2.1.2.3 实现 _estimate_capability_cost 方法
  - [x] 2.1.2.4 实现预算统计逻辑（从 Ledger 查询）
- [x] 2.1.3 编写单元测试
  - [x] 2.1.3.1 测试预算充足时允许高成本能力
  - [x] 2.1.3.2 测试预算用完时阻止高成本能力
  - [x] 2.1.3.3 测试预算用完时允许低成本能力

### 2.2 实现 TimeConstraint
- [x] 2.2.1 创建 owlclaw/governance/constraints/time.py
- [x] 2.2.2 实现 TimeConstraint 类
  - [x] 2.2.2.1 实现 __init__ 方法（加载时区和交易时间配置）
  - [x] 2.2.2.2 实现 `evaluate` 方法
  - [x] 2.2.2.3 实现工作日检查逻辑
  - [x] 2.2.2.4 实现交易时间检查逻辑
- [x] 2.2.3 编写单元测试
  - [x] 2.2.3.1 测试交易时间内允许能力
  - [x] 2.2.3.2 测试非交易时间阻止能力
  - [x] 2.2.3.3 测试非工作日阻止能力

### 2.3 实现 RateLimitConstraint
- [x] 2.3.1 创建 owlclaw/governance/constraints/rate_limit.py
- [x] 2.3.2 实现 RateLimitConstraint 类
  - [x] 2.3.2.1 实现 __init__ 方法
  - [x] 2.3.2.2 实现 `evaluate` 方法
  - [x] 2.3.2.3 实现 _get_daily_call_count 方法（带缓存）
  - [x] 2.3.2.4 实现 _get_last_call_time 方法
  - [x] 2.3.2.5 实现 max_daily_calls 检查
  - [x] 2.3.2.6 实现 cooldown_seconds 检查
- [x] 2.3.3 编写单元测试
  - [x] 2.3.3.1 测试未超过每日调用次数时允许
  - [x] 2.3.3.2 测试超过每日调用次数时阻止
  - [x] 2.3.3.3 测试冷却时间内阻止
  - [x] 2.3.3.4 测试冷却时间后允许

### 2.4 实现 CircuitBreakerConstraint
- [x] 2.4.1 创建 owlclaw/governance/constraints/circuit_breaker.py
- [x] 2.4.2 定义 CircuitState 枚举
- [x] 2.4.3 实现 CircuitBreakerConstraint 类
  - [x] 2.4.3.1 实现 __init__ 方法
  - [x] 2.4.3.2 实现 `evaluate` 方法
  - [x] 2.4.3.3 实现 _get_recent_failures 方法
  - [x] 2.4.3.4 实现熔断器状态转换逻辑
  - [x] 2.4.3.5 实现 on_capability_success 方法
- [x] 2.4.4 编写单元测试
  - [x] 2.4.4.1 测试连续失败达到阈值时打开熔断器
  - [x] 2.4.4.2 测试熔断器打开时阻止能力
  - [x] 2.4.4.3 测试恢复超时后自动关闭熔断器
  - [x] 2.4.4.4 测试成功执行后重置熔断器

### 2.5 VisibilityFilter 集成测试
- [x] 2.5.1 编写集成测试：所有约束协同工作
- [x] 2.5.2 编写集成测试：约束评估并行执行
- [x] 2.5.3 编写集成测试：约束评估异常处理

---

## 3. Phase 3：Ledger 和 Router 完整实现（2 天）

### 3.1 实现 Ledger 异步写入队列
- [x] 3.1.1 实现 _background_writer 方法
  - [x] 3.1.1.1 实现队列监听循环
  - [x] 3.1.1.2 实现批量积累逻辑
  - [x] 3.1.1.3 实现超时刷新逻辑
- [x] 3.1.2 实现 _flush_batch 方法
  - [x] 3.1.2.1 实现批量数据库写入
  - [x] 3.1.2.2 实现重试逻辑（3 次，指数退避）
  - [x] 3.1.2.3 实现异常处理
- [x] 3.1.3 实现 _write_to_fallback_log 方法
- [x] 3.1.4 编写单元测试
  - [x] 3.1.4.1 测试批量写入正常工作
  - [x] 3.1.4.2 测试超时自动刷新
  - [x] 3.1.4.3 测试写入失败降级到日志

### 3.2 实现 Ledger 查询接口
- [x] 3.2.1 定义 LedgerQueryFilters 数据类
- [x] 3.2.2 实现 query_records 方法
  - [x] 3.2.2.1 实现 tenant_id 强制过滤
  - [x] 3.2.2.2 实现时间范围过滤
  - [x] 3.2.2.3 实现 agent_id 过滤
  - [x] 3.2.2.4 实现 capability_name 过滤
  - [x] 3.2.2.5 实现分页支持
- [x] 3.2.3 实现 get_cost_summary 方法
  - [x] 3.2.3.1 实现成本聚合查询
  - [x] 3.2.3.2 实现按 Agent 统计
  - [x] 3.2.3.3 实现按能力统计
- [x] 3.2.4 编写单元测试

### 3.3 Router 完整实现
- [x] 3.3.1 实现配置加载和验证
- [x] 3.3.2 实现配置热重载
- [x] 3.3.3 实现降级链完整逻辑
- [x] 3.3.4 编写单元测试
  - [x] 3.3.4.1 测试 task_type 路由规则匹配
  - [x] 3.3.4.2 测试默认模型降级
  - [x] 3.3.4.3 测试降级链顺序
  - [x] 3.3.4.4 测试所有模型失败时返回 None

---

## 4. Phase 4：集成到 Agent Runtime（2 天）

### 4.1 Agent Runtime 集成 VisibilityFilter
- [x] 4.1.1 在 Agent Runtime 初始化时创建 VisibilityFilter
- [x] 4.1.2 注册所有约束评估器
- [x] 4.1.3 在 Agent Run 启动时调用 `filter_capabilities`
- [x] 4.1.4 将过滤后的能力列表传递给 LLM
- [x] 4.1.5 记录过滤决策到日志
- [x] 4.1.6 编写集成测试

### 4.2 Agent Runtime 集成 Router
- [x] 4.2.1 在 Agent Runtime 初始化时创建 Router
- [x] 4.2.2 在每次 LLM 调用前调用 select_model
- [x] 4.2.3 从当前 Skill 的 task_type 获取路由规则
- [x] 4.2.4 实现模型失败时的降级逻辑
- [x] 4.2.5 记录模型选择和降级事件到 Ledger
- [x] 4.2.6 编写集成测试

### 4.3 Agent Runtime 集成 Ledger
- [x] 4.3.1 在 Agent Runtime 初始化时创建 Ledger
- [x] 4.3.2 启动 Ledger 后台写入任务
- [x] 4.3.3 在能力执行后调用 `record_execution`
- [x] 4.3.4 收集所有必需的记录字段
  - [x] 4.3.4.1 从 litellm 获取 token 使用量
  - [x] 4.3.4.2 从 LLM 响应获取决策理由
  - [x] 4.3.4.3 计算执行时间
  - [x] 4.3.4.4 估算成本
- [x] 4.3.5 在 Agent Runtime 停止时停止 Ledger
- [x] 4.3.6 编写集成测试

### 4.4 端到端测试
- [x] 4.4.1 编写完整 Agent Run 端到端测试
- [x] 4.4.2 验证 VisibilityFilter 生效
- [x] 4.4.3 验证 Router 生效
- [x] 4.4.4 验证 Ledger 记录完整
- [x] 4.4.5 验证约束状态更新

---

## 5. Phase 5：数据库迁移和验证（1 天）

### 5.1 创建数据库迁移
- [x] 5.1.1 创建 Alembic 迁移脚本
  - [x] 5.1.1.1 生成迁移文件：`alembic revision --autogenerate -m "add ledger_records table"`
  - [x] 5.1.1.2 验证迁移脚本正确性
  - [x] 5.1.1.3 添加迁移注释和文档
- [x] 5.1.2 运行迁移：`alembic upgrade head`
- [x] 5.1.3 验证表结构
  - [x] 5.1.3.1 验证所有字段存在
  - [x] 5.1.3.2 验证索引创建
  - [x] 5.1.3.3 验证约束（NOT NULL, 外键等）

### 5.2 验证 tenant_id 隔离
- [x] 5.2.1 创建多个 tenant 的测试数据
- [x] 5.2.2 验证查询强制 tenant_id 过滤
- [x] 5.2.3 验证不同 tenant 数据完全隔离
- [x] 5.2.4 编写 tenant 隔离测试

### 5.3 性能测试
- [x] 5.3.1 测试约束评估延迟（目标 P95 < 10ms）
- [x] 5.3.2 测试 Ledger 异步写入性能
- [x] 5.3.3 测试 Ledger 查询性能
- [x] 5.3.4 测试高并发场景
- [x] 5.3.5 优化性能瓶颈

---

## 6. 验收清单

### 6.1 功能验收
- [x] VisibilityFilter 所有约束类型正常工作
- [x] Ledger 记录所有能力执行
- [x] Ledger 查询接口可用
- [x] Router 模型选择和降级正常工作
- [x] 治理层集成到 Agent Runtime

### 6.2 性能验收
- [x] 约束评估延迟 P95 < 10ms
- [x] Ledger 异步写入不阻塞 Agent Run
- [x] Ledger 查询响应时间 P95 < 200ms
- [x] 支持单个 Agent 每分钟 10+ 次 run

### 6.3 测试验收
- [x] 单元测试覆盖率 > 80%
- [x] 所有集成测试通过
- [x] 所有端到端测试通过
- [x] 性能测试达标

### 6.4 文档验收
- [x] API 文档完整
- [x] 配置文档完整
- [x] 集成指南完整
- [x] 故障排查指南完整

---

## 7. 依赖与阻塞

### 7.1 依赖
- **database-core**：Ledger 需要数据库访问和 Base 模型
- **agent-runtime**：治理层需要集成到 Agent Runtime
- **integrations-llm**：Router 需要 litellm 的模型信息

### 7.2 阻塞
- 无

---

## 8. 风险

### 8.1 风险：约束评估延迟影响性能
- **缓解**：使用内存缓存，并行评估，设置超时

### 8.2 风险：Ledger 队列积压
- **缓解**：监控队列长度，动态调整批量大小

### 8.3 风险：模型降级导致决策质量下降
- **缓解**：记录降级事件，提供告警，支持禁止降级配置

---

## 9. 参考文档

- .kiro/specs/governance/requirements.md
- .kiro/specs/governance/design.md
- .kiro/specs/agent-runtime/tasks.md
- .kiro/specs/database-core/tasks.md
- docs/ARCHITECTURE_ANALYSIS.md §4

---

**维护者**：OwlClaw 开发团队  
**最后更新**：2026-02-11
