# Design: Governance Layer

> **目标**：为 OwlClaw Agent 提供生产级治理能力的技术设计  
> **状态**：设计中  
> **最后更新**：2026-02-11

---

## 1. 架构设计

### 1.1 整体架构

`
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
`

### 1.2 核心组件

#### 组件 1：VisibilityFilter（可见性过滤器）

**职责**：在 Agent 看到工具列表之前，根据约束条件过滤能力。

**接口定义**：
`python
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
        \"\"\"注册约束评估器\"\"\"
        self.evaluators.append(evaluator)
    
    async def filter_capabilities(
        self,
        capabilities: List[Capability],
        agent_id: str,
        context: RunContext
    ) -> List[Capability]:
        \"\"\"
        过滤能力列表
        
        对每个能力应用所有约束评估器，只返回所有约束都通过的能力
        \"\"\"
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
                logger.info(f\"Capability {cap.name} filtered: {reasons}\")
        
        return filtered
`

#### 组件 2：Ledger（执行记录）

**职责**：记录每次能力执行的完整上下文，支持查询和分析。

**接口定义**：
`python
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

class Ledger:
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.write_queue = asyncio.Queue()
    
    async def record_execution(
        self,
        tenant_id: UUID,
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
        \"\"\"
        记录能力执行（异步写入）
        \"\"\"
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
        tenant_id: UUID,
        filters: LedgerQueryFilters
    ) -> List[LedgerRecord]:
        \"\"\"查询执行记录\"\"\"
        async with self.session_factory() as session:
            query = select(LedgerRecord).where(
                LedgerRecord.tenant_id == tenant_id
            )
            
            if filters.agent_id:
                query = query.where(LedgerRecord.agent_id == filters.agent_id)
            if filters.start_date:
                query = query.where(LedgerRecord.created_at >= filters.start_date)
            if filters.end_date:
                query = query.where(LedgerRecord.created_at <= filters.end_date)
            
            result = await session.execute(query)
            return result.scalars().all()
`

#### 组件 3：Router（模型路由）

**职责**：根据 task_type 选择合适的 LLM 模型，支持降级链。

**接口定义**：
`python
@dataclass
class ModelSelection:
    model: str
    fallback: List[str]

class Router:
    def __init__(self, config: dict):
        self.rules = config.get('rules', [])
        self.default_model = config.get('default_model', 'gpt-3.5-turbo')
    
    async def select_model(
        self,
        task_type: str,
        context: RunContext
    ) -> ModelSelection:
        \"\"\"
        选择 LLM 模型
        \"\"\"
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
        \"\"\"
        处理模型失败，返回降级模型
        \"\"\"
        if not fallback_chain:
            return None
        
        next_model = fallback_chain[0]
        logger.warning(
            f\"Model {failed_model} failed for task_type {task_type}, \"
            f\"falling back to {next_model}\"
        )
        
        return next_model
`

---

## 2. 实现细节

### 2.1 文件结构

`
owlclaw/
├── governance/
│   ├── __init__.py
│   ├── visibility.py          # VisibilityFilter + 约束评估器
│   ├── ledger.py              # Ledger + LedgerRecord 模型
│   ├── router.py              # Router + 路由规则
│   └── constraints/
│       ├── __init__.py
│       ├── budget.py          # BudgetConstraint
│       ├── time.py            # TimeConstraint
│       ├── rate_limit.py      # RateLimitConstraint
│       └── circuit_breaker.py # CircuitBreakerConstraint
`


### 2.2 BudgetConstraint 实现

**当前问题**：Agent 无限制调用高成本 LLM，导致预算超支。

**解决方案**：在能力可见性过滤阶段，检查 Agent 的月度预算使用情况，如果预算用完则隐藏高成本能力。

**实现**：
`python
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
                    reason=f\"预算不足（已用 {used_cost}，上限 {budget_limit}）\"
                )
        
        return FilterResult(visible=True)
    
    def _estimate_capability_cost(self, capability: Capability) -> Decimal:
        \"\"\"估算能力的单次调用成本\"\"\"
        # 从历史记录或配置中获取平均成本
        return capability.metadata.get('estimated_cost', Decimal('0.05'))
`

**关键点**：
- 使用 Ledger 统计当月成本，避免重复计算
- 高成本阈值可配置（默认 ¥0.1/次）
- 预算用完时只隐藏高成本能力，保留低成本能力

### 2.3 TimeConstraint 实现

**当前问题**：某些能力（如交易操作）只应在特定时间可用。

