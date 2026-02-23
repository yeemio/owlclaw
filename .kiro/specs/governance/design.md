# Design: Governance Layer

## 文档联动

- requirements: `.kiro/specs/governance/requirements.md`
- design: `.kiro/specs/governance/design.md`
- tasks: `.kiro/specs/governance/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


> **目标**：为 OwlClaw Agent 提供生产级治理能力的技术设计  
> **状态**：设计中  
> **最后更新**：2026-02-22

---

## 架构例外声明（实现阶段需固化）

本 spec 当前未引入业务层面的数据库铁律例外。实现阶段遵循以下约束：

1. 治理层所有持久化与查询路径统一采用 `tenant_id: str`（对应数据库 `VARCHAR(64)`）。
2. `alembic_version` 属于 Alembic 系统表，不适用业务表约束。

除上述显式例外外，治理层业务表与查询路径仍严格遵循数据库五条铁律（`tenant_id` 前缀索引、`TIMESTAMPTZ`、Alembic 管理等）。

## 1. 架构设计

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Agent Runtime                             │
│                                                                  │
│  ┌──────────────┐                                                │
│  │ Agent Run    │                                                │
│  │ 启动         │                                                │
│  └──────┬───────┘                                                │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Governance Layer                            │   │
│  │                                                          │   │
│  │  ┌─────────────────┐  ┌─────────────┐  ┌────────────┐  │   │
│  │  │ VisibilityFilter│  │   Ledger    │  │   Router   │  │   │
│  │  │                 │  │             │  │            │  │   │
│  │  │ • 预算约束      │  │ • 记录执行  │  │ • 模型选择 │  │   │
│  │  │ • 时间约束      │  │ • 查询统计  │  │ • 降级链   │  │   │
│  │  │ • 频率限制      │  │ • 成本分析  │  │ • 路由规则 │  │   │
│  │  │ • 熔断器        │  │             │  │            │  │   │
│  │  └────────┬────────┘  └──────┬──────┘  └─────┬──────┘  │   │
│  │           │                  │               │         │   │
│  └───────────┼──────────────────┼───────────────┼─────────┘   │
│              │                  │               │             │
│              ▼                  ▼               ▼             │
│  ┌───────────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ 过滤后的能力列表   │  │ 执行记录      │  │ 选中的模型    │   │
│  └───────────────────┘  └──────────────┘  └──────────────┘   │
│              │                  │               │             │
│              ▼                  │               ▼             │
│  ┌──────────────────────────────┼───────────────────────────┐ │
│  │         LLM Function Calling  │                           │ │
│  └──────────────────────────────┼───────────────────────────┘ │
│                                  │                             │
│                                  ▼                             │
│                          ┌──────────────┐                      │
│                          │ 能力执行完成  │                      │
│                          └──────┬───────┘                      │
│                                  │                             │
│                                  ▼                             │
│                          ┌──────────────┐                      │
│                          │ Ledger 记录  │                      │
│                          └──────────────┘                      │
└─────────────────────────────────────────────────────────────────┘

                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │   PostgreSQL Database   │
                    │                         │
                    │  • ledger_records 表    │
                    │  • tenant_id 隔离       │
                    └─────────────────────────┘
```

**架构说明**：

治理层由三个核心组件组成，在 Agent Runtime 的不同阶段发挥作用：

1. **VisibilityFilter**：在 Agent Run 启动时过滤能力列表，只向 LLM 展示符合约束条件的能力
2. **Router**：在每次 LLM 调用前选择合适的模型，支持降级链
3. **Ledger**：在能力执行后异步记录完整上下文，支持审计和成本分析

### 1.2 核心组件

#### 组件 1：VisibilityFilter（可见性过滤器）

**职责**：在 Agent 看到工具列表之前，根据约束条件过滤能力。

**接口定义**：
```python
from typing import List, Protocol
from dataclasses import dataclass

@dataclass
class FilterResult:
    visible: bool
    reason: str = ""

class ConstraintEvaluator(Protocol):
    async def evaluate(
        self,
        capability: Capability,
        agent_id: str,
        context: RunContext
    ) -> FilterResult:
        ...

class VisibilityFilter:
    def __init__(self):
        self.evaluators: List[ConstraintEvaluator] = []
    
    def register_evaluator(self, evaluator: ConstraintEvaluator):
        """注册约束评估器"""
        self.evaluators.append(evaluator)
    
    async def filter_capabilities(
        self,
        capabilities: List[Capability],
        agent_id: str,
        context: RunContext
    ) -> List[Capability]:
        """
        过滤能力列表
        
        对每个能力应用所有约束评估器，只返回所有约束都通过的能力
        """
        filtered = []
        for cap in capabilities:
            visible = True
            reasons = []
            
            for evaluator in self.evaluators:
                result = await evaluator.evaluate(cap, agent_id, context)
                if not result.visible:
                    visible = False
                    reasons.append(result.reason)
            
            if visible:
                filtered.append(cap)
            else:
                logger.info(f"Capability {cap.name} filtered: {reasons}")
        
        return filtered
```

**设计要点**：
- 使用 Protocol 定义约束评估器接口，支持插件化扩展
- 所有约束评估器并行执行，提高性能
- 记录过滤决策到日志，便于调试
- 异常处理采用 fail-open 策略（评估失败时允许能力可见）

#### 组件 2：Ledger（执行记录）

**职责**：记录每次能力执行的完整上下文，支持查询和分析。

**接口定义**：
```python
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from uuid import UUID
from datetime import datetime, date
from typing import List, Optional
import asyncio

class Ledger:
    def __init__(self, session_factory, batch_size=10, flush_interval=5):
        self.session_factory = session_factory
        self.write_queue = asyncio.Queue()
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._writer_task = None
    
    async def start(self):
        """启动后台写入任务"""
        self._writer_task = asyncio.create_task(self._background_writer())
    
    async def stop(self):
        """停止后台写入任务"""
        if self._writer_task:
            self._writer_task.cancel()
            try:
                await self._writer_task
            except asyncio.CancelledError:
                pass
    
    async def record_execution(
        self,
        tenant_id: str,
        agent_id: str,
        run_id: str,
        capability_name: str,
        task_type: str,
        input_params: dict,
        output_result: dict,
        decision_reasoning: str,
        execution_time_ms: int,
        llm_model: str,
        llm_tokens_input: int,
        llm_tokens_output: int,
        estimated_cost: Decimal,
        status: str,
        error_message: str = None
    ):
        """记录能力执行（异步写入）"""
        record = LedgerRecord(
            tenant_id=tenant_id,
            agent_id=agent_id,
            run_id=run_id,
            capability_name=capability_name,
            task_type=task_type,
            input_params=input_params,
            output_result=output_result,
            decision_reasoning=decision_reasoning,
            execution_time_ms=execution_time_ms,
            llm_model=llm_model,
            llm_tokens_input=llm_tokens_input,
            llm_tokens_output=llm_tokens_output,
            estimated_cost=estimated_cost,
            status=status,
            error_message=error_message
        )
        
        await self.write_queue.put(record)

    async def query_records(
        self,
        tenant_id: str,
        filters: LedgerQueryFilters
    ) -> List[LedgerRecord]:
        """查询执行记录"""
        async with self.session_factory() as session:
            query = select(LedgerRecord).where(
                LedgerRecord.tenant_id == tenant_id
            )
            
            if filters.agent_id:
                query = query.where(LedgerRecord.agent_id == filters.agent_id)
            if filters.capability_name:
                query = query.where(LedgerRecord.capability_name == filters.capability_name)
            if filters.start_date:
                query = query.where(LedgerRecord.created_at >= filters.start_date)
            if filters.end_date:
                query = query.where(LedgerRecord.created_at <= filters.end_date)
            if filters.status:
                query = query.where(LedgerRecord.status == filters.status)
            
            if filters.limit:
                query = query.limit(filters.limit)
            if filters.offset:
                query = query.offset(filters.offset)
            
            result = await session.execute(query)
            return result.scalars().all()
    
    async def get_cost_summary(
        self,
        tenant_id: str,
        agent_id: str,
        start_date: date,
        end_date: date
    ) -> CostSummary:
        """统计成本摘要"""
        async with self.session_factory() as session:
            query = select(
                func.sum(LedgerRecord.estimated_cost).label('total_cost'),
                func.count(LedgerRecord.id).label('total_calls')
            ).where(
                LedgerRecord.tenant_id == tenant_id,
                LedgerRecord.agent_id == agent_id,
                LedgerRecord.created_at >= start_date,
                LedgerRecord.created_at <= end_date
            )
            
            result = await session.execute(query)
            row = result.first()
            
            return CostSummary(
                total_cost=row.total_cost or Decimal('0'),
                total_calls=row.total_calls or 0
            )
```

