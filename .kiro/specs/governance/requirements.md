# Requirements: Governance Layer

## 文档联动

- requirements: `.kiro/specs/governance/requirements.md`
- design: `.kiro/specs/governance/design.md`
- tasks: `.kiro/specs/governance/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


> **目标**：为 OwlClaw Agent 提供生产级治理能力，包括能力可见性过滤、执行记录和模型路由  
> **优先级**：P0  
> **预估工作量**：8-10 天

---

## 1. 背景与动机

### 1.1 当前问题

AI Agent 项目失败的主要原因（Gartner 预测 40% 失败率）：
- **成本失控**：Agent 无限制调用高成本 LLM，导致预算超支
- **缺乏治理**：没有约束机制，Agent 可能执行危险操作
- **不可追溯**：决策过程不透明，无法审计和调试
- **模型选择不当**：所有任务使用同一模型，成本和性能不平衡

OwlClaw 的核心差异化在于**开箱即用的治理层**，这是 LangChain、Restate 等框架缺失的能力。

### 1.2 设计目标

1. **可见性过滤**：在 Agent 看到工具列表之前，根据约束条件过滤掉不可用的能力
2. **执行记录**：记录每次能力执行的完整上下文，支持审计和调试
3. **智能路由**：根据任务类型选择合适的 LLM 模型，平衡成本和性能
4. **零侵入集成**：治理逻辑对业务代码透明，通过配置和装饰器实现

---

## 2. 用户故事

### 2.1 作为系统管理员

**故事 1**：预算控制
```
作为系统管理员
我希望限制 Agent 的月度 LLM 调用预算
这样我可以避免成本失控
```

**验收标准**：
- [ ] 可以为每个 Agent 配置月度预算上限（如 ¥5000/月）
- [ ] 当预算用完时，高成本能力自动从可见工具列表中移除
- [ ] Agent 仍可使用低成本或免费能力
- [ ] 预算重置时间可配置（每月 1 号）
- [ ] 预算使用情况可查询

**故事 2**：时间约束
```
作为业务负责人
我希望某些能力只在特定时间可用（如交易时间）
这样我可以避免 Agent 在非工作时间执行敏感操作
```

**验收标准**：
- [ ] 可以为能力配置时间约束（如 trading_hours_only）
- [ ] 非约束时间内，该能力不在可见工具列表中
- [ ] 支持多种时间约束类型（工作日、交易时间、自定义时间段）
- [ ] 时间约束支持时区配置

**故事 3**：频率限制
```
作为系统管理员
我希望限制某些能力的调用频率
这样我可以避免 Agent 过度调用外部 API 或数据库
```

**验收标准**：
- [ ] 可以为能力配置调用频率限制（如 max_daily_calls: 50）
- [ ] 可以配置冷却时间（如 cooldown_seconds: 300）
- [ ] 超过频率限制时，该能力暂时从可见工具列表中移除
- [ ] 冷却期结束后，能力自动恢复可见

### 2.2 作为开发者

**故事 4**：决策追溯
```
作为开发者
我希望能够查看 Agent 的每次决策记录
这样我可以调试问题和优化 Agent 行为
```

**验收标准**：
- [ ] 每次能力执行都有完整记录（输入、输出、决策理由）
- [ ] 记录包含时间戳、Agent 身份、任务类型
- [ ] 记录包含 LLM 调用的 token 使用量和成本
- [ ] 记录可按时间范围、Agent、能力名称查询
- [ ] 记录支持导出（JSON、CSV）

**故事 5**：模型路由
```
作为开发者
我希望不同类型的任务使用不同的 LLM 模型
这样我可以平衡成本和性能
```

**验收标准**：
- [ ] 可以为不同 task_type 配置不同的模型（如 trading_decision → gpt-4）
- [ ] 支持模型降级链（主模型失败时自动降级）
- [ ] 模型选择逻辑对 Agent Runtime 透明
- [ ] 模型路由配置可热更新

```
作为系统管理员
我希望限制 Agent 每月的 LLM 调用成本
这样我可以避免预算超支
```

**验收标准**：
- [ ] 可以为每个 Agent 配置月度预算上限
- [ ] 当预算用完时，高成本能力自动从可见工具列表中移除
- [ ] Agent 仍可使用低成本或免费能力
- [ ] 预算重置时自动恢复所有能力

**故事 2**：交易时间约束
```
作为业务负责人
我希望交易相关的能力只在交易时间可用
这样我可以避免非交易时间的误操作
```

**验收标准**：
- [ ] 可以在 SKILL.md 中配置 trading_hours_only 约束
- [ ] 非交易时间，该能力不在可见工具列表中
- [ ] 交易时间自动恢复该能力的可见性
- [ ] 支持自定义交易时间规则（工作日 9:30-15:00）

**故事 3**：频率限制
```
作为系统管理员
我希望限制某些能力的调用频率
这样我可以避免 Agent 过度调用外部 API
```

**验收标准**：
- [ ] 可以配置 max_daily_calls（每日最大调用次数）
- [ ] 可以配置 cooldown_seconds（两次调用的最小间隔）
- [ ] 超过限制时，该能力暂时从可见工具列表中移除
- [ ] 限制重置后自动恢复该能力

### 2.2 作为审计人员

**故事 4**：决策追溯
```
作为审计人员
我希望查看 Agent 的所有决策记录
这样我可以审计 Agent 的行为是否合规
```

**验收标准**：
- [ ] 每次能力执行都记录到 Ledger
- [ ] 记录包含：时间、Agent 身份、能力名称、输入参数、输出结果
- [ ] 记录包含 Agent 的决策理由（LLM 的 reasoning）
- [ ] 支持按时间范围、Agent、能力名称查询记录
- [ ] 记录持久化到数据库，支持长期存储

**故事 5**：成本分析
```
作为财务人员
我希望查看每个 Agent 的 LLM 调用成本
这样我可以优化成本分配
```

**验收标准**：
- [ ] Ledger 记录每次 LLM 调用的 token 使用量
- [ ] Ledger 记录每次调用的估算成本
- [ ] 支持按 Agent、按能力、按时间范围统计成本
- [ ] 支持导出成本报告

### 2.3 作为开发者

**故事 6**：模型路由
```
作为开发者
我希望不同类型的任务使用不同的 LLM 模型
这样我可以平衡成本和性能
```

**验收标准**：
- [ ] 可以配置 task_type → model 的映射关系
- [ ] 支持模型降级链（主模型失败时自动降级）
- [ ] 在 SKILL.md 中声明 task_type
- [ ] Agent Runtime 自动根据 task_type 选择模型
- [ ] 记录模型选择和降级事件到 Ledger

---

## 3. 功能需求

### 3.1 可见性过滤（VisibilityFilter）

#### FR-1：预算约束过滤

**需求**：根据 Agent 的月度预算使用情况，过滤高成本能力。

**接口定义**：
```python
class BudgetConstraint:
    async def evaluate(
        self, 
        capability: Capability, 
        agent_id: str,
        context: RunContext
    ) -> FilterResult:
        \"\"\"
        评估预算约束
        
        Returns:
            FilterResult(visible=True) 如果预算充足
            FilterResult(visible=False, reason="预算不足") 如果预算用完
        \"\"\"