**解决方案**：检查当前时间是否符合能力的时间约束。

**实现**：
`python
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
                    reason=\"非交易日\"
                )
            
            # 检查是否交易时间
            current_time = now.time()
            if not (self.trading_hours['start'] <= current_time <= self.trading_hours['end']):
                return FilterResult(
                    visible=False,
                    reason=f\"非交易时间（交易时间：{self.trading_hours['start']}-{self.trading_hours['end']}）\"
                )
        
        return FilterResult(visible=True)
`

**关键点**：
- 支持时区配置
- 支持自定义交易时间和工作日
- 可扩展支持节假日规则

### 2.4 RateLimitConstraint 实现

**当前问题**：Agent 可能过度调用某些能力，导致外部 API 限流或成本过高。

**解决方案**：检查能力的调用频率，超过限制时暂时隐藏。

**实现**：
`python
from datetime import datetime, timedelta

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
                    reason=f\"超过每日调用次数限制（{count}/{max_daily_calls}）\"
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
                        reason=f\"冷却中（还需等待 {remaining} 秒）\"
                    )
        
        return FilterResult(visible=True)
    
    async def _get_daily_call_count(
        self, tenant_id: UUID, agent_id: str, capability_name: str
    ) -> int:
        \"\"\"获取今日调用次数（带缓存）\"\"\"
        # 从缓存或 Ledger 查询
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
        self, tenant_id: UUID, agent_id: str, capability_name: str
    ) -> Optional[datetime]:
        \"\"\"获取上次调用时间\"\"\"
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
`

**关键点**：
- 使用缓存减少数据库查询
- 支持每日调用次数和冷却时间两种限制
- 限制重置时间自动处理（每日 0 点）

### 2.5 CircuitBreakerConstraint 实现

**当前问题**：能力连续失败时，继续调用会浪费资源。

**解决方案**：实现熔断器模式，连续失败达到阈值时自动熔断。

**实现**：
`python
from enum import Enum

class CircuitState(Enum):
    CLOSED = \"closed\"      # 正常状态
    OPEN = \"open\"          # 熔断状态
    HALF_OPEN = \"half_open\" # 半开状态（尝试恢复）

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
                    reason=\"熔断中（能力连续失败）\"
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
                reason=f\"熔断器打开（连续失败 {recent_failures} 次）\"
            )
        
        return FilterResult(visible=True)
    
    async def _get_recent_failures(
        self, tenant_id: UUID, agent_id: str, capability_name: str
    ) -> int:
        \"\"\"获取最近的连续失败次数\"\"\"
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
        \"\"\"能力执行成功时调用，重置熔断器\"\"\"
        cache_key = (agent_id, capability_name)
        if cache_key in self.circuit_states:
            self.circuit_states[cache_key] = (CircuitState.CLOSED, None)
`

**关键点**：
- 实现标准的熔断器模式（CLOSED → OPEN → HALF_OPEN → CLOSED）
- 连续失败次数可配置
- 恢复超时可配置
- 成功执行后自动重置熔断器


### 2.6 LedgerRecord 数据模型

**实现**：
`python
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
`

**关键点**：
- 所有表必须包含 tenant_id（租户隔离）
- 关键字段建立索引（tenant_id, agent_id, capability_name, created_at）
- input_params 和 output_result 使用 JSON 类型
- estimated_cost 使用 DECIMAL 类型保证精度

### 2.7 Ledger 异步写入队列

**当前问题**：同步写入 Ledger 会阻塞 Agent Run。

**解决方案**：使用异步队列批量写入。

**实现**：
`python
import asyncio
from typing import List

class Ledger:
    def __init__(self, session_factory, batch_size=10, flush_interval=5):
        self.session_factory = session_factory
        self.write_queue = asyncio.Queue()
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._writer_task = None
    
    async def start(self):
        \"\"\"启动后台写入任务\"\"\"
        self._writer_task = asyncio.create_task(self._background_writer())
    
    async def stop(self):
        \"\"\"停止后台写入任务\"\"\"
        if self._writer_task:
            self._writer_task.cancel()
            await self._writer_task
    
    async def _background_writer(self):
        \"\"\"后台批量写入任务\"\"\"
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
            
            except Exception as e:
                logger.error(f\"Ledger writer error: {e}\")
    
    async def _flush_batch(self, batch: List[LedgerRecord]):
        \"\"\"批量写入数据库\"\"\"
        try:
            async with self.session_factory() as session:
                session.add_all(batch)
                await session.commit()
                logger.info(f\"Flushed {len(batch)} ledger records\")
        except Exception as e:
            logger.error(f\"Failed to flush ledger batch: {e}\")
            # 写入失败时记录到本地日志文件
            await self._write_to_fallback_log(batch)
    
    async def _write_to_fallback_log(self, batch: List[LedgerRecord]):
        \"\"\"写入失败时的降级方案\"\"\"
        import json
        with open('ledger_fallback.log', 'a') as f:
            for record in batch:
                f.write(json.dumps({
                    'tenant_id': str(record.tenant_id),
                    'agent_id': record.agent_id,
                    'capability_name': record.capability_name,
                    'created_at': record.created_at.isoformat()
                }) + '\\n')
`