**设计要点**：
- 异步队列批量写入，避免阻塞 Agent Run
- 强制 tenant_id 隔离，确保数据安全
- 支持灵活的查询条件和分页
- 提供成本统计接口，支持预算管理


#### 组件 3：Router（模型路由）

**职责**：根据 task_type 选择合适的 LLM 模型，支持降级链。

**接口定义**：
```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ModelSelection:
    model: str
    fallback: List[str]

class Router:
    def __init__(self, config: dict):
        self.rules = config.get('rules', [])
        self.default_model = config.get('default_model', 'gpt-3.5-turbo')
        self._validate_config()
    
    def _validate_config(self):
        """验证配置的模型名称合法性"""
        valid_models = {
            'gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo', 'gpt-4o-mini',
            'claude-3-opus', 'claude-3-sonnet', 'claude-3-haiku'
        }
        
        for rule in self.rules:
            if rule['model'] not in valid_models:
                logger.warning(f"Unknown model in config: {rule['model']}")
            for fallback in rule.get('fallback', []):
                if fallback not in valid_models:
                    logger.warning(f"Unknown fallback model: {fallback}")
    
    async def select_model(
        self,
        task_type: str,
        context: RunContext
    ) -> ModelSelection:
        """选择 LLM 模型"""
        for rule in self.rules:
            if rule['task_type'] == task_type:
                return ModelSelection(
                    model=rule['model'],
                    fallback=rule.get('fallback', [])
                )
        
        return ModelSelection(
            model=self.default_model,
            fallback=[]
        )
    
    async def handle_model_failure(
        self,
        failed_model: str,
        task_type: str,
        error: Exception,
        fallback_chain: List[str]
    ) -> Optional[str]:
        """处理模型失败，返回降级模型"""
        if not fallback_chain:
            return None
        
        next_model = fallback_chain[0]
        logger.warning(
            f"Model {failed_model} failed for task_type {task_type}, "
            f"falling back to {next_model}. Error: {error}"
        )
        
        return next_model
```

**设计要点**：
- 基于 task_type 的路由规则，支持不同任务使用不同模型
- 降级链机制，主模型失败时自动尝试备用模型
- 配置验证，启动时检查模型名称合法性
- 降级事件记录到 Ledger，便于事后分析


---

## 2. 实现细节

### 2.1 文件结构

```
owlclaw/
├── governance/
│   ├── __init__.py
│   ├── visibility.py          # VisibilityFilter + 约束评估器基类
│   ├── ledger.py              # Ledger + LedgerRecord 模型
│   ├── router.py              # Router + 路由规则
│   └── constraints/
│       ├── __init__.py
│       ├── budget.py          # BudgetConstraint
│       ├── time.py            # TimeConstraint
│       ├── rate_limit.py      # RateLimitConstraint
│       └── circuit_breaker.py # CircuitBreakerConstraint
```

### 2.2 约束评估器实现

#### 2.2.1 BudgetConstraint（预算约束）

**当前问题**：Agent 无限制调用高成本 LLM，导致预算超支。

**解决方案**：在能力可见性过滤阶段，检查 Agent 的月度预算使用情况，如果预算用完则隐藏高成本能力。

**实现**：
```python
from decimal import Decimal
from datetime import datetime, date

class BudgetConstraint:
    def __init__(self, ledger: Ledger, config: dict):
        self.ledger = ledger
        self.high_cost_threshold = Decimal(config.get('high_cost_threshold', '0.1'))
        self.budget_limits = config.get('budget_limits', {})  # {agent_id: limit}
    
    async def evaluate(
        self,
        capability: Capability,
        agent_id: str,
        context: RunContext
    ) -> FilterResult:
        # 获取 Agent 的预算上限
        budget_limit = self.budget_limits.get(agent_id)
        if not budget_limit:
            return FilterResult(visible=True)
        
        # 统计当月已用成本
        start_of_month = date.today().replace(day=1)
        cost_summary = await self.ledger.get_cost_summary(
            tenant_id=context.tenant_id,
            agent_id=agent_id,
            start_date=start_of_month,
            end_date=date.today()
        )
        
        used_cost = cost_summary.total_cost
        remaining = Decimal(budget_limit) - used_cost
        
        # 如果预算用完，隐藏高成本能力
        if remaining <= 0:
            estimated_cost = self._estimate_capability_cost(capability)
            if estimated_cost > self.high_cost_threshold:
                return FilterResult(
                    visible=False,
                    reason=f"预算不足（已用 {used_cost}，上限 {budget_limit}）"
                )
        
        return FilterResult(visible=True)
    
    def _estimate_capability_cost(self, capability: Capability) -> Decimal:
        """估算能力的单次调用成本"""
        # 从历史记录或配置中获取平均成本
        return capability.metadata.get('estimated_cost', Decimal('0.05'))
```

**关键点**：
- 使用 Ledger 统计当月成本，避免重复计算
- 高成本阈值可配置（默认 ¥0.1/次）
- 预算用完时只隐藏高成本能力，保留低成本能力
- 每月 1 日自动重置预算计数


#### 2.2.2 TimeConstraint（时间约束）

**当前问题**：某些能力（如交易操作）只应在特定时间可用。

**解决方案**：检查当前时间是否符合能力的时间约束。

**实现**：
```python
from datetime import datetime, time
import pytz

class TimeConstraint:
    def __init__(self, config: dict):
        self.trading_hours = config.get('trading_hours', {
            'start': time(9, 30),
            'end': time(15, 0),
            'weekdays': [0, 1, 2, 3, 4]  # 周一到周五
        })
        self.timezone = pytz.timezone(config.get('timezone', 'Asia/Shanghai'))
    
    async def evaluate(
        self,
        capability: Capability,
        agent_id: str,
        context: RunContext
    ) -> FilterResult:
        constraints = capability.metadata.get('owlclaw', {}).get('constraints', {})
        
        # 检查 trading_hours_only 约束
        if constraints.get('trading_hours_only'):
            now = datetime.now(self.timezone)
            
            # 检查是否工作日
            if now.weekday() not in self.trading_hours['weekdays']:
                return FilterResult(
                    visible=False,
                    reason="非交易日"
                )
            
            # 检查是否交易时间
            current_time = now.time()
            if not (self.trading_hours['start'] <= current_time <= self.trading_hours['end']):
                return FilterResult(
                    visible=False,
                    reason=f"非交易时间（交易时间：{self.trading_hours['start']}-{self.trading_hours['end']}）"
                )
        
        return FilterResult(visible=True)
```

**关键点**：
- 支持时区配置
- 支持自定义交易时间和工作日
- 可扩展支持节假日规则
- 约束配置在 SKILL.md frontmatter 的 owlclaw.constraints 字段


#### 2.2.3 RateLimitConstraint（频率限制）

**当前问题**：Agent 可能过度调用某些能力，导致外部 API 限流或成本过高。

**解决方案**：检查能力的调用频率，超过限制时暂时隐藏。

**实现**：
```python
from datetime import datetime, timedelta, date

class RateLimitConstraint:
    def __init__(self, ledger: Ledger):
        self.ledger = ledger
        self.cache = {}  # {(agent_id, capability_name): (count, last_call_time)}
    
    async def evaluate(
        self,
        capability: Capability,
        agent_id: str,
        context: RunContext
    ) -> FilterResult:
        constraints = capability.metadata.get('owlclaw', {}).get('constraints', {})
        
        max_daily_calls = constraints.get('max_daily_calls')
        cooldown_seconds = constraints.get('cooldown_seconds')
        
        if not max_daily_calls and not cooldown_seconds:
            return FilterResult(visible=True)
        
        cache_key = (agent_id, capability.name)
        
        # 检查每日调用次数
        if max_daily_calls:
            count = await self._get_daily_call_count(
                context.tenant_id, agent_id, capability.name
            )
            if count >= max_daily_calls:
                return FilterResult(
                    visible=False,
                    reason=f"超过每日调用次数限制（{count}/{max_daily_calls}）"
                )
        
        # 检查冷却时间
        if cooldown_seconds:
            last_call_time = await self._get_last_call_time(
                context.tenant_id, agent_id, capability.name
            )
            if last_call_time:
                elapsed = (datetime.utcnow() - last_call_time).total_seconds()
                if elapsed < cooldown_seconds:
                    remaining = int(cooldown_seconds - elapsed)
                    return FilterResult(
                        visible=False,
                        reason=f"冷却中（还需等待 {remaining} 秒）"
                    )
        
        return FilterResult(visible=True)
    
    async def _get_daily_call_count(
        self, tenant_id: str, agent_id: str, capability_name: str
    ) -> int:
        """获取今日调用次数（带缓存）"""
        today = date.today()
        records = await self.ledger.query_records(
            tenant_id=tenant_id,
            filters=LedgerQueryFilters(
                agent_id=agent_id,
                capability_name=capability_name,
                start_date=today,
                end_date=today
            )
        )
        return len(records)
    
    async def _get_last_call_time(
        self, tenant_id: str, agent_id: str, capability_name: str
    ) -> Optional[datetime]:
        """获取上次调用时间"""
        records = await self.ledger.query_records(
            tenant_id=tenant_id,
            filters=LedgerQueryFilters(
                agent_id=agent_id,
                capability_name=capability_name,
                limit=1,
                order_by='created_at DESC'
            )
        )
        return records[0].created_at if records else None
```