```

**验收标准**：
- [ ] WHEN Agent 月度预算未用完时，THE System SHALL 返回 visible=True
- [ ] WHEN Agent 月度预算用完时，THE System SHALL 对高成本能力返回 visible=False
- [ ] THE System SHALL 从配置文件读取预算上限
- [ ] THE System SHALL 从 Ledger 统计当月已用成本
- [ ] THE System SHALL 定义高成本能力的阈值（默认 > ¥0.1/次）
- [ ] THE System SHALL 在每月 1 日自动重置预算计数

#### FR-2：时间约束过滤

**需求**：根据时间规则（如交易时间）过滤能力。

**接口定义**：
```python
class TimeConstraint:
    async def evaluate(
        self, 
        capability: Capability, 
        agent_id: str,
        context: RunContext
    ) -> FilterResult:
        \"\"\"
        评估时间约束
        
        Returns:
            FilterResult(visible=True) 如果当前时间符合约束
            FilterResult(visible=False, reason="非交易时间") 如果不符合
        \"\"\"
```

**验收标准**：
- [ ] THE System SHALL 支持 trading_hours_only 约束
- [ ] THE System SHALL 支持自定义时间规则（cron 表达式）
- [ ] WHEN 当前时间不符合约束时，THE System SHALL 返回 visible=False
- [ ] THE System SHALL 考虑时区（默认使用 Agent 配置的时区）
- [ ] THE System SHALL 支持节假日规则（可选）


#### FR-3：频率限制过滤

**需求**：根据调用频率限制过滤能力。

**接口定义**：
```python
class RateLimitConstraint:
    async def evaluate(
        self, 
        capability: Capability, 
        agent_id: str,
        context: RunContext
    ) -> FilterResult:
        \"\"\"
        评估频率限制
        
        Returns:
            FilterResult(visible=True) 如果未超过限制
            FilterResult(visible=False, reason="超过每日调用次数") 如果超限
        \"\"\"