**关键点**：
- 批量写入减少数据库连接开销
- 超时自动刷新避免数据积压
- 写入失败时降级到本地日志

---

## 3. 数据流

### 3.1 Agent Run 完整流程

`
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
│  • 更新预算使用量                                                │
│  • 更新调用计数                                                  │
│  • 更新熔断器状态                                                │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 9: Agent Run 完成                                          │
└─────────────────────────────────────────────────────────────────┘
`

**关键点**：
- VisibilityFilter 在 LLM 调用之前执行
- Router 在每次 LLM 调用时选择模型
- Ledger 记录在能力执行之后异步写入
- 约束状态在 Ledger 记录后更新


### 3.2 模型降级流程

`
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
`

---

## 4. 错误处理

### 4.1 VisibilityFilter 异常处理

**场景**：约束评估器抛出异常（如数据库连接失败）。

**处理**：
`python
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
            for evaluator in self.evaluators:
                result = await evaluator.evaluate(cap, agent_id, context)
                if not result.visible:
                    visible = False
                    break
            
            if visible:
                filtered.append(cap)
        
        except Exception as e:
            logger.error(f\"Constraint evaluation error for {cap.name}: {e}\")
            # Fail-open: 评估失败时允许该能力
            filtered.append(cap)
    
    return filtered
`

**关键点**：
- Fail-open 策略：评估失败时允许能力可见
- 记录错误日志便于调试
- 不中断 Agent Run

### 4.2 Ledger 写入失败处理

**场景**：数据库连接失败或写入超时。

**处理**：
`python
async def _flush_batch(self, batch: List[LedgerRecord]):
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            async with self.session_factory() as session:
                session.add_all(batch)
                await session.commit()
                return
        
        except Exception as e:
            logger.warning(f\"Ledger write attempt {attempt + 1} failed: {e}\")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay * (attempt + 1))
            else:
                logger.error(f\"Ledger write failed after {max_retries} attempts\")
                await self._write_to_fallback_log(batch)
`

**关键点**：
- 重试 3 次，指数退避
- 最终失败时降级到本地日志
- 不抛出异常，不影响 Agent Run

### 4.3 Router 异常处理

**场景**：路由配置错误或模型不可用。

**处理**：
`python
async def select_model(
    self,
    task_type: str,
    context: RunContext
) -> ModelSelection:
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
        logger.error(f\"Router error: {e}\")
        # 降级到默认模型
        return ModelSelection(
            model=self.default_model,
            fallback=[]
        )
`

**关键点**：
- 异常时降级到 default_model
- 记录错误日志
- 保证 Agent Run 可以继续

---

## 5. 配置

### 5.1 配置文件格式

`yaml
# owlclaw.yaml

governance:
  # VisibilityFilter 配置
  visibility:
    budget:
      high_cost_threshold: 0.1  # 高成本能力阈值（元/次）
      limits:
        agent_001: 5000  # Agent 月度预算（元）
        agent_002: 3000
    
    time:
      timezone: Asia/Shanghai
      trading_hours:
        start: \"09:30\"
        end: \"15:00\"
        weekdays: [0, 1, 2, 3, 4]  # 周一到周五
    
    rate_limit:
      # 全局默认值，可在 SKILL.md 中覆盖
      default_max_daily_calls: 100
      default_cooldown_seconds: 60
    
    circuit_breaker:
      failure_threshold: 5  # 连续失败次数阈值
      recovery_timeout: 300  # 熔断恢复时间（秒）
  
  # Ledger 配置
  ledger:
    batch_size: 10  # 批量写入大小
    flush_interval: 5  # 刷新间隔（秒）
    fallback_log_path: \"./ledger_fallback.log\"
  
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
`

### 5.2 SKILL.md 中的约束配置