**关键点**：
- 使用缓存减少数据库查询
- 支持每日调用次数和冷却时间两种限制
- 限制重置时间自动处理（每日 0 点）
- 冷却时间精确到秒


#### 2.2.4 CircuitBreakerConstraint（熔断器）

**当前问题**：能力连续失败时，继续调用会浪费资源。

**解决方案**：实现熔断器模式，连续失败达到阈值时自动熔断。

**实现**：
```python
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"      # 正常状态
    OPEN = "open"          # 熔断状态
    HALF_OPEN = "half_open" # 半开状态（尝试恢复）

class CircuitBreakerConstraint:
    def __init__(self, ledger: Ledger, config: dict):
        self.ledger = ledger
        self.failure_threshold = config.get('failure_threshold', 5)
        self.recovery_timeout = config.get('recovery_timeout', 300)  # 秒
        self.circuit_states = {}  # {(agent_id, capability_name): (state, open_time)}
    
    async def evaluate(
        self,
        capability: Capability,
        agent_id: str,
        context: RunContext
    ) -> FilterResult:
        cache_key = (agent_id, capability.name)
        
        # 获取熔断器状态
        state, open_time = self.circuit_states.get(cache_key, (CircuitState.CLOSED, None))
        
        if state == CircuitState.OPEN:
            # 检查是否可以恢复
            if open_time and (datetime.utcnow() - open_time).total_seconds() > self.recovery_timeout:
                self.circuit_states[cache_key] = (CircuitState.HALF_OPEN, None)
                return FilterResult(visible=True)
            else:
                return FilterResult(
                    visible=False,
                    reason="熔断中（能力连续失败）"
                )
        
        # 检查最近的失败次数
        recent_failures = await self._get_recent_failures(
            context.tenant_id, agent_id, capability.name
        )
        
        if recent_failures >= self.failure_threshold:
            # 打开熔断器
            self.circuit_states[cache_key] = (CircuitState.OPEN, datetime.utcnow())
            return FilterResult(
                visible=False,
                reason=f"熔断器打开（连续失败 {recent_failures} 次）"
            )
        
        return FilterResult(visible=True)
    
    async def _get_recent_failures(
        self, tenant_id: str, agent_id: str, capability_name: str
    ) -> int:
        """获取最近的连续失败次数"""
        records = await self.ledger.query_records(
            tenant_id=tenant_id,
            filters=LedgerQueryFilters(
                agent_id=agent_id,
                capability_name=capability_name,
                limit=self.failure_threshold + 1,
                order_by='created_at DESC'
            )
        )
        
        # 统计连续失败次数
        failures = 0
        for record in records:
            if record.status == 'failure':
                failures += 1
            else:
                break  # 遇到成功记录就停止
        
        return failures
    
    async def on_capability_success(self, agent_id: str, capability_name: str):
        """能力执行成功时调用，重置熔断器"""
        cache_key = (agent_id, capability_name)
        if cache_key in self.circuit_states:
            self.circuit_states[cache_key] = (CircuitState.CLOSED, None)
```

**关键点**：
- 实现标准的熔断器模式（CLOSED → OPEN → HALF_OPEN → CLOSED）
- 连续失败次数可配置（默认 5 次）
- 恢复超时可配置（默认 300 秒）
- 成功执行后自动重置熔断器
- 熔断器状态在内存中维护，重启后重置


### 2.3 数据模型

#### 2.3.1 LedgerRecord（执行记录）

**实现**：
```python
from sqlalchemy import Column, String, Integer, JSON, DECIMAL, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID
from owlclaw.db import Base
import uuid
from datetime import datetime

class LedgerRecord(Base):
    __tablename__ = 'ledger_records'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    agent_id = Column(String(255), nullable=False, index=True)
    run_id = Column(String(255), nullable=False, index=True)
    capability_name = Column(String(255), nullable=False, index=True)
    task_type = Column(String(100), nullable=False, index=True)
    
    input_params = Column(JSON, nullable=False)
    output_result = Column(JSON, nullable=True)
    decision_reasoning = Column(String, nullable=True)
    
    execution_time_ms = Column(Integer, nullable=False)
    llm_model = Column(String(100), nullable=False)
    llm_tokens_input = Column(Integer, nullable=False)
    llm_tokens_output = Column(Integer, nullable=False)
    estimated_cost = Column(DECIMAL(10, 4), nullable=False)
    
    status = Column(
        Enum('success', 'failure', 'timeout', name='execution_status'),
        nullable=False,
        index=True
    )
    error_message = Column(String, nullable=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        {'comment': 'Agent 能力执行记录，用于审计和成本分析'}
    )
```

**关键点**：
- 所有表必须包含 tenant_id（租户隔离）
- 关键字段建立索引（tenant_id, agent_id, capability_name, created_at, status）
- input_params 和 output_result 使用 JSON 类型
- estimated_cost 使用 DECIMAL 类型保证精度
- status 使用 Enum 类型确保数据一致性

#### 2.3.2 辅助数据类

```python
from dataclasses import dataclass
from decimal import Decimal
from datetime import date
from typing import Optional

@dataclass
class LedgerQueryFilters:
    agent_id: Optional[str] = None
    capability_name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    limit: Optional[int] = None
    offset: Optional[int] = None
    order_by: Optional[str] = None

@dataclass
class CostSummary:
    total_cost: Decimal
    total_calls: int
```


### 2.4 Ledger 异步写入队列

**当前问题**：同步写入 Ledger 会阻塞 Agent Run。

**解决方案**：使用异步队列批量写入。

**实现**：
```python
import asyncio
from typing import List
import json

class Ledger:
    # ... (前面的方法)
    
    async def _background_writer(self):
        """后台批量写入任务"""
        batch = []
        
        while True:
            try:
                # 等待新记录或超时
                record = await asyncio.wait_for(
                    self.write_queue.get(),
                    timeout=self.flush_interval
                )
                batch.append(record)
                
                # 达到批量大小时写入
                if len(batch) >= self.batch_size:
                    await self._flush_batch(batch)
                    batch = []
            
            except asyncio.TimeoutError:
                # 超时时写入当前批次
                if batch:
                    await self._flush_batch(batch)
                    batch = []
            
            except asyncio.CancelledError:
                # 停止时写入剩余批次
                if batch:
                    await self._flush_batch(batch)
                raise
            
            except Exception as e:
                logger.error(f"Ledger writer error: {e}")
    
    async def _flush_batch(self, batch: List[LedgerRecord]):
        """批量写入数据库"""
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                async with self.session_factory() as session:
                    session.add_all(batch)
                    await session.commit()
                    logger.info(f"Flushed {len(batch)} ledger records")
                    return
            
            except Exception as e:
                logger.warning(f"Ledger write attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))
                else:
                    logger.error(f"Ledger write failed after {max_retries} attempts")
                    # 写入失败时记录到本地日志文件
                    await self._write_to_fallback_log(batch)
    
    async def _write_to_fallback_log(self, batch: List[LedgerRecord]):
        """写入失败时的降级方案"""
        try:
            with open('ledger_fallback.log', 'a') as f:
                for record in batch:
                    f.write(json.dumps({
                        'tenant_id': str(record.tenant_id),
                        'agent_id': record.agent_id,
                        'run_id': record.run_id,
                        'capability_name': record.capability_name,
                        'task_type': record.task_type,
                        'status': record.status,
                        'created_at': record.created_at.isoformat()
                    }) + '\n')
            logger.info(f"Wrote {len(batch)} records to fallback log")
        except Exception as e:
            logger.error(f"Failed to write to fallback log: {e}")
```