```

**验收标准**：
- [ ] THE System SHALL 支持 max_daily_calls 约束（每日最大调用次数）
- [ ] THE System SHALL 支持 cooldown_seconds 约束（两次调用最小间隔）
- [ ] THE System SHALL 从 Ledger 统计当日调用次数
- [ ] THE System SHALL 从 Ledger 获取上次调用时间
- [ ] WHEN 超过 max_daily_calls 时，THE System SHALL 返回 visible=False
- [ ] WHEN 距离上次调用不足 cooldown_seconds 时，THE System SHALL 返回 visible=False
- [ ] THE System SHALL 在每日 0 点自动重置调用计数

#### FR-4：熔断约束过滤

**需求**：根据能力的失败率自动熔断。

**接口定义**：
```python
class CircuitBreakerConstraint:
    async def evaluate(
        self, 
        capability: Capability, 
        agent_id: str,
        context: RunContext
    ) -> FilterResult:
        \"\"\"
        评估熔断状态
        
        Returns:
            FilterResult(visible=True) 如果熔断器关闭
            FilterResult(visible=False, reason="熔断中") 如果熔断器打开
        \"\"\"
```

**验收标准**：
- [ ] THE System SHALL 支持 failure_threshold 配置（连续失败次数阈值，默认 5）
- [ ] THE System SHALL 支持 recovery_timeout 配置（熔断恢复时间，默认 300 秒）
- [ ] THE System SHALL 从 Ledger 统计最近的失败次数
- [ ] WHEN 连续失败次数 >= failure_threshold 时，THE System SHALL 打开熔断器
- [ ] WHEN 熔断器打开时，THE System SHALL 返回 visible=False
- [ ] WHEN 熔断器打开超过 recovery_timeout 时，THE System SHALL 自动关闭熔断器
- [ ] THE System SHALL 在能力成功执行后重置失败计数

#### FR-5：VisibilityFilter 集成

**需求**：将所有约束集成到统一的过滤器中。

**接口定义**：
```python
class VisibilityFilter:
    async def filter_capabilities(
        self,
        capabilities: List[Capability],
        agent_id: str,
        context: RunContext
    ) -> List[Capability]:
        \"\"\"
        过滤能力列表
        
        Returns:
            经过所有约束过滤后的能力列表
        \"\"\"
```

**验收标准**：
- [ ] THE System SHALL 对每个能力应用所有约束评估
- [ ] THE System SHALL 只返回所有约束都通过的能力
- [ ] THE System SHALL 记录过滤决策到日志
- [ ] THE System SHALL 支持约束的优先级排序
- [ ] THE System SHALL 支持约束的动态注册
- [ ] THE System SHALL 在 Agent Runtime 调用 filter_capabilities 前执行过滤

### 3.2 执行记录（Ledger）

#### FR-6：能力执行记录

**需求**：记录每次能力执行的完整上下文。

**数据模型**：
```python
class LedgerRecord(Base):
    __tablename__ = 'ledger_records'
    
    id: UUID
    tenant_id: UUID  # 租户隔离
    agent_id: str
    run_id: str
    capability_name: str
    task_type: str
    input_params: dict
    output_result: dict
    decision_reasoning: str  # LLM 的决策理由
    execution_time_ms: int
    llm_model: str
    llm_tokens_input: int
    llm_tokens_output: int
    estimated_cost: Decimal
    status: str  # success / failure / timeout
    error_message: str
    created_at: datetime