`yaml
---
name: entry-monitor
description: 检查持仓股票的入场机会
metadata:
  author: mionyee-team
  version: \"1.0\"
owlclaw:
  task_type: trading_decision
  constraints:
    trading_hours_only: true
    max_daily_calls: 50
    cooldown_seconds: 300
---
`

---

## 6. 测试策略

### 6.1 单元测试

**BudgetConstraint 测试**：
`python
import pytest
from decimal import Decimal

@pytest.mark.asyncio
async def test_budget_constraint_blocks_high_cost_capability():
    # Arrange
    ledger = MockLedger(used_cost=Decimal('4900'))
    constraint = BudgetConstraint(ledger, {
        'high_cost_threshold': '0.1',
        'budget_limits': {'agent_001': '5000'}
    })
    
    high_cost_cap = Capability(
        name='expensive_analysis',
        metadata={'estimated_cost': Decimal('0.5')}
    )
    
    # Act
    result = await constraint.evaluate(
        high_cost_cap,
        'agent_001',
        RunContext(tenant_id=uuid.uuid4())
    )
    
    # Assert
    assert result.visible == False
    assert \"预算不足\" in result.reason

@pytest.mark.asyncio
async def test_budget_constraint_allows_low_cost_capability():
    # Arrange
    ledger = MockLedger(used_cost=Decimal('4900'))
    constraint = BudgetConstraint(ledger, {
        'high_cost_threshold': '0.1',
        'budget_limits': {'agent_001': '5000'}
    })
    
    low_cost_cap = Capability(
        name='simple_query',
        metadata={'estimated_cost': Decimal('0.01')}
    )
    
    # Act
    result = await constraint.evaluate(
        low_cost_cap,
        'agent_001',
        RunContext(tenant_id=uuid.uuid4())
    )
    
    # Assert
    assert result.visible == True
`

### 6.2 集成测试

**VisibilityFilter 集成测试**：
`python
@pytest.mark.asyncio
async def test_visibility_filter_applies_all_constraints():
    # Arrange
    ledger = create_test_ledger()
    filter = VisibilityFilter()
    filter.register_evaluator(BudgetConstraint(ledger, budget_config))
    filter.register_evaluator(TimeConstraint(time_config))
    filter.register_evaluator(RateLimitConstraint(ledger))
    
    capabilities = [
        create_test_capability('cap1', trading_hours_only=True),
        create_test_capability('cap2', max_daily_calls=10),
        create_test_capability('cap3')
    ]
    
    # Act
    filtered = await filter.filter_capabilities(
        capabilities,
        'agent_001',
        create_test_context()
    )
    
    # Assert
    assert len(filtered) > 0
    # 验证过滤逻辑
`

### 6.3 端到端测试

**完整 Agent Run 测试**：
`python
@pytest.mark.asyncio
async def test_agent_run_with_governance():
    # Arrange
    app = create_test_app_with_governance()
    
    # Act
    result = await app.run_agent(
        agent_id='test_agent',
        trigger_event={'type': 'cron', 'focus': 'check_opportunities'}
    )
    
    # Assert
    assert result.status == 'completed'
    
    # 验证 Ledger 记录
    records = await app.ledger.query_records(
        tenant_id=test_tenant_id,
        filters=LedgerQueryFilters(agent_id='test_agent')
    )
    assert len(records) > 0
    
    # 验证约束生效
    # ...
`

---

## 7. 迁移计划

### 7.1 Phase 1：核心基础设施（3 天）

- [ ] 创建 governance 包结构
- [ ] 实现 VisibilityFilter 基类和约束评估器接口
- [ ] 实现 Ledger 基类和 LedgerRecord 模型
- [ ] 实现 Router 基类
- [ ] 编写单元测试

### 7.2 Phase 2：约束评估器实现（3 天）

- [ ] 实现 BudgetConstraint
- [ ] 实现 TimeConstraint
- [ ] 实现 RateLimitConstraint
- [ ] 实现 CircuitBreakerConstraint
- [ ] 编写单元测试和集成测试

### 7.3 Phase 3：Ledger 和 Router 实现（2 天）

- [ ] 实现 Ledger 异步写入队列
- [ ] 实现 Ledger 查询接口
- [ ] 实现 Router 模型选择和降级
- [ ] 编写单元测试

### 7.4 Phase 4：集成到 Agent Runtime（2 天）

- [ ] 在 Agent Runtime 中集成 VisibilityFilter
- [ ] 在 Agent Runtime 中集成 Router
- [ ] 在 Agent Runtime 中集成 Ledger
- [ ] 编写端到端测试

### 7.5 Phase 5：数据库迁移和验证（1 天）