**关键点**：
- 批量写入减少数据库连接开销（默认 10 条/批）
- 超时自动刷新避免数据积压（默认 5 秒）
- 写入失败时重试 3 次，指数退避
- 最终失败时降级到本地日志文件
- 优雅停止时写入剩余批次


---

## 3. 数据流

### 3.1 Agent Run 完整流程

```
┌─────────────────────────────────────────────────────────────────┐
│                     Agent Run 启动                               │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 1: 加载身份和知识                                          │
│  • 加载 SOUL.md、IDENTITY.md                                    │
│  • 加载 Skills 的 SKILL.md                                      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 2: 获取所有注册的能力                                      │
│  • 从 Capability Registry 获取 business capabilities            │
│  • 从 Built-in Tools 获取内建工具                               │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 3: VisibilityFilter 过滤能力                              │
│  • BudgetConstraint: 检查预算                                   │
│  • TimeConstraint: 检查时间约束                                 │
│  • RateLimitConstraint: 检查频率限制                            │
│  • CircuitBreakerConstraint: 检查熔断状态                       │
│  → 返回过滤后的能力列表                                          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 4: Router 选择 LLM 模型                                    │
│  • 从当前 Skill 的 task_type 获取路由规则                        │
│  • 返回 ModelSelection(model, fallback)                         │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 5: LLM Function Calling                                   │
│  • 构建 system prompt（身份 + 知识 + 可见工具）                  │
│  • 调用 litellm.acompletion(model, tools)                       │
│  • LLM 返回 function call 请求                                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 6: 执行能力                                                │
│  • 调用对应的 capability handler                                 │
│  • 记录执行时间和结果                                            │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 7: Ledger 记录执行                                         │
│  • 创建 LedgerRecord                                            │
│  • 异步写入队列                                                  │
│  • 后台批量写入数据库                                            │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 8: 更新约束状态                                            │
│  • 更新预算使用量（通过 Ledger 查询）                            │
│  • 更新调用计数（通过 Ledger 查询）                              │
│  • 更新熔断器状态（成功时重置）                                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 9: Agent Run 完成                                          │
└─────────────────────────────────────────────────────────────────┘
```

**关键点**：
- VisibilityFilter 在 LLM 调用之前执行（Step 3）
- Router 在每次 LLM 调用时选择模型（Step 4）
- Ledger 记录在能力执行之后异步写入（Step 7）
- 约束状态在 Ledger 记录后更新（Step 8）
- 整个流程对业务代码透明，通过配置和装饰器实现


### 3.2 模型降级流程

```
┌─────────────────────────────────────────────────────────────────┐
│  Router.select_model(task_type='trading_decision')              │
│  → ModelSelection(model='gpt-4', fallback=['claude-3', 'gpt-3.5'])│
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  尝试调用 gpt-4                                                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
                    失败（rate limit）
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Router.handle_model_failure('gpt-4', error, fallback)          │
│  → 返回 'claude-3'                                              │
│  → Ledger 记录降级事件                                           │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  尝试调用 claude-3                                               │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
                       成功
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  继续 Agent Run                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**关键点**：
- 主模型失败时自动尝试 fallback 列表中的模型
- 按 fallback 列表顺序依次尝试
- 记录降级事件到 Ledger，便于事后分析
- 区分可重试错误和不可重试错误
- 所有模型都失败时返回错误

### 3.3 约束评估流程

```
┌─────────────────────────────────────────────────────────────────┐
│  VisibilityFilter.filter_capabilities(capabilities)             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
                  对每个能力并行评估
                         │
        ┌────────────────┼────────────────┬────────────────┐
        │                │                │                │
        ▼                ▼                ▼                ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Budget       │ │ Time         │ │ RateLimit    │ │ Circuit      │
│ Constraint   │ │ Constraint   │ │ Constraint   │ │ Breaker      │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │                │
       └────────────────┼────────────────┼────────────────┘
                        │                │
                        ▼                ▼
                  所有约束都通过？
                        │
            ┌───────────┴───────────┐
            │                       │
           是                      否
            │                       │
            ▼                       ▼
    ┌──────────────┐        ┌──────────────┐
    │ 能力可见     │        │ 能力隐藏     │
    │ 添加到列表   │        │ 记录原因     │
    └──────────────┘        └──────────────┘
```

**关键点**：
- 所有约束评估器并行执行，提高性能
- 任一约束不通过，能力即被过滤
- 记录过滤原因到日志，便于调试
- 评估失败时采用 fail-open 策略


---

## 4. 错误处理

### 4.1 VisibilityFilter 异常处理

**场景**：约束评估器抛出异常（如数据库连接失败）。

**处理策略**：Fail-open（评估失败时允许能力可见）

**实现**：
```python
async def filter_capabilities(
    self,
    capabilities: List[Capability],
    agent_id: str,
    context: RunContext
) -> List[Capability]:
    filtered = []
    
    for cap in capabilities:
        try:
            visible = True
            reasons = []
            
            for evaluator in self.evaluators:
                try:
                    result = await evaluator.evaluate(cap, agent_id, context)
                    if not result.visible:
                        visible = False
                        reasons.append(result.reason)
                except Exception as e:
                    logger.error(
                        f"Constraint evaluation error for {cap.name} "
                        f"by {evaluator.__class__.__name__}: {e}"
                    )
                    # Fail-open: 单个评估器失败时继续评估其他评估器
                    continue
            
            if visible:
                filtered.append(cap)
            else:
                logger.info(f"Capability {cap.name} filtered: {reasons}")
        
        except Exception as e:
            logger.error(f"Unexpected error filtering {cap.name}: {e}")
            # Fail-open: 完全失败时允许该能力
            filtered.append(cap)
    
    return filtered
```

**关键点**：
- Fail-open 策略：评估失败时允许能力可见，避免治理层故障导致 Agent 完全不可用
- 记录详细错误日志，包含评估器类名和能力名称
- 单个评估器失败不影响其他评估器
- 不中断 Agent Run

### 4.2 Ledger 写入失败处理

**场景**：数据库连接失败或写入超时。

**处理策略**：重试 + 降级到本地日志

**实现**：见 2.4 节 `_flush_batch` 方法

**关键点**：
- 重试 3 次，指数退避（1s, 2s, 3s）
- 最终失败时降级到本地日志文件
- 写入失败不抛出异常，不中断 Agent Run
- 记录详细错误日志，便于事后恢复数据

### 4.3 Router 异常处理

**场景**：配置错误或模型选择失败。

**处理策略**：降级到 default_model

**实现**：
```python
async def select_model(
    self,
    task_type: str,
    context: RunContext
) -> ModelSelection:
    """选择 LLM 模型"""
    try:
        for rule in self.rules:
            if rule['task_type'] == task_type:
                return ModelSelection(
                    model=rule['model'],
                    fallback=rule.get('fallback', [])
                )
        
        return ModelSelection(
            model=self.default_model,
            fallback=[]
        )
    
    except Exception as e:
        logger.error(f"Router error for task_type {task_type}: {e}")
        # 降级到 default_model
        return ModelSelection(
            model=self.default_model,
            fallback=[]
        )
```

**关键点**：
- 配置错误时降级到 default_model
- 记录错误日志，便于调试
- 不中断 Agent Run
- 确保 Agent 始终有可用的模型


---

## 5. 配置

### 5.1 治理层配置（owlclaw.yaml）

```yaml
governance:
  # VisibilityFilter 配置
  visibility:
    # 预算约束
    budget:
      high_cost_threshold: 0.1  # 高成本能力阈值（元/次）
      budget_limits:
        agent_001: 5000  # Agent 月度预算上限（元）
        agent_002: 3000
    
    # 时间约束
    time:
      timezone: Asia/Shanghai
      trading_hours:
        start: "09:30"
        end: "15:00"
        weekdays: [0, 1, 2, 3, 4]  # 周一到周五
    
    # 熔断器
    circuit_breaker:
      failure_threshold: 5  # 连续失败次数阈值
      recovery_timeout: 300  # 恢复超时（秒）
  
  # Ledger 配置
  ledger:
    batch_size: 10  # 批量写入大小
    flush_interval: 5  # 刷新间隔（秒）
  
  # Router 配置
  router:
    default_model: gpt-3.5-turbo
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
```

### 5.2 能力约束配置（SKILL.md frontmatter）

```yaml
---
name: execute_trade
description: 执行交易订单
task_type: trading_decision
owlclaw:
  constraints:
    trading_hours_only: true  # 只在交易时间可用
    max_daily_calls: 50  # 每日最大调用次数
    cooldown_seconds: 60  # 两次调用最小间隔（秒）