```

**验收标准**：
- [ ] THE System SHALL 在能力执行后记录到数据库
- [ ] THE System SHALL 包含所有必需字段
- [ ] THE System SHALL 支持 tenant_id 隔离
- [ ] THE System SHALL 异步写入（不阻塞 Agent Run）
- [ ] THE System SHALL 在写入失败时记录到日志但不中断 Agent Run
- [ ] THE System SHALL 支持批量写入优化


#### FR-7：Ledger 查询接口

**需求**：提供查询接口支持审计和分析。

**接口定义**：
```python
class Ledger:
    async def query_records(
        self,
        tenant_id: UUID,
        filters: LedgerQueryFilters
    ) -> List[LedgerRecord]:
        \"\"\"
        查询执行记录
        
        Args:
            filters: 查询条件（时间范围、agent_id、capability_name 等）
        \"\"\"
    
    async def get_cost_summary(
        self,
        tenant_id: UUID,
        agent_id: str,
        start_date: date,
        end_date: date
    ) -> CostSummary:
        \"\"\"
        统计成本摘要
        \"\"\"
```

**验收标准**：
- [ ] THE System SHALL 支持按时间范围查询
- [ ] THE System SHALL 支持按 agent_id 查询
- [ ] THE System SHALL 支持按 capability_name 查询
- [ ] THE System SHALL 支持按 status 查询
- [ ] THE System SHALL 支持分页查询
- [ ] THE System SHALL 支持成本统计（按 Agent、按能力、按时间）
- [ ] THE System SHALL 强制 tenant_id 隔离

### 3.3 模型路由（Router）

#### FR-8：task_type 路由规则

**需求**：根据 task_type 选择合适的 LLM 模型。

**配置格式**：
`yaml
governance:
  router:
    rules:
      - task_type: trading_decision
        model: gpt-4
        fallback: [claude-3-opus, gpt-3.5-turbo]
      - task_type: monitoring
        model: gpt-3.5-turbo
        fallback: [gpt-4o-mini]
      - task_type: analysis
        model: claude-3-sonnet
        fallback: [gpt-4, gpt-3.5-turbo]
    default_model: gpt-3.5-turbo
```

**验收标准**：
- [ ] THE System SHALL 从配置文件加载路由规则
- [ ] THE System SHALL 根据 task_type 匹配路由规则
- [ ] WHEN 没有匹配规则时，THE System SHALL 使用 default_model
- [ ] THE System SHALL 支持路由规则的热重载
- [ ] THE System SHALL 验证配置的模型名称合法性

#### FR-9：模型降级链

**需求**：主模型失败时自动降级到备用模型。

**接口定义**：
```python
class Router:
    async def select_model(
        self,
        task_type: str,
        context: RunContext
    ) -> ModelSelection:
        \"\"\"
        选择 LLM 模型
        
        Returns:
            ModelSelection(model='gpt-4', fallback=['claude-3-opus'])
        \"\"\"
    
    async def handle_model_failure(
        self,
        failed_model: str,
        task_type: str,
        error: Exception
    ) -> Optional[str]:
        \"\"\"
        处理模型失败，返回降级模型
        
        Returns:
            降级模型名称，如果没有可用降级则返回 None
        \"\"\"
```

**验收标准**：
- [ ] THE System SHALL 在主模型失败时自动尝试 fallback 列表中的模型
- [ ] THE System SHALL 按 fallback 列表顺序依次尝试
- [ ] THE System SHALL 记录降级事件到 Ledger
- [ ] THE System SHALL 区分可重试错误和不可重试错误
- [ ] WHEN 所有模型都失败时，THE System SHALL 返回错误
- [ ] THE System SHALL 支持降级策略配置（立即降级 vs 重试后降级）

#### FR-10：Router 与 Agent Runtime 集成

**需求**：Router 在 Agent Runtime 的 function calling 循环中被调用。

**集成点**：
```python
# Agent Runtime 中的调用
model_selection = await router.select_model(
    task_type=current_skill.task_type,
    context=run_context
)