- [ ] 创建 Alembic 迁移脚本
- [ ] 运行迁移创建 ledger_records 表
- [ ] 验证 tenant_id 隔离
- [ ] 性能测试

---

## 8. 风险与缓解

### 8.1 风险：约束评估延迟

**影响**：P95 延迟 > 10ms 会影响 Agent Run 性能。

**缓解**：
- 使用内存缓存（预算、调用计数）
- 约束评估并行执行
- 设置评估超时

### 8.2 风险：Ledger 队列积压

**影响**：写入队列积压导致内存占用过高。

**缓解**：
- 监控队列长度
- 队列满时触发告警
- 动态调整 batch_size 和 flush_interval

### 8.3 风险：模型降级导致决策质量下降

**影响**：降级到低质量模型可能导致错误决策。

**缓解**：
- 记录降级事件到 Ledger
- 提供降级告警
- 支持禁止降级配置

---

## 9. 正确性属性

### 属性 1：预算约束的单调性

**属性**：在同一个月内，Agent 的已用成本单调递增。

**验证**：
`python
# Property-based test
@given(
    agent_id=st.text(min_size=1),
    executions=st.lists(st.decimals(min_value=0, max_value=10), min_size=1)
)
def test_budget_monotonic(agent_id, executions):
    ledger = Ledger()
    costs = []
    
    for cost in executions:
        ledger.record_execution(..., estimated_cost=cost)
        summary = ledger.get_cost_summary(agent_id, this_month)
        costs.append(summary.total_cost)
    
    # 验证单调递增
    assert all(costs[i] <= costs[i+1] for i in range(len(costs)-1))
`

### 属性 2：时间约束的对称性

**属性**：如果时间 T 在交易时间内，则 T+1秒 也应该在交易时间内（除非跨越边界）。

**验证**：Property-based test 验证时间约束的连续性。

### 属性 3：频率限制的重置性

**属性**：每日 0 点后，调用计数应重置为 0。

**验证**：
`python
def test_rate_limit_resets_daily():
    constraint = RateLimitConstraint(ledger)
    
    # 今天调用 50 次
    for _ in range(50):
        constraint.evaluate(cap, agent_id, today_context)
    
    # 明天应该重置
    result = constraint.evaluate(cap, agent_id, tomorrow_context)
    assert result.visible == True
`

### 属性 4：熔断器的状态转换

**属性**：熔断器状态转换遵循 CLOSED → OPEN → HALF_OPEN → CLOSED 循环。

**验证**：状态机测试验证所有合法转换。

### 属性 5：Ledger 记录的完整性

**属性**：每次能力执行都应该有对应的 Ledger 记录。

**验收**：
`python
def test_ledger_completeness():
    # 执行 N 次能力
    for _ in range(N):
        agent.execute_capability(cap)
    
    # 查询 Ledger
    records = ledger.query_records(agent_id)
    
    # 验证记录数量
    assert len(records) == N
`

### 属性 6：Router 降级链的有序性

**属性**：模型降级按 fallback 列表顺序进行。

**验证**：
`python
def test_router_fallback_order():
    router = Router(config)
    selection = router.select_model('trading_decision')
    
    # 模拟主模型失败
    next_model = router.handle_model_failure(
        selection.model, 'trading_decision', error, selection.fallback
    )
    
    # 验证返回第一个 fallback
    assert next_model == selection.fallback[0]
`

### 属性 7：tenant_id 隔离性

**属性**：不同 tenant 的 Ledger 记录完全隔离。

**验证**：
`python
def test_tenant_isolation():
    tenant1_records = ledger.query_records(tenant_id=tenant1)
    tenant2_records = ledger.query_records(tenant_id=tenant2)
    
    # 验证没有交叉
    tenant1_ids = {r.id for r in tenant1_records}
    tenant2_ids = {r.id for r in tenant2_records}
    assert tenant1_ids.isdisjoint(tenant2_ids)
`

---

## 10. 参考文档

- docs/ARCHITECTURE_ANALYSIS.md §4（治理层设计）
- docs/DATABASE_ARCHITECTURE.md（数据库架构）
- .cursor/rules/owlclaw_database.mdc（数据库编码规范）
- .kiro/specs/agent-runtime/design.md（Agent 运行时设计）
- .kiro/specs/database-core/design.md（数据库核心设计）
- Circuit Breaker Pattern（Martin Fowler）
- Rate Limiting Patterns（NGINX）

---

**维护者**：OwlClaw 开发团队  
**最后更新**：2026-02-11