---

# Execute Trade

执行交易订单的能力...
```

**关键点**：
- 约束配置在 SKILL.md frontmatter 的 owlclaw.constraints 字段
- 支持多种约束类型组合
- 约束配置对业务代码透明
- 支持热重载（Router 配置）


---

## 6. 集成到 Agent Runtime

### 6.1 初始化

```python
from owlclaw.governance import VisibilityFilter, Ledger, Router
from owlclaw.governance.constraints import (
    BudgetConstraint,
    TimeConstraint,
    RateLimitConstraint,
    CircuitBreakerConstraint
)

class AgentRuntime:
    def __init__(self, config: dict, session_factory):
        # 初始化 Ledger
        self.ledger = Ledger(
            session_factory=session_factory,
            batch_size=config['governance']['ledger']['batch_size'],
            flush_interval=config['governance']['ledger']['flush_interval']
        )
        
        # 初始化 VisibilityFilter
        self.visibility_filter = VisibilityFilter()
        
        # 注册约束评估器
        self.visibility_filter.register_evaluator(
            BudgetConstraint(
                ledger=self.ledger,
                config=config['governance']['visibility']['budget']
            )
        )
        self.visibility_filter.register_evaluator(
            TimeConstraint(
                config=config['governance']['visibility']['time']
            )
        )
        self.visibility_filter.register_evaluator(
            RateLimitConstraint(ledger=self.ledger)
        )
        self.visibility_filter.register_evaluator(
            CircuitBreakerConstraint(
                ledger=self.ledger,
                config=config['governance']['visibility']['circuit_breaker']
            )
        )
        
        # 初始化 Router
        self.router = Router(config['governance']['router'])
    
    async def start(self):
        """启动 Agent Runtime"""
        await self.ledger.start()
    
    async def stop(self):
        """停止 Agent Runtime"""
        await self.ledger.stop()
```

### 6.2 Agent Run 流程集成

```python
async def run_agent(
    self,
    agent_id: str,
    task: str,
    context: RunContext
) -> AgentRunResult:
    """执行 Agent Run"""
    
    # Step 1: 加载身份和知识
    identity = await self.load_identity(agent_id)
    skills = await self.load_skills(agent_id)
    
    # Step 2: 获取所有注册的能力
    all_capabilities = await self.capability_registry.get_all_capabilities()
    
    # Step 3: VisibilityFilter 过滤能力
    visible_capabilities = await self.visibility_filter.filter_capabilities(
        capabilities=all_capabilities,
        agent_id=agent_id,
        context=context
    )
    
    # Step 4: 构建工具列表
    tools = self._build_tools(visible_capabilities)
    
    # Step 5: Function Calling 循环
    messages = [{"role": "user", "content": task}]
    
    while True:
        # Router 选择模型
        current_skill = self._get_current_skill(skills, context)
        model_selection = await self.router.select_model(
            task_type=current_skill.task_type,
            context=context
        )
        
        # 调用 LLM
        try:
            response = await litellm.acompletion(
                model=model_selection.model,
                messages=messages,
                tools=tools
            )
        except Exception as e:
            # 模型失败时尝试降级
            fallback_model = await self.router.handle_model_failure(
                failed_model=model_selection.model,
                task_type=current_skill.task_type,
                error=e,
                fallback_chain=model_selection.fallback
            )
            
            if fallback_model:
                response = await litellm.acompletion(
                    model=fallback_model,
                    messages=messages,
                    tools=tools
                )
            else:
                raise
        
        # 检查是否有 function call
        if not response.choices[0].message.tool_calls:
            break
        
        # 执行能力
        for tool_call in response.choices[0].message.tool_calls:
            start_time = time.time()
            
            try:
                result = await self._execute_capability(
                    capability_name=tool_call.function.name,
                    params=json.loads(tool_call.function.arguments)
                )
                status = 'success'
                error_message = None
            except Exception as e:
                result = {"error": str(e)}
                status = 'failure'
                error_message = str(e)
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Ledger 记录执行
            await self.ledger.record_execution(
                tenant_id=context.tenant_id,
                agent_id=agent_id,
                run_id=context.run_id,
                capability_name=tool_call.function.name,
                task_type=current_skill.task_type,
                input_params=json.loads(tool_call.function.arguments),
                output_result=result,
                decision_reasoning=response.choices[0].message.content or "",
                execution_time_ms=execution_time_ms,
                llm_model=model_selection.model,
                llm_tokens_input=response.usage.prompt_tokens,
                llm_tokens_output=response.usage.completion_tokens,
                estimated_cost=self._estimate_cost(response.usage, model_selection.model),
                status=status,
                error_message=error_message
            )
            
            # 更新熔断器状态
            if status == 'success':
                circuit_breaker = self._get_circuit_breaker_constraint()
                await circuit_breaker.on_capability_success(agent_id, tool_call.function.name)
            
            # 添加结果到消息历史
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result)
            })
    
    return AgentRunResult(
        agent_id=agent_id,
        run_id=context.run_id,
        result=response.choices[0].message.content
    )
```

**关键点**：
- VisibilityFilter 在 LLM 调用前过滤能力
- Router 在每次 LLM 调用时选择模型
- Ledger 在能力执行后异步记录
- 熔断器状态在成功执行后更新
- 模型失败时自动降级
- 整个流程对业务代码透明


---

## 7. 性能优化

### 7.1 约束评估性能

**目标**：约束评估延迟 P95 < 10ms

**优化策略**：

1. **内存缓存**：
```python
class RateLimitConstraint:
    def __init__(self, ledger: Ledger):
        self.ledger = ledger
        self.cache = TTLCache(maxsize=1000, ttl=60)  # 1 分钟 TTL
    
    async def _get_daily_call_count(
        self, tenant_id: str, agent_id: str, capability_name: str
    ) -> int:
        cache_key = f"{tenant_id}:{agent_id}:{capability_name}:{date.today()}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        count = await self._query_from_ledger(tenant_id, agent_id, capability_name)
        self.cache[cache_key] = count
        return count
```

2. **并行评估**：
```python
async def filter_capabilities(
    self,
    capabilities: List[Capability],
    agent_id: str,
    context: RunContext
) -> List[Capability]:
    """并行评估所有约束"""
    tasks = []
    for cap in capabilities:
        task = self._evaluate_capability(cap, agent_id, context)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    filtered = []
    for cap, result in zip(capabilities, results):
        if isinstance(result, Exception):
            logger.error(f"Evaluation error for {cap.name}: {result}")
            filtered.append(cap)  # Fail-open
        elif result:
            filtered.append(cap)
    
    return filtered
```

3. **超时控制**：
```python
async def evaluate(
    self,
    capability: Capability,
    agent_id: str,
    context: RunContext
) -> FilterResult:
    try:
        return await asyncio.wait_for(
            self._do_evaluate(capability, agent_id, context),
            timeout=0.1  # 100ms 超时
        )
    except asyncio.TimeoutError:
        logger.warning(f"Constraint evaluation timeout for {capability.name}")
        return FilterResult(visible=True)  # Fail-open
```

### 7.2 Ledger 写入性能

**目标**：Ledger 异步写入不阻塞 Agent Run

**优化策略**：

1. **批量写入**：见 2.4 节
2. **连接池**：使用 SQLAlchemy 连接池
3. **索引优化**：在高频查询字段上建立索引

```sql
CREATE INDEX idx_ledger_tenant_agent_date 
ON ledger_records (tenant_id, agent_id, created_at DESC);

CREATE INDEX idx_ledger_tenant_capability_date 
ON ledger_records (tenant_id, capability_name, created_at DESC);
```

### 7.3 查询性能

**目标**：Ledger 查询响应时间 P95 < 200ms

**优化策略**：

1. **分页查询**：避免一次性加载大量数据
2. **索引覆盖**：查询字段都在索引中
3. **查询缓存**：对成本统计等高频查询使用缓存

```python
class Ledger:
    def __init__(self, session_factory, batch_size=10, flush_interval=5):
        self.session_factory = session_factory
        self.write_queue = asyncio.Queue()
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._writer_task = None
        self.cost_cache = TTLCache(maxsize=100, ttl=300)  # 5 分钟 TTL
    
    async def get_cost_summary(
        self,
        tenant_id: str,
        agent_id: str,
        start_date: date,
        end_date: date
    ) -> CostSummary:
        cache_key = f"{tenant_id}:{agent_id}:{start_date}:{end_date}"
        
        if cache_key in self.cost_cache:
            return self.cost_cache[cache_key]
        
        summary = await self._query_cost_summary(tenant_id, agent_id, start_date, end_date)
        self.cost_cache[cache_key] = summary
        return summary