llm_response = await litellm.acompletion(
    model=model_selection.model,
    messages=messages,
    tools=visible_tools
)
```

**验收标准**：
- [ ] THE System SHALL 在每次 LLM 调用前调用 Router
- [ ] THE System SHALL 将 task_type 从 SKILL.md frontmatter 传递给 Router
- [ ] WHEN SKILL.md 未声明 task_type 时，THE System SHALL 使用 default_model
- [ ] THE System SHALL 在模型失败时调用 handle_model_failure
- [ ] THE System SHALL 将模型选择和降级事件记录到 Ledger

---

## 4. 非功能需求

### 4.1 性能

**NFR-1：约束评估性能**
- 单个约束评估延迟 P95 < 5ms
- VisibilityFilter 总延迟 P95 < 10ms（包含所有约束）
- Ledger 异步写入，不阻塞 Agent Run
- Router 模型选择延迟 P95 < 2ms

**验收标准**：
- [ ] 约束评估使用内存缓存（预算、调用计数）
- [ ] Ledger 使用异步队列批量写入
- [ ] Router 配置缓存在内存中


### 4.2 可靠性

**NFR-2：治理层可靠性**
- 治理层故障不应导致 Agent 完全不可用
- Ledger 写入失败不应中断 Agent Run
- 约束评估失败时应降级为允许（fail-open）

**验收标准**：
- [ ] VisibilityFilter 异常时记录日志并返回所有能力
- [ ] Ledger 写入失败时记录日志但不抛出异常
- [ ] Router 异常时使用 default_model
- [ ] 所有治理组件支持降级模式

### 4.3 安全性

**NFR-3：数据隔离和审计**
- 所有 Ledger 记录强制 tenant_id 隔离
- 敏感数据（如 API keys）不记录到 Ledger
- 支持 Ledger 记录的加密存储（可选）
- 支持审计日志的不可篡改性（可选）

**验收标准**：
- [ ] LedgerRecord 模型包含 tenant_id 字段
- [ ] 所有查询强制 tenant_id 过滤
- [ ] input_params 和 output_result 自动脱敏
- [ ] 支持配置敏感字段列表

### 4.4 可扩展性

**NFR-4：治理组件可扩展**
- 支持自定义约束类型
- 支持自定义路由策略
- 支持自定义 Ledger 存储后端

**验收标准**：
- [ ] 约束评估器使用插件架构
- [ ] Router 支持自定义路由函数
- [ ] Ledger 支持抽象存储接口

---

## 5. 验收标准总览

### 5.1 功能验收

- [ ] **FR-1**：预算约束过滤正常工作
- [ ] **FR-2**：时间约束过滤正常工作
- [ ] **FR-3**：频率限制过滤正常工作
- [ ] **FR-4**：熔断约束过滤正常工作
- [ ] **FR-5**：VisibilityFilter 集成到 Agent Runtime
- [ ] **FR-6**：能力执行记录到 Ledger
- [ ] **FR-7**：Ledger 查询接口可用
- [ ] **FR-8**：task_type 路由规则生效
- [ ] **FR-9**：模型降级链正常工作
- [ ] **FR-10**：Router 集成到 Agent Runtime

### 5.2 非功能验收

- [ ] **NFR-1**：性能指标达标
- [ ] **NFR-2**：治理层故障不影响 Agent 可用性
- [ ] **NFR-3**：tenant_id 隔离生效
- [ ] **NFR-4**：支持自定义扩展

### 5.3 测试验收

- [ ] 单元测试覆盖率 > 80%
- [ ] 集成测试覆盖所有约束类型
- [ ] 端到端测试验证治理层与 Agent Runtime 集成
- [ ] 性能测试验证延迟指标

---

## 6. 约束与假设

### 6.1 约束

- 治理层依赖 database-core（Ledger 需要数据库）
- 治理层依赖 agent-runtime（集成点）
- 治理层依赖 integrations-llm（Router 需要 litellm）
- 约束配置在 SKILL.md frontmatter 的 owlclaw.constraints 字段
- 路由配置在 owlclaw.yaml 的 governance.router 字段

### 6.2 假设

- Agent 的 task_type 在 SKILL.md 中声明
- Ledger 记录的 token 使用量由 litellm 提供
- 成本估算基于公开的模型定价
- 时区配置在 Agent 的 IDENTITY.md 中

---

## 7. 依赖

### 7.1 外部依赖

- PostgreSQL（Ledger 存储）
- litellm（LLM 调用和 token 统计）
- OpenTelemetry（可选，分布式追踪）

### 7.2 内部依赖

- **owlclaw.db**（database-core）— 数据库访问和 Base 模型
- **owlclaw.agent.runtime** — Agent 运行时集成点
- **owlclaw.integrations.llm** — LLM 调用和模型管理
- **owlclaw.capabilities.registry** — 能力注册和元数据

---

## 8. 风险与缓解

### 8.1 风险：约束评估延迟影响 Agent 性能

**影响**：如果约束评估太慢，会增加 Agent Run 的启动延迟。

**缓解**：
- 使用内存缓存存储预算和调用计数
- 约束评估并行执行
- 设置约束评估超时（默认 100ms）

### 8.2 风险：Ledger 写入失败导致数据丢失

**影响**：如果 Ledger 写入失败，审计记录会丢失。

**缓解**：
- 使用异步队列缓冲 Ledger 记录
- 写入失败时重试（最多 3 次）
- 记录写入失败到本地日志文件
- 支持从日志文件恢复 Ledger 记录

### 8.3 风险：模型降级导致决策质量下降

**影响**：降级到低质量模型可能导致 Agent 决策错误。

**缓解**：
- 记录降级事件到 Ledger，便于事后分析
- 支持配置降级策略（如禁止降级到某些模型）
- 提供降级告警通知

### 8.4 风险：约束配置错误导致能力不可用

**影响**：如果约束配置过于严格，Agent 可能无法执行任何能力。

**缓解**：
- 启动时验证约束配置的合法性
- 提供约束配置的测试工具
- 记录约束过滤决策到日志，便于调试

---

## 9. Definition of Done

> 本节定义「实现何时算完成」：**每项打勾且对应验收通过**即该项 done；全节打勾 + 实现+测试通过 = spec 收口。

### 9.1 VisibilityFilter 完成

- [ ] 预算约束评估器实现并通过单元测试
- [ ] 时间约束评估器实现并通过单元测试
- [ ] 频率限制评估器实现并通过单元测试
- [ ] 熔断约束评估器实现并通过单元测试
- [ ] VisibilityFilter 集成所有约束并通过集成测试
- [ ] VisibilityFilter 集成到 Agent Runtime 并通过端到端测试

### 9.2 Ledger 完成

- [ ] LedgerRecord 数据模型实现并通过迁移
- [ ] Ledger 写入接口实现并通过单元测试
- [ ] Ledger 查询接口实现并通过单元测试
- [ ] Ledger 异步写入队列实现并通过性能测试
- [ ] Ledger 集成到 Agent Runtime 并通过端到端测试

### 9.3 Router 完成

- [ ] Router 配置加载实现并通过单元测试
- [ ] Router 模型选择实现并通过单元测试
- [ ] Router 降级链实现并通过单元测试
- [ ] Router 集成到 Agent Runtime 并通过端到端测试
- [ ] Router 降级事件记录到 Ledger 并验证

### 9.4 集成验证

- [ ] 治理层三个组件（VisibilityFilter、Ledger、Router）协同工作
- [ ] Agent Run 完整流程通过端到端测试
- [ ] 性能指标达标（约束评估 < 10ms，Ledger 异步写入）
- [ ] 错误处理和降级策略验证通过

### 9.5 验收矩阵

| 场景/维度 | VisibilityFilter | Ledger | Router | 通过 |
|-----------|-----------------|--------|--------|------|
| 预算用完 | 高成本能力隐藏 | 记录过滤决策 | 使用低成本模型 | [ ] |
| 非交易时间 | 交易能力隐藏 | 记录过滤决策 | 正常路由 | [ ] |
| 超过频率限制 | 能力暂时隐藏 | 记录过滤决策 | 正常路由 | [ ] |
| 能力连续失败 | 熔断器打开 | 记录失败和熔断 | 正常路由 | [ ] |
| 主模型失败 | 正常过滤 | 记录降级事件 | 降级到备用模型 | [ ] |
| Ledger 写入失败 | 正常过滤 | 降级到日志 | 正常路由 | [ ] |

---

## 10. 参考文档

- docs/ARCHITECTURE_ANALYSIS.md §4（治理层设计）
- docs/DATABASE_ARCHITECTURE.md（数据库架构）
- .cursor/rules/owlclaw_database.mdc（数据库编码规范）
- .kiro/specs/agent-runtime/requirements.md（Agent 运行时需求）
- .kiro/specs/database-core/requirements.md（数据库核心需求）
- Agent Skills 规范（agentskills.io）— SKILL.md frontmatter 格式

---

**维护者**：OwlClaw 开发团队  
**最后更新**：2026-02-11
```