```


---

## 8. 安全性

### 8.1 租户隔离

**要求**：所有 Ledger 记录强制 tenant_id 隔离

**实现**：

1. **数据模型**：所有表包含 tenant_id 字段
2. **查询过滤**：所有查询强制 tenant_id 过滤
3. **索引设计**：tenant_id 作为复合索引的第一列

```python
async def query_records(
    self,
    tenant_id: str,
    filters: LedgerQueryFilters
) -> List[LedgerRecord]:
    """查询执行记录"""
    async with self.session_factory() as session:
        # 强制 tenant_id 过滤
        query = select(LedgerRecord).where(
            LedgerRecord.tenant_id == tenant_id
        )
        
        # ... 其他过滤条件
        
        result = await session.execute(query)
        return result.scalars().all()
```

### 8.2 敏感数据脱敏

**要求**：敏感数据（如 API keys）不记录到 Ledger

**实现**：

```python
class Ledger:
    SENSITIVE_KEYS = {'api_key', 'password', 'token', 'secret'}
    
    def _sanitize_params(self, params: dict) -> dict:
        """脱敏敏感参数"""
        sanitized = {}
        for key, value in params.items():
            if any(sensitive in key.lower() for sensitive in self.SENSITIVE_KEYS):
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_params(value)
            else:
                sanitized[key] = value
        return sanitized
    
    async def record_execution(
        self,
        tenant_id: str,
        agent_id: str,
        run_id: str,
        capability_name: str,
        task_type: str,
        input_params: dict,
        output_result: dict,
        # ... 其他参数
    ):
        """记录能力执行（异步写入）"""
        record = LedgerRecord(
            tenant_id=tenant_id,
            agent_id=agent_id,
            run_id=run_id,
            capability_name=capability_name,
            task_type=task_type,
            input_params=self._sanitize_params(input_params),
            output_result=self._sanitize_params(output_result),
            # ... 其他字段
        )
        
        await self.write_queue.put(record)
```

### 8.3 审计日志不可篡改（可选）

**要求**：支持 Ledger 记录的不可篡改性

**实现**：

1. **数据库级别**：使用 PostgreSQL 的 `INSERT ONLY` 表
2. **应用级别**：记录哈希链

```python
class LedgerRecord(Base):
    __tablename__ = 'ledger_records'
    
    # ... 其他字段
    
    prev_record_hash = Column(String(64), nullable=True)
    record_hash = Column(String(64), nullable=False)
    
    def compute_hash(self) -> str:
        """计算记录哈希"""
        import hashlib
        data = f"{self.tenant_id}:{self.agent_id}:{self.run_id}:{self.capability_name}:{self.created_at}"
        return hashlib.sha256(data.encode()).hexdigest()
```


---

## 9. 可扩展性

### 9.1 自定义约束评估器

**要求**：支持自定义约束类型

**实现**：

```python
from owlclaw.governance import ConstraintEvaluator, FilterResult

class CustomConstraint(ConstraintEvaluator):
    """自定义约束评估器"""
    
    async def evaluate(
        self,
        capability: Capability,
        agent_id: str,
        context: RunContext
    ) -> FilterResult:
        # 自定义约束逻辑
        if self._check_custom_condition(capability, agent_id):
            return FilterResult(visible=True)
        else:
            return FilterResult(visible=False, reason="自定义约束不满足")
    
    def _check_custom_condition(
        self, capability: Capability, agent_id: str
    ) -> bool:
        # 实现自定义检查逻辑
        pass

# 注册自定义约束
visibility_filter.register_evaluator(CustomConstraint())
```

### 9.2 自定义路由策略

**要求**：支持自定义路由函数

**实现**：

```python
from typing import Callable

class Router:
    def __init__(self, config: dict):
        self.rules = config.get('rules', [])
        self.default_model = config.get('default_model', 'gpt-3.5-turbo')
        self.custom_selector: Optional[Callable] = None
    
    def set_custom_selector(
        self, 
        selector: Callable[[str, RunContext], ModelSelection]
    ):
        """设置自定义模型选择函数"""
        self.custom_selector = selector
    
    async def select_model(
        self,
        task_type: str,
        context: RunContext
    ) -> ModelSelection:
        """选择 LLM 模型"""
        # 优先使用自定义选择器
        if self.custom_selector:
            try:
                return self.custom_selector(task_type, context)
            except Exception as e:
                logger.error(f"Custom selector error: {e}")
        
        # 降级到配置规则
        for rule in self.rules:
            if rule['task_type'] == task_type:
                return ModelSelection(
                    model=rule['model'],
                    fallback=rule.get('fallback', [])
                )
        
        return ModelSelection(
            model=self.default_model,
            fallback=[]
        )

# 使用自定义路由
def custom_model_selector(task_type: str, context: RunContext) -> ModelSelection:
    # 基于上下文的动态路由
    if context.user_tier == 'premium':
        return ModelSelection(model='gpt-4', fallback=['claude-3-opus'])
    else:
        return ModelSelection(model='gpt-3.5-turbo', fallback=[])

router.set_custom_selector(custom_model_selector)
```

### 9.3 自定义 Ledger 存储后端

**要求**：支持抽象存储接口

**实现**：

```python
from abc import ABC, abstractmethod

class LedgerStorage(ABC):
    """Ledger 存储抽象接口"""
    
    @abstractmethod
    async def write_records(self, records: List[LedgerRecord]):
        """批量写入记录"""
        pass
    
    @abstractmethod
    async def query_records(
        self, tenant_id: str, filters: LedgerQueryFilters
    ) -> List[LedgerRecord]:
        """查询记录"""
        pass

class PostgresLedgerStorage(LedgerStorage):
    """PostgreSQL 存储实现"""
    
    def __init__(self, session_factory):
        self.session_factory = session_factory
    
    async def write_records(self, records: List[LedgerRecord]):
        async with self.session_factory() as session:
            session.add_all(records)
            await session.commit()
    
    async def query_records(
        self, tenant_id: str, filters: LedgerQueryFilters
    ) -> List[LedgerRecord]:
        # PostgreSQL 查询实现
        pass

class S3LedgerStorage(LedgerStorage):
    """S3 存储实现（用于长期归档）"""
    
    def __init__(self, s3_client, bucket: str):
        self.s3_client = s3_client
        self.bucket = bucket
    
    async def write_records(self, records: List[LedgerRecord]):
        # 写入 S3
        pass
    
    async def query_records(
        self, tenant_id: str, filters: LedgerQueryFilters
    ) -> List[LedgerRecord]:
        # 从 S3 查询
        pass

# 使用自定义存储
ledger = Ledger(storage=S3LedgerStorage(s3_client, 'ledger-bucket'))
```


---

## 10. 测试策略

### 10.1 单元测试

**覆盖目标**：> 80%

**测试重点**：

1. **约束评估器**：
```python
@pytest.mark.asyncio
async def test_budget_constraint_blocks_high_cost_capability():
    """测试预算用完时阻止高成本能力"""
    ledger = MockLedger(used_cost=Decimal('5000'))
    constraint = BudgetConstraint(
        ledger=ledger,
        config={'high_cost_threshold': '0.1', 'budget_limits': {'agent_001': 5000}}
    )
    
    capability = Capability(
        name='expensive_capability',
        metadata={'estimated_cost': Decimal('0.2')}
    )
    
    result = await constraint.evaluate(capability, 'agent_001', mock_context)
    
    assert result.visible == False
    assert '预算不足' in result.reason

@pytest.mark.asyncio
async def test_time_constraint_blocks_outside_trading_hours():
    """测试非交易时间阻止能力"""
    constraint = TimeConstraint(config={
        'timezone': 'Asia/Shanghai',
        'trading_hours': {'start': time(9, 30), 'end': time(15, 0), 'weekdays': [0, 1, 2, 3, 4]}
    })
    
    capability = Capability(
        name='trade_capability',
        metadata={'owlclaw': {'constraints': {'trading_hours_only': True}}}
    )
    
    # Mock 当前时间为周六
    with freeze_time('2026-02-21 10:00:00'):  # 周六
        result = await constraint.evaluate(capability, 'agent_001', mock_context)
    
    assert result.visible == False
    assert '非交易日' in result.reason
```

2. **Ledger 异步写入**：
```python
@pytest.mark.asyncio
async def test_ledger_batch_write():
    """测试批量写入"""
    ledger = Ledger(session_factory, batch_size=3, flush_interval=10)
    await ledger.start()
    
    # 写入 5 条记录
    for i in range(5):
        await ledger.record_execution(
            tenant_id="default",
            agent_id='agent_001',
            run_id=f'run_{i}',
            # ... 其他参数
        )
    
    # 等待批量写入
    await asyncio.sleep(0.5)
    
    # 验证数据库中有 3 条记录（第一批）
    records = await query_ledger_records()
    assert len(records) == 3
    
    await ledger.stop()
```

3. **Router 降级链**：
```python
@pytest.mark.asyncio
async def test_router_fallback_chain():
    """测试模型降级链"""
    router = Router(config={
        'default_model': 'gpt-3.5-turbo',
        'rules': [
            {
                'task_type': 'trading_decision',
                'model': 'gpt-4',
                'fallback': ['claude-3-opus', 'gpt-3.5-turbo']
            }
        ]
    })
    
    fallback_chain = ['claude-3-opus', 'gpt-3.5-turbo']
    next_model = await router.handle_model_failure(
        failed_model='gpt-4',
        task_type='trading_decision',
        error=Exception('Rate limit'),
        fallback_chain=fallback_chain
    )
    
    assert next_model == 'claude-3-opus'
```

### 10.2 集成测试

**测试重点**：

1. **治理层协同工作**：
```python
@pytest.mark.asyncio
async def test_governance_layer_integration():
    """测试治理层三个组件协同工作"""
    # 初始化治理层
    ledger = Ledger(session_factory)
    visibility_filter = VisibilityFilter()
    visibility_filter.register_evaluator(BudgetConstraint(ledger, config))
    visibility_filter.register_evaluator(TimeConstraint(config))
    router = Router(config)
    
    await ledger.start()
    
    # 过滤能力
    capabilities = [high_cost_capability, low_cost_capability]
    filtered = await visibility_filter.filter_capabilities(
        capabilities, 'agent_001', context
    )
    
    # 选择模型
    model_selection = await router.select_model('trading_decision', context)
    
    # 记录执行
    await ledger.record_execution(
        tenant_id=context.tenant_id,
        agent_id='agent_001',
        # ... 其他参数
    )
    
    await ledger.stop()
    
    # 验证
    assert len(filtered) == 1  # 只有低成本能力可见
    assert model_selection.model == 'gpt-4'
```

### 10.3 端到端测试

**测试重点**：

1. **完整 Agent Run 流程**：
```python
@pytest.mark.asyncio
async def test_agent_run_with_governance():
    """测试完整 Agent Run 流程"""
    runtime = AgentRuntime(config, session_factory)
    await runtime.start()
    
    result = await runtime.run_agent(
        agent_id='agent_001',
        task='执行交易决策',
        context=RunContext(tenant_id="default", run_id='run_001')
    )
    
    # 验证 Ledger 记录
    records = await runtime.ledger.query_records(
        tenant_id=context.tenant_id,
        filters=LedgerQueryFilters(agent_id='agent_001')
    )
    
    assert len(records) > 0
    assert records[0].task_type == 'trading_decision'
    
    await runtime.stop()
```

### 10.4 性能测试

**测试重点**：

1. **约束评估延迟**：
```python
@pytest.mark.asyncio
async def test_constraint_evaluation_latency():
    """测试约束评估延迟"""
    visibility_filter = VisibilityFilter()
    # 注册所有约束评估器
    
    capabilities = [create_capability() for _ in range(100)]
    
    start_time = time.time()
    filtered = await visibility_filter.filter_capabilities(
        capabilities, 'agent_001', context
    )
    elapsed = time.time() - start_time
    
    # P95 < 10ms
    assert elapsed < 0.01
```

2. **Ledger 写入性能**：
```python
@pytest.mark.asyncio
async def test_ledger_write_performance():
    """测试 Ledger 写入性能"""
    ledger = Ledger(session_factory, batch_size=100)
    await ledger.start()
    
    # 写入 1000 条记录
    start_time = time.time()
    for i in range(1000):
        await ledger.record_execution(
            # ... 参数
        )
    elapsed = time.time() - start_time
    
    # 异步写入不应阻塞
    assert elapsed < 1.0  # < 1 秒
    
    await ledger.stop()
```


---

## 11. 监控和告警

### 11.1 关键指标

**治理层健康指标**：

1. **VisibilityFilter**：
   - 约束评估延迟（P50, P95, P99）
   - 约束评估失败率
   - 能力过滤率（被过滤的能力占比）

2. **Ledger**：
   - 写入队列长度
   - 批量写入延迟
   - 写入失败率
   - 降级到本地日志的次数

3. **Router**：
   - 模型选择延迟
   - 模型降级次数
   - 模型失败率

**实现**：

```python
from prometheus_client import Counter, Histogram, Gauge

# VisibilityFilter 指标
constraint_evaluation_duration = Histogram(
    'governance_constraint_evaluation_duration_seconds',
    'Constraint evaluation duration',
    ['constraint_type']
)

constraint_evaluation_errors = Counter(
    'governance_constraint_evaluation_errors_total',
    'Constraint evaluation errors',
    ['constraint_type']
)

capability_filtered_total = Counter(
    'governance_capability_filtered_total',
    'Capabilities filtered',
    ['reason']
)

# Ledger 指标
ledger_queue_length = Gauge(
    'governance_ledger_queue_length',
    'Ledger write queue length'
)

ledger_write_duration = Histogram(
    'governance_ledger_write_duration_seconds',
    'Ledger batch write duration'
)

ledger_write_errors = Counter(
    'governance_ledger_write_errors_total',
    'Ledger write errors'
)

# Router 指标
model_selection_duration = Histogram(
    'governance_model_selection_duration_seconds',
    'Model selection duration'
)

model_fallback_total = Counter(
    'governance_model_fallback_total',
    'Model fallback count',
    ['from_model', 'to_model', 'task_type']
)
```

### 11.2 告警规则

**Prometheus 告警规则**：

```yaml
groups:
  - name: governance_alerts
    rules:
      # 约束评估延迟过高
      - alert: ConstraintEvaluationSlow
        expr: histogram_quantile(0.95, governance_constraint_evaluation_duration_seconds) > 0.01
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Constraint evaluation is slow"
          description: "P95 constraint evaluation duration is {{ $value }}s"
      
      # Ledger 队列积压
      - alert: LedgerQueueBacklog
        expr: governance_ledger_queue_length > 1000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Ledger queue backlog"
          description: "Ledger queue length is {{ $value }}"
      
      # Ledger 写入失败率过高
      - alert: LedgerWriteFailureHigh
        expr: rate(governance_ledger_write_errors_total[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Ledger write failure rate is high"
          description: "Ledger write failure rate is {{ $value }}/s"
      
      # 模型降级频繁
      - alert: ModelFallbackFrequent
        expr: rate(governance_model_fallback_total[5m]) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Model fallback is frequent"
          description: "Model fallback rate is {{ $value }}/s"
```

### 11.3 日志记录

**日志级别**：

- **INFO**：正常操作（能力过滤、模型选择、Ledger 写入）
- **WARNING**：可恢复错误（约束评估失败、模型降级、Ledger 重试）
- **ERROR**：不可恢复错误（Ledger 写入最终失败、所有模型都失败）

**日志格式**：

```python
import structlog

logger = structlog.get_logger()

# VisibilityFilter 日志
logger.info(
    "capability_filtered",
    capability_name=cap.name,
    agent_id=agent_id,
    reasons=reasons
)

# Router 日志
logger.warning(
    "model_fallback",
    failed_model=failed_model,
    fallback_model=next_model,
    task_type=task_type,
    error=str(error)
)

# Ledger 日志
logger.error(
    "ledger_write_failed",
    batch_size=len(batch),
    attempts=max_retries,
    error=str(e)
)
```


---

## 12. 部署和运维

### 12.1 数据库迁移

**Alembic 迁移脚本**：

```bash
# 生成迁移脚本
alembic revision --autogenerate -m "add ledger_records table"

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

**迁移脚本示例**：

```python
"""add ledger_records table

Revision ID: abc123
Revises: xyz789
Create Date: 2026-02-22 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.create_table(
        'ledger_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('agent_id', sa.String(255), nullable=False, index=True),
        sa.Column('run_id', sa.String(255), nullable=False, index=True),
        sa.Column('capability_name', sa.String(255), nullable=False, index=True),
        sa.Column('task_type', sa.String(100), nullable=False, index=True),
        sa.Column('input_params', postgresql.JSON, nullable=False),
        sa.Column('output_result', postgresql.JSON, nullable=True),
        sa.Column('decision_reasoning', sa.String, nullable=True),
        sa.Column('execution_time_ms', sa.Integer, nullable=False),
        sa.Column('llm_model', sa.String(100), nullable=False),
        sa.Column('llm_tokens_input', sa.Integer, nullable=False),
        sa.Column('llm_tokens_output', sa.Integer, nullable=False),
        sa.Column('estimated_cost', sa.DECIMAL(10, 4), nullable=False),
        sa.Column('status', sa.Enum('success', 'failure', 'timeout', name='execution_status'), nullable=False, index=True),
        sa.Column('error_message', sa.String, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, index=True),
        comment='Agent 能力执行记录，用于审计和成本分析'
    )
    
    # 创建复合索引
    op.create_index(
        'idx_ledger_tenant_agent_date',
        'ledger_records',
        ['tenant_id', 'agent_id', 'created_at']
    )
    
    op.create_index(
        'idx_ledger_tenant_capability_date',
        'ledger_records',
        ['tenant_id', 'capability_name', 'created_at']
    )

def downgrade():
    op.drop_index('idx_ledger_tenant_capability_date', 'ledger_records')
    op.drop_index('idx_ledger_tenant_agent_date', 'ledger_records')
    op.drop_table('ledger_records')
    op.execute('DROP TYPE execution_status')
```

### 12.2 配置管理

**环境变量**：

```bash
# 数据库连接
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/owlclaw

# 治理层配置
GOVERNANCE_LEDGER_BATCH_SIZE=10
GOVERNANCE_LEDGER_FLUSH_INTERVAL=5
GOVERNANCE_BUDGET_HIGH_COST_THRESHOLD=0.1

# 日志级别
LOG_LEVEL=INFO
```

**配置文件热重载**：

```python
import asyncio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ConfigReloadHandler(FileSystemEventHandler):
    def __init__(self, router: Router):
        self.router = router
    
    def on_modified(self, event):
        if event.src_path.endswith('owlclaw.yaml'):
            logger.info("Config file modified, reloading router rules")
            new_config = load_config('owlclaw.yaml')
            self.router.reload_config(new_config['governance']['router'])

# 启动配置监听
observer = Observer()
observer.schedule(ConfigReloadHandler(router), path='.', recursive=False)
observer.start()
```

### 12.3 故障排查

**常见问题**：

1. **Ledger 队列积压**：
   - 检查数据库连接是否正常
   - 检查批量写入延迟是否过高
   - 增加 batch_size 或减少 flush_interval

2. **约束评估延迟过高**：
   - 检查数据库查询性能
   - 检查缓存是否生效
   - 增加约束评估超时时间

3. **模型降级频繁**：
   - 检查主模型的可用性
   - 检查 API 限流配置
   - 调整降级策略

**调试工具**：

```python
# 查看 Ledger 队列状态
async def debug_ledger_queue(ledger: Ledger):
    print(f"Queue size: {ledger.write_queue.qsize()}")
    print(f"Writer task running: {ledger._writer_task and not ledger._writer_task.done()}")

# 查看约束评估器状态
async def debug_visibility_filter(visibility_filter: VisibilityFilter):
    print(f"Registered evaluators: {len(visibility_filter.evaluators)}")
    for evaluator in visibility_filter.evaluators:
        print(f"  - {evaluator.__class__.__name__}")

# 查看 Router 配置
async def debug_router(router: Router):
    print(f"Default model: {router.default_model}")
    print(f"Rules: {len(router.rules)}")
    for rule in router.rules:
        print(f"  - {rule['task_type']} -> {rule['model']}")
```


---

## 13. 未来扩展

### 13.1 分布式追踪

**集成 OpenTelemetry**：

```python
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

tracer = trace.get_tracer(__name__)

class VisibilityFilter:
    async def filter_capabilities(
        self,
        capabilities: List[Capability],
        agent_id: str,
        context: RunContext
    ) -> List[Capability]:
        with tracer.start_as_current_span("filter_capabilities") as span:
            span.set_attribute("agent_id", agent_id)
            span.set_attribute("capability_count", len(capabilities))
            
            filtered = []
            for cap in capabilities:
                with tracer.start_as_current_span(f"evaluate_{cap.name}"):
                    # 评估逻辑
                    pass
            
            span.set_attribute("filtered_count", len(filtered))
            return filtered
```

### 13.2 成本优化建议

**基于 Ledger 数据的成本分析**：

```python
class CostOptimizer:
    def __init__(self, ledger: Ledger):
        self.ledger = ledger
    
    async def analyze_cost_by_capability(
        self, tenant_id: str, agent_id: str, days: int = 30
    ) -> List[CostAnalysis]:
        """分析各能力的成本"""
        start_date = date.today() - timedelta(days=days)
        records = await self.ledger.query_records(
            tenant_id=tenant_id,
            filters=LedgerQueryFilters(
                agent_id=agent_id,
                start_date=start_date
            )
        )
        
        # 按能力聚合成本
        cost_by_capability = {}
        for record in records:
            if record.capability_name not in cost_by_capability:
                cost_by_capability[record.capability_name] = {
                    'total_cost': Decimal('0'),
                    'call_count': 0
                }
            cost_by_capability[record.capability_name]['total_cost'] += record.estimated_cost
            cost_by_capability[record.capability_name]['call_count'] += 1
        
        # 生成优化建议
        suggestions = []
        for capability_name, stats in cost_by_capability.items():
            avg_cost = stats['total_cost'] / stats['call_count']
            if avg_cost > Decimal('0.5'):
                suggestions.append(CostAnalysis(
                    capability_name=capability_name,
                    total_cost=stats['total_cost'],
                    call_count=stats['call_count'],
                    avg_cost=avg_cost,
                    suggestion=f"考虑优化 {capability_name}，平均成本较高（{avg_cost} 元/次）"
                ))
        
        return suggestions
```

### 13.3 智能预算分配

**基于历史数据的预算预测**：

```python
class BudgetPredictor:
    def __init__(self, ledger: Ledger):
        self.ledger = ledger
    
    async def predict_monthly_cost(
        self, tenant_id: str, agent_id: str
    ) -> Decimal:
        """预测月度成本"""
        # 获取过去 7 天的成本
        start_date = date.today() - timedelta(days=7)
        cost_summary = await self.ledger.get_cost_summary(
            tenant_id=tenant_id,
            agent_id=agent_id,
            start_date=start_date,
            end_date=date.today()
        )
        
        # 计算日均成本
        daily_avg = cost_summary.total_cost / 7
        
        # 预测月度成本（考虑工作日）
        working_days_per_month = 22
        predicted_cost = daily_avg * working_days_per_month
        
        return predicted_cost
    
    async def suggest_budget_limit(
        self, tenant_id: str, agent_id: str, buffer: float = 1.2
    ) -> Decimal:
        """建议预算上限"""
        predicted_cost = await self.predict_monthly_cost(tenant_id, agent_id)
        suggested_limit = predicted_cost * Decimal(str(buffer))
        
        return suggested_limit
```

### 13.4 多租户成本分摊

**基于使用量的成本分摊**：

```python
class CostAllocation:
    def __init__(self, ledger: Ledger):
        self.ledger = ledger
    
    async def allocate_shared_costs(
        self, tenant_ids: List[str], shared_cost: Decimal, month: date
    ) -> Dict[str, Decimal]:
        """按使用量分摊共享成本"""
        # 获取各租户的使用量
        usage_by_tenant = {}
        for tenant_id in tenant_ids:
            records = await self.ledger.query_records(
                tenant_id=tenant_id,
                filters=LedgerQueryFilters(
                    start_date=month.replace(day=1),
                    end_date=month
                )
            )
            usage_by_tenant[tenant_id] = len(records)
        
        # 计算总使用量
        total_usage = sum(usage_by_tenant.values())
        
        # 按比例分摊成本
        allocated_costs = {}
        for tenant_id, usage in usage_by_tenant.items():
            ratio = Decimal(usage) / Decimal(total_usage)
            allocated_costs[tenant_id] = shared_cost * ratio
        
        return allocated_costs
```

---

## 14. 参考文档

- `.kiro/specs/governance/requirements.md` — 治理层需求文档
- `.kiro/specs/governance/tasks.md` — 治理层任务清单
- `.kiro/specs/agent-runtime/design.md` — Agent 运行时设计
- `.kiro/specs/database-core/design.md` — 数据库核心设计
- `docs/ARCHITECTURE_ANALYSIS.md` §4 — 治理层架构分析
- Agent Skills 规范（agentskills.io）— SKILL.md frontmatter 格式

---

**维护者**：OwlClaw 开发团队  
**最后更新**：2026-02-22  
**版本**：1.0.0

