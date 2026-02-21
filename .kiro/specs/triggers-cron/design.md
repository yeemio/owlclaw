# Design: Cron Triggers

> **目标**：为 OwlClaw Agent 提供 Cron 定时触发能力的详细设计  
> **版本**：v1.0  
> **状态**：Draft

---

## 1. 设计概览

### 1.1 核心理念

Cron Triggers 将传统的定时任务调度与 Agent 自主决策能力结合：

- **声明式配置**：通过 `@app.cron` 装饰器声明定时任务
- **持久化调度**：基于 Hatchet 的 Cron 支持，保证任务不丢失
- **Agent 决策**：触发后由 Agent 通过 function calling 自主决策
- **治理集成**：自动应用 governance 约束和记录
- **渐进式迁移**：支持 fallback handler，平滑从传统 cron 迁移

### 1.2 架构定位

```
┌─────────────────────────────────────────────────────────────┐
│                      OwlClaw Application                     │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  @app.cron(expression="0 * * * *")                     │ │
│  │  async def hourly_check(): ...                         │ │
│  └────────────────────────────────────────────────────────┘ │
└───────────────────────┬─────────────────────────────────────┘
                        │ 注册
                        ↓
┌─────────────────────────────────────────────────────────────┐
│                   Triggers Layer (本设计)                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  CronTriggerRegistry                                 │  │
│  │  - 解析 cron 表达式                                   │  │
│  │  - 注册到 Hatchet                                     │  │
│  │  - 管理触发器生命周期                                 │  │
│  └──────────────────────────────────────────────────────┘  │
└───────────────────────┬─────────────────────────────────────┘
                        │ 调度
                        ↓
┌─────────────────────────────────────────────────────────────┐
│                  Hatchet Integration Layer                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  @hatchet_client.workflow(on_cron="0 * * * *")      │  │
│  │  class CronWorkflow: ...                             │  │
│  └──────────────────────────────────────────────────────┘  │
└───────────────────────┬─────────────────────────────────────┘
                        │ 触发
                        ↓
┌─────────────────────────────────────────────────────────────┐
│                      Agent Runtime                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  agent_runtime.trigger_event(                        │  │
│  │      event_name="hourly_check",                      │  │
│  │      focus="inventory_monitor"                       │  │
│  │  )                                                    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```


### 1.3 设计目标

1. **简单易用**：开发者只需一个装饰器即可注册 Cron 任务
2. **可靠持久**：基于 Hatchet 保证任务不丢失，支持故障恢复
3. **智能决策**：Agent 根据上下文自主决策，而非执行固定脚本
4. **治理集成**：自动应用成本、时间、频率约束
5. **平滑迁移**：支持 fallback handler，降低迁移风险

---

## 2. 数据模型

### 2.1 CronTrigger 配置

```python
from dataclasses import dataclass
from typing import Optional, Callable, List

@dataclass
class CronTriggerConfig:
    """Cron 触发器配置"""
    
    # 基本信息
    event_name: str                    # 事件名称（唯一标识）
    expression: str                    # Cron 表达式（5 字段）
    description: Optional[str] = None  # 任务描述
    
    # Agent 配置
    focus: Optional[str] = None        # Focus 标识符（引导 Agent 关注）
    
    # Fallback 配置
    fallback_handler: Optional[Callable] = None  # Fallback 函数
    fallback_strategy: str = "on_failure"        # 触发策略：on_failure/always/never
    migration_weight: float = 1.0                # Agent 决策权重（0-1）
    
    # 治理配置
    max_cost_per_run: Optional[float] = None     # 单次执行成本上限（USD）
    max_daily_cost: Optional[float] = None       # 每日总成本上限（USD）
    max_duration: Optional[int] = None           # 最大执行时长（秒）
    cooldown_seconds: int = 0                    # 冷却时间（秒）
    max_daily_runs: Optional[int] = None         # 每日最大执行次数
    
    # 可靠性配置
    retry_on_failure: bool = True                # 失败时是否重试
    max_retries: int = 3                         # 最大重试次数
    retry_delay_seconds: int = 60                # 重试延迟（秒）
    
    # 元数据
    priority: int = 0                            # 优先级（数字越大优先级越高）
    tags: List[str] = None                       # 标签（用于分组和查询）
    enabled: bool = True                         # 是否启用
```

### 2.2 CronExecution 记录

```python
from datetime import datetime
from enum import Enum

class ExecutionStatus(str, Enum):
    """执行状态"""
    PENDING = "pending"       # 等待执行
    RUNNING = "running"       # 执行中
    SUCCESS = "success"       # 成功
    FAILED = "failed"         # 失败
    SKIPPED = "skipped"       # 跳过（约束不满足）
    FALLBACK = "fallback"     # 使用 fallback

@dataclass
class CronExecution:
    """Cron 执行记录"""
    
    # 基本信息
    execution_id: str                  # 执行 ID（UUID）
    event_name: str                    # 事件名称
    triggered_at: datetime             # 触发时间
    
    # 执行信息
    status: ExecutionStatus            # 执行状态
    started_at: Optional[datetime]     # 开始时间
    completed_at: Optional[datetime]   # 完成时间
    duration_seconds: Optional[float]  # 执行时长
    
    # Agent 信息
    agent_run_id: Optional[str]        # Agent Run ID
    decision_mode: str                 # 决策模式：agent/fallback
    llm_calls: int = 0                 # LLM 调用次数
    cost_usd: float = 0.0              # 成本（USD）
    
    # 治理信息
    governance_checks: dict            # 约束检查结果
    skip_reason: Optional[str]         # 跳过原因
    
    # 错误信息
    error_message: Optional[str]       # 错误信息
    error_traceback: Optional[str]     # 错误堆栈
    retry_count: int = 0               # 重试次数
    
    # 元数据
    context: dict                      # 触发上下文
```


---

## 3. 核心组件设计

### 3.1 CronTriggerRegistry

**职责**：管理所有 Cron 触发器的注册、配置和生命周期。

```python
from typing import Dict, List, Optional
from owlclaw.integrations.hatchet import hatchet_client

class CronTriggerRegistry:
    """Cron 触发器注册表"""
    
    def __init__(self, app: "OwlClawApp"):
        self.app = app
        self._triggers: Dict[str, CronTriggerConfig] = {}
        self._hatchet_workflows: Dict[str, type] = {}
    
    def register(
        self,
        event_name: str,
        expression: str,
        focus: Optional[str] = None,
        fallback_handler: Optional[Callable] = None,
        **kwargs
    ) -> None:
        """
        注册 Cron 触发器
        
        Args:
            event_name: 事件名称（唯一标识）
            expression: Cron 表达式
            focus: Focus 标识符
            fallback_handler: Fallback 函数
            **kwargs: 其他配置参数
        
        Raises:
            ValueError: 如果 event_name 已存在或 expression 非法
        """
        # 1. 验证参数
        if event_name in self._triggers:
            raise ValueError(f"Cron trigger '{event_name}' already registered")
        
        if not self._validate_cron_expression(expression):
            raise ValueError(f"Invalid cron expression: {expression}")
        
        # 2. 创建配置
        config = CronTriggerConfig(
            event_name=event_name,
            expression=expression,
            focus=focus,
            fallback_handler=fallback_handler,
            **kwargs
        )
        
        # 3. 注册到 Hatchet
        workflow_class = self._create_hatchet_workflow(config)
        self._hatchet_workflows[event_name] = workflow_class
        
        # 4. 保存配置
        self._triggers[event_name] = config
        
        logger.info(f"Registered cron trigger: {event_name} ({expression})")
    
    def _validate_cron_expression(self, expression: str) -> bool:
        """验证 Cron 表达式"""
        try:
            # 使用 croniter 验证
            from croniter import croniter
            croniter(expression)
            return True
        except Exception as e:
            logger.error(f"Invalid cron expression: {expression}, error: {e}")
            return False
    
    def _create_hatchet_workflow(self, config: CronTriggerConfig) -> type:
        """创建 Hatchet Workflow"""
        
        # 动态创建 Workflow 类
        @hatchet_client.workflow(
            name=f"cron_{config.event_name}",
            on_cron=config.expression
        )
        class CronWorkflow:
            
            @hatchet_client.step()
            async def trigger_agent(self, context):
                """触发 Agent Run"""
                
                # 1. 创建执行记录
                execution = CronExecution(
                    execution_id=str(uuid.uuid4()),
                    event_name=config.event_name,
                    triggered_at=datetime.utcnow(),
                    status=ExecutionStatus.PENDING,
                    context={
                        "trigger_type": "cron",
                        "expression": config.expression,
                        "focus": config.focus,
                    }
                )
                
                try:
                    # 2. 治理检查
                    if not await self._check_governance(config, execution):
                        execution.status = ExecutionStatus.SKIPPED
                        await self._record_execution(execution)
                        return
                    
                    # 3. 决定执行模式（Agent vs Fallback）
                    use_agent = self._should_use_agent(config)
                    execution.decision_mode = "agent" if use_agent else "fallback"
                    
                    # 4. 执行
                    execution.status = ExecutionStatus.RUNNING
                    execution.started_at = datetime.utcnow()
                    
                    if use_agent:
                        await self._execute_agent(config, execution)
                    else:
                        await self._execute_fallback(config, execution)
                    
                    execution.status = ExecutionStatus.SUCCESS
                    
                except Exception as e:
                    execution.status = ExecutionStatus.FAILED
                    execution.error_message = str(e)
                    execution.error_traceback = traceback.format_exc()
                    
                    # 5. 失败处理
                    await self._handle_failure(config, execution)
                
                finally:
                    # 6. 记录执行
                    execution.completed_at = datetime.utcnow()
                    execution.duration_seconds = (
                        execution.completed_at - execution.started_at
                    ).total_seconds()
                    await self._record_execution(execution)
            
            async def _check_governance(
                self, 
                config: CronTriggerConfig, 
                execution: CronExecution
            ) -> bool:
                """检查治理约束"""
                from owlclaw.governance import governance_manager
                
                checks = {}
                
                # 检查冷却时间
                if config.cooldown_seconds > 0:
                    last_execution = await self._get_last_execution(config.event_name)
                    if last_execution:
                        elapsed = (datetime.utcnow() - last_execution.completed_at).total_seconds()
                        if elapsed < config.cooldown_seconds:
                            checks["cooldown"] = False
                            execution.skip_reason = f"Cooldown not satisfied: {elapsed}s < {config.cooldown_seconds}s"
                            return False
                    checks["cooldown"] = True
                
                # 检查每日执行次数
                if config.max_daily_runs:
                    today_runs = await self._count_today_runs(config.event_name)
                    if today_runs >= config.max_daily_runs:
                        checks["daily_runs"] = False
                        execution.skip_reason = f"Daily run limit reached: {today_runs} >= {config.max_daily_runs}"
                        return False
                    checks["daily_runs"] = True
                
                # 检查每日成本
                if config.max_daily_cost:
                    today_cost = await self._get_today_cost(config.event_name)
                    if today_cost >= config.max_daily_cost:
                        checks["daily_cost"] = False
                        execution.skip_reason = f"Daily cost limit reached: ${today_cost} >= ${config.max_daily_cost}"
                        return False
                    checks["daily_cost"] = True
                
                execution.governance_checks = checks
                return True
            
            def _should_use_agent(self, config: CronTriggerConfig) -> bool:
                """决定是否使用 Agent（支持渐进式迁移）"""
                import random
                return random.random() < config.migration_weight
            
            async def _execute_agent(
                self, 
                config: CronTriggerConfig, 
                execution: CronExecution
            ):
                """执行 Agent 决策"""
                from owlclaw.agent.runtime import agent_runtime
                
                # 触发 Agent Run
                run = await agent_runtime.trigger_event(
                    event_name=config.event_name,
                    focus=config.focus,
                    context=execution.context
                )
                
                # 记录 Agent 信息
                execution.agent_run_id = run.run_id
                execution.llm_calls = run.llm_calls
                execution.cost_usd = run.cost_usd
                
                # 检查成本约束
                if config.max_cost_per_run and execution.cost_usd > config.max_cost_per_run:
                    raise ValueError(
                        f"Cost limit exceeded: ${execution.cost_usd} > ${config.max_cost_per_run}"
                    )
            
            async def _execute_fallback(
                self, 
                config: CronTriggerConfig, 
                execution: CronExecution
            ):
                """执行 Fallback Handler"""
                if config.fallback_handler:
                    execution.status = ExecutionStatus.FALLBACK
                    await config.fallback_handler()
                else:
                    raise ValueError("No fallback handler configured")
            
            async def _handle_failure(
                self, 
                config: CronTriggerConfig, 
                execution: CronExecution
            ):
                """处理执行失败"""
                # 尝试 fallback
                if config.fallback_strategy in ["on_failure", "always"]:
                    try:
                        await self._execute_fallback(config, execution)
                        execution.status = ExecutionStatus.FALLBACK
                    except Exception as e:
                        logger.error(f"Fallback also failed: {e}")
                
                # 重试逻辑由 Hatchet 处理
                if config.retry_on_failure and execution.retry_count < config.max_retries:
                    raise  # 让 Hatchet 重试
            
            async def _record_execution(self, execution: CronExecution):
                """记录执行到 Ledger"""
                from owlclaw.governance.ledger import ledger
                
                await ledger.record_event(
                    event_type="cron_execution",
                    event_name=execution.event_name,
                    data=execution.__dict__
                )
            
            async def _get_last_execution(self, event_name: str) -> Optional[CronExecution]:
                """获取上次执行记录"""
                # 从 Ledger 查询
                pass
            
            async def _count_today_runs(self, event_name: str) -> int:
                """统计今日执行次数"""
                # 从 Ledger 查询
                pass
            
            async def _get_today_cost(self, event_name: str) -> float:
                """统计今日成本"""
                # 从 Ledger 查询
                pass
        
        return CronWorkflow
    
    def get_trigger(self, event_name: str) -> Optional[CronTriggerConfig]:
        """获取触发器配置"""
        return self._triggers.get(event_name)
    
    def list_triggers(self) -> List[CronTriggerConfig]:
        """列出所有触发器"""
        return list(self._triggers.values())
    
    async def pause_trigger(self, event_name: str):
        """暂停触发器"""
        config = self._triggers.get(event_name)
        if not config:
            raise ValueError(f"Trigger not found: {event_name}")
        
        config.enabled = False
        # 通知 Hatchet 暂停
        # TODO: Hatchet API 调用
    
    async def resume_trigger(self, event_name: str):
        """恢复触发器"""
        config = self._triggers.get(event_name)
        if not config:
            raise ValueError(f"Trigger not found: {event_name}")
        
        config.enabled = True
        # 通知 Hatchet 恢复
        # TODO: Hatchet API 调用
    
    async def trigger_now(self, event_name: str, **kwargs):
        """手动触发"""
        config = self._triggers.get(event_name)
        if not config:
            raise ValueError(f"Trigger not found: {event_name}")
        
        # 创建手动触发的执行记录
        execution = CronExecution(
            execution_id=str(uuid.uuid4()),
            event_name=event_name,
            triggered_at=datetime.utcnow(),
            status=ExecutionStatus.PENDING,
            context={
                "trigger_type": "manual",
                "expression": config.expression,
                "focus": config.focus,
                **kwargs
            }
        )
        
        # 直接执行（不通过 Hatchet）
        workflow = self._hatchet_workflows[event_name]()
        await workflow.trigger_agent(None)
```


### 3.2 装饰器 API

**职责**：提供简洁的装饰器 API 用于注册 Cron 触发器。

```python
from functools import wraps
from typing import Optional, Callable

class OwlClawApp:
    """OwlClaw 应用主类"""
    
    def __init__(self):
        self.cron_registry = CronTriggerRegistry(self)
    
    def cron(
        self,
        expression: str,
        event_name: Optional[str] = None,
        focus: Optional[str] = None,
        description: Optional[str] = None,
        fallback: Optional[Callable] = None,
        **kwargs
    ):
        """
        Cron 触发器装饰器
        
        Args:
            expression: Cron 表达式（5 字段）
            event_name: 事件名称（默认使用函数名）
            focus: Focus 标识符
            description: 任务描述
            fallback: Fallback 函数（可以是被装饰的函数本身）
            **kwargs: 其他配置参数（max_cost_per_run, max_daily_cost 等）
        
        Example:
            @app.cron(
                expression="0 * * * *",
                event_name="hourly_check",
                focus="inventory_monitor",
                description="每小时检查库存水平",
                max_cost_per_run=0.5,
                max_daily_cost=10.0
            )
            async def hourly_inventory_check():
                # 可选的 fallback 实现
                # 如果 Agent 决策失败，执行这里的逻辑
                pass
        """
        def decorator(func: Callable):
            # 使用函数名作为默认 event_name
            _event_name = event_name or func.__name__
            
            # 使用被装饰的函数作为 fallback（如果没有显式指定）
            _fallback = fallback or func
            
            # 注册触发器
            self.cron_registry.register(
                event_name=_event_name,
                expression=expression,
                focus=focus,
                fallback_handler=_fallback,
                description=description or func.__doc__,
                **kwargs
            )
            
            # 返回原函数（不修改）
            @wraps(func)
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)
            
            return wrapper
        
        return decorator
    
    @property
    def cron(self) -> CronTriggerRegistry:
        """访问 Cron 触发器注册表"""
        return self.cron_registry
```

**使用示例**：

```python
from owlclaw import OwlClawApp

app = OwlClawApp()

# 示例 1：最简单的用法
@app.cron(expression="0 * * * *")
async def hourly_check():
    """每小时检查（Agent 决策失败时执行此函数）"""
    print("Fallback: checking...")

# 示例 2：指定 focus 和约束
@app.cron(
    expression="0 9 * * 1-5",
    event_name="morning_decision",
    focus="trading_decision",
    description="交易日开盘前决策",
    max_cost_per_run=1.0,
    max_daily_cost=20.0,
    cooldown_seconds=3600
)
async def morning_trading():
    """Fallback: 使用固定策略"""
    pass

# 示例 3：只用 Agent，不提供 fallback
@app.cron(
    expression="0 18 * * *",
    event_name="daily_report",
    focus="reporting",
    fallback=None  # 不提供 fallback
)
async def daily_report():
    """每日报告（必须由 Agent 生成）"""
    pass

# 示例 4：渐进式迁移
@app.cron(
    expression="*/15 * * * *",
    event_name="frequent_check",
    migration_weight=0.5,  # 50% 使用 Agent，50% 使用 fallback
    fallback_strategy="on_failure"
)
async def frequent_check():
    """高频检查（逐步迁移到 Agent）"""
    # 原有的业务逻辑
    pass
```


### 3.3 Focus 与 Skills 集成

**职责**：根据 focus 参数选择性加载 Skills，引导 Agent 关注特定业务领域。

```python
from owlclaw.capabilities.skills import SkillsManager

class FocusManager:
    """Focus 管理器"""
    
    def __init__(self, skills_manager: SkillsManager):
        self.skills_manager = skills_manager
    
    async def load_skills_for_focus(
        self, 
        focus: Optional[str]
    ) -> List[Skill]:
        """
        根据 focus 加载 Skills
        
        Args:
            focus: Focus 标识符（如 "inventory_monitor", "trading_decision"）
        
        Returns:
            匹配的 Skills 列表
        """
        if not focus:
            # 没有 focus，加载所有 Skills
            return await self.skills_manager.load_all_skills()
        
        # 根据 focus 过滤 Skills
        all_skills = await self.skills_manager.load_all_skills()
        matched_skills = []
        
        for skill in all_skills:
            # 检查 Skill 的 frontmatter 中的 focus 标签
            if self._skill_matches_focus(skill, focus):
                matched_skills.append(skill)
        
        return matched_skills
    
    def _skill_matches_focus(self, skill: Skill, focus: str) -> bool:
        """检查 Skill 是否匹配 focus"""
        # 从 SKILL.md 的 frontmatter 读取 focus 标签
        skill_focuses = skill.metadata.get("focus", [])
        
        if isinstance(skill_focuses, str):
            skill_focuses = [skill_focuses]
        
        return focus in skill_focuses
    
    def build_agent_prompt(
        self, 
        focus: Optional[str], 
        skills: List[Skill]
    ) -> str:
        """构建 Agent prompt"""
        prompt_parts = []
        
        if focus:
            prompt_parts.append(f"Current focus: {focus}")
            prompt_parts.append(f"You should prioritize actions related to {focus}.")
        
        prompt_parts.append(f"\nAvailable skills ({len(skills)}):")
        for skill in skills:
            prompt_parts.append(f"- {skill.name}: {skill.description}")
        
        return "\n".join(prompt_parts)
```

**SKILL.md 示例**（支持 focus 标签）：

```markdown
---
name: inventory_check
description: 检查库存水平并发送预警
focus: 
  - inventory_monitor
  - warehouse_management
version: 1.0.0
---

# Inventory Check Skill

## 功能

检查指定仓库的库存水平，当库存低于安全阈值时发送预警。

## 使用场景

- 定期库存检查（每小时）
- 补货决策
- 库存预警

## 可用工具

- `check_inventory(warehouse_id: str) -> dict`
- `send_alert(message: str, recipients: List[str])`
```


### 3.4 Governance 集成

**职责**：在 Cron 触发前后应用治理约束和记录。

```python
from owlclaw.governance import GovernanceManager, Ledger

class CronGovernance:
    """Cron 触发器的治理层"""
    
    def __init__(
        self, 
        governance_manager: GovernanceManager,
        ledger: Ledger
    ):
        self.governance = governance_manager
        self.ledger = ledger
    
    async def check_constraints(
        self, 
        config: CronTriggerConfig,
        execution: CronExecution
    ) -> tuple[bool, Optional[str]]:
        """
        检查治理约束
        
        Returns:
            (是否通过, 失败原因)
        """
        checks = {}
        
        # 1. 检查冷却时间
        if config.cooldown_seconds > 0:
            last_exec = await self._get_last_successful_execution(config.event_name)
            if last_exec:
                elapsed = (datetime.utcnow() - last_exec.completed_at).total_seconds()
                if elapsed < config.cooldown_seconds:
                    return False, f"Cooldown: {elapsed}s < {config.cooldown_seconds}s"
            checks["cooldown"] = True
        
        # 2. 检查每日执行次数
        if config.max_daily_runs:
            today_count = await self._count_today_executions(config.event_name)
            if today_count >= config.max_daily_runs:
                return False, f"Daily runs: {today_count} >= {config.max_daily_runs}"
            checks["daily_runs"] = True
        
        # 3. 检查每日成本
        if config.max_daily_cost:
            today_cost = await self._sum_today_cost(config.event_name)
            if today_cost >= config.max_daily_cost:
                return False, f"Daily cost: ${today_cost} >= ${config.max_daily_cost}"
            checks["daily_cost"] = True
        
        # 4. 检查熔断器
        circuit_breaker = await self._check_circuit_breaker(config.event_name)
        if circuit_breaker["open"]:
            return False, f"Circuit breaker open: {circuit_breaker['reason']}"
        checks["circuit_breaker"] = True
        
        execution.governance_checks = checks
        return True, None
    
    async def record_execution(self, execution: CronExecution):
        """记录执行到 Ledger"""
        await self.ledger.record_event(
            event_type="cron_execution",
            event_name=execution.event_name,
            timestamp=execution.triggered_at,
            data={
                "execution_id": execution.execution_id,
                "status": execution.status.value,
                "duration_seconds": execution.duration_seconds,
                "cost_usd": execution.cost_usd,
                "llm_calls": execution.llm_calls,
                "decision_mode": execution.decision_mode,
                "governance_checks": execution.governance_checks,
                "error_message": execution.error_message,
            }
        )
    
    async def update_circuit_breaker(
        self, 
        event_name: str, 
        execution: CronExecution
    ):
        """更新熔断器状态"""
        # 获取最近 N 次执行
        recent_executions = await self._get_recent_executions(event_name, limit=10)
        
        # 计算失败率
        failed_count = sum(1 for e in recent_executions if e.status == ExecutionStatus.FAILED)
        failure_rate = failed_count / len(recent_executions) if recent_executions else 0
        
        # 如果失败率 > 50%，打开熔断器
        if failure_rate > 0.5:
            await self._open_circuit_breaker(
                event_name, 
                reason=f"High failure rate: {failure_rate:.1%}"
            )
    
    async def _get_last_successful_execution(
        self, 
        event_name: str
    ) -> Optional[CronExecution]:
        """获取上次成功执行"""
        events = await self.ledger.query_events(
            event_type="cron_execution",
            event_name=event_name,
            filters={"status": ExecutionStatus.SUCCESS.value},
            limit=1,
            order_by="timestamp DESC"
        )
        return events[0] if events else None
    
    async def _count_today_executions(self, event_name: str) -> int:
        """统计今日执行次数"""
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        events = await self.ledger.query_events(
            event_type="cron_execution",
            event_name=event_name,
            time_range=(today_start, datetime.utcnow())
        )
        return len(events)
    
    async def _sum_today_cost(self, event_name: str) -> float:
        """统计今日成本"""
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        events = await self.ledger.query_events(
            event_type="cron_execution",
            event_name=event_name,
            time_range=(today_start, datetime.utcnow())
        )
        return sum(e.data.get("cost_usd", 0) for e in events)
    
    async def _check_circuit_breaker(self, event_name: str) -> dict:
        """检查熔断器状态"""
        # 从 Redis/DB 读取熔断器状态
        # 返回 {"open": bool, "reason": str}
        pass
    
    async def _open_circuit_breaker(self, event_name: str, reason: str):
        """打开熔断器"""
        # 写入 Redis/DB
        # 发送告警通知
        pass
    
    async def _get_recent_executions(
        self, 
        event_name: str, 
        limit: int
    ) -> List[CronExecution]:
        """获取最近的执行记录"""
        events = await self.ledger.query_events(
            event_type="cron_execution",
            event_name=event_name,
            limit=limit,
            order_by="timestamp DESC"
        )
        return [self._event_to_execution(e) for e in events]
    
    def _event_to_execution(self, event: dict) -> CronExecution:
        """将 Ledger 事件转换为 CronExecution"""
        # 转换逻辑
        pass
```


---

## 4. 数据流设计

### 4.1 注册流程

```
┌─────────────┐
│  Developer  │
└──────┬──────┘
       │ @app.cron(expression="0 * * * *")
       ↓
┌─────────────────────────────────────────┐
│  OwlClawApp.cron() decorator            │
│  1. 验证 cron 表达式                     │
│  2. 创建 CronTriggerConfig              │
│  3. 调用 CronTriggerRegistry.register() │
└──────┬──────────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────────┐
│  CronTriggerRegistry                    │
│  1. 验证 event_name 唯一性              │
│  2. 创建 Hatchet Workflow               │
│  3. 注册到 Hatchet                      │
│  4. 保存配置到内存                      │
└──────┬──────────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────────┐
│  Hatchet Server                         │
│  1. 接收 workflow 注册                  │
│  2. 解析 on_cron 参数                   │
│  3. 创建 cron 调度任务                  │
│  4. 持久化到 PostgreSQL                 │
└─────────────────────────────────────────┘
```

### 4.2 触发流程

```
┌─────────────────────────────────────────┐
│  Hatchet Scheduler                      │
│  1. 根据 cron 表达式计算下次触发时间     │
│  2. 到达触发时间                        │
│  3. 创建 workflow run                   │
└──────┬──────────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────────┐
│  Hatchet Worker (OwlClaw Process)       │
│  1. 接收 workflow run                   │
│  2. 执行 CronWorkflow.trigger_agent()   │
└──────┬──────────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────────┐
│  CronWorkflow.trigger_agent()           │
│  1. 创建 CronExecution 记录             │
│  2. 检查 governance 约束                │
│  3. 决定执行模式（Agent/Fallback）      │
│  4. 执行并记录结果                      │
└──────┬──────────────────────────────────┘
       │
       ├─────────────────┬─────────────────┐
       │ Agent 模式      │ Fallback 模式   │
       ↓                 ↓                 │
┌──────────────┐  ┌──────────────────┐    │
│ Agent Runtime│  │ Fallback Handler │    │
│ 1. 加载 Skills│  │ 1. 执行原逻辑    │    │
│ 2. LLM 决策  │  │ 2. 返回结果      │    │
│ 3. 执行工具  │  └──────────────────┘    │
│ 4. 返回结果  │                          │
└──────┬───────┘                          │
       │                                  │
       └──────────────┬───────────────────┘
                      ↓
       ┌─────────────────────────────────┐
       │  记录到 Ledger                   │
       │  1. 执行状态                     │
       │  2. 成本和时长                   │
       │  3. 治理检查结果                 │
       │  4. 错误信息（如果有）           │
       └─────────────────────────────────┘
```

### 4.3 治理检查流程

```
┌─────────────────────────────────────────┐
│  CronWorkflow.trigger_agent()           │
└──────┬──────────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────────┐
│  CronGovernance.check_constraints()     │
└──────┬──────────────────────────────────┘
       │
       ├──→ 检查冷却时间
       │    └─→ 查询 Ledger 获取上次执行时间
       │
       ├──→ 检查每日执行次数
       │    └─→ 查询 Ledger 统计今日执行次数
       │
       ├──→ 检查每日成本
       │    └─→ 查询 Ledger 统计今日总成本
       │
       └──→ 检查熔断器
            └─→ 查询 Redis/DB 获取熔断器状态
       
       ↓
┌─────────────────────────────────────────┐
│  返回检查结果                            │
│  - 通过：继续执行                        │
│  - 不通过：跳过执行并记录原因            │
└─────────────────────────────────────────┘
```


---

## 5. 错误处理

### 5.1 错误分类

| 错误类型 | 处理策略 | 示例 |
|---------|---------|------|
| 配置错误 | 启动时失败，拒绝注册 | 非法的 cron 表达式、重复的 event_name |
| Hatchet 连接错误 | 记录错误，尝试 fallback | Hatchet Server 不可用 |
| 治理约束不满足 | 跳过执行，记录原因 | 超过每日成本上限、冷却时间未满足 |
| Agent 执行错误 | 重试或 fallback | LLM 调用失败、工具执行失败 |
| Fallback 执行错误 | 记录错误，发送告警 | Fallback 函数抛出异常 |

### 5.2 重试策略

```python
class RetryStrategy:
    """重试策略"""
    
    @staticmethod
    def should_retry(
        error: Exception, 
        retry_count: int, 
        config: CronTriggerConfig
    ) -> bool:
        """判断是否应该重试"""
        
        # 不重试的错误类型
        if isinstance(error, (ValueError, TypeError)):
            return False
        
        # 检查重试次数
        if retry_count >= config.max_retries:
            return False
        
        # 检查是否启用重试
        if not config.retry_on_failure:
            return False
        
        return True
    
    @staticmethod
    def calculate_delay(retry_count: int, config: CronTriggerConfig) -> int:
        """计算重试延迟（指数退避）"""
        base_delay = config.retry_delay_seconds
        return base_delay * (2 ** retry_count)
```

### 5.3 熔断器机制

```python
class CircuitBreaker:
    """熔断器"""
    
    def __init__(self, failure_threshold: float = 0.5, window_size: int = 10):
        self.failure_threshold = failure_threshold
        self.window_size = window_size
    
    async def check(self, event_name: str) -> tuple[bool, Optional[str]]:
        """
        检查熔断器状态
        
        Returns:
            (是否打开, 原因)
        """
        # 获取最近的执行记录
        recent = await self._get_recent_executions(event_name, self.window_size)
        
        if len(recent) < self.window_size:
            return False, None  # 样本不足，不触发熔断
        
        # 计算失败率
        failed = sum(1 for e in recent if e.status == ExecutionStatus.FAILED)
        failure_rate = failed / len(recent)
        
        if failure_rate >= self.failure_threshold:
            return True, f"High failure rate: {failure_rate:.1%} (threshold: {self.failure_threshold:.1%})"
        
        return False, None
    
    async def open(self, event_name: str, reason: str):
        """打开熔断器"""
        # 1. 记录到 Redis/DB
        await self._set_state(event_name, "open", reason)
        
        # 2. 暂停 Cron 触发器
        # TODO: 调用 Hatchet API 暂停 workflow
        
        # 3. 发送告警
        await self._send_alert(
            title=f"Circuit breaker opened: {event_name}",
            message=f"Reason: {reason}",
            severity="critical"
        )
    
    async def close(self, event_name: str):
        """关闭熔断器"""
        # 1. 更新状态
        await self._set_state(event_name, "closed", None)
        
        # 2. 恢复 Cron 触发器
        # TODO: 调用 Hatchet API 恢复 workflow
        
        # 3. 发送通知
        await self._send_alert(
            title=f"Circuit breaker closed: {event_name}",
            message="Service recovered",
            severity="info"
        )
```

### 5.4 错误通知

```python
class ErrorNotifier:
    """错误通知器"""
    
    async def notify_failure(
        self, 
        execution: CronExecution,
        config: CronTriggerConfig
    ):
        """通知执行失败"""
        
        # 判断是否需要通知
        if not self._should_notify(execution, config):
            return
        
        # 构建通知消息
        message = self._build_message(execution, config)
        
        # 发送通知（邮件、Slack、钉钉等）
        await self._send_notification(message)
    
    def _should_notify(
        self, 
        execution: CronExecution,
        config: CronTriggerConfig
    ) -> bool:
        """判断是否需要通知"""
        
        # 只通知失败的执行
        if execution.status != ExecutionStatus.FAILED:
            return False
        
        # 检查是否连续失败
        # 只在第 1、3、5 次失败时通知，避免通知风暴
        return execution.retry_count in [0, 2, 4]
    
    def _build_message(
        self, 
        execution: CronExecution,
        config: CronTriggerConfig
    ) -> dict:
        """构建通知消息"""
        return {
            "title": f"Cron Task Failed: {config.event_name}",
            "fields": [
                {"name": "Event Name", "value": config.event_name},
                {"name": "Expression", "value": config.expression},
                {"name": "Triggered At", "value": execution.triggered_at.isoformat()},
                {"name": "Error", "value": execution.error_message},
                {"name": "Retry Count", "value": str(execution.retry_count)},
            ],
            "severity": "error"
        }
```


---

## 6. 性能优化

### 6.1 并发控制

```python
import asyncio
from asyncio import Semaphore

class ConcurrencyController:
    """并发控制器"""
    
    def __init__(self, max_concurrent: int = 10):
        self.semaphore = Semaphore(max_concurrent)
        self.active_tasks: Dict[str, asyncio.Task] = {}
    
    async def execute_with_limit(
        self, 
        event_name: str,
        coro: Coroutine
    ):
        """限制并发执行"""
        async with self.semaphore:
            task = asyncio.create_task(coro)
            self.active_tasks[event_name] = task
            
            try:
                result = await task
                return result
            finally:
                del self.active_tasks[event_name]
    
    def get_active_count(self) -> int:
        """获取当前活跃任务数"""
        return len(self.active_tasks)
    
    async def wait_all(self):
        """等待所有任务完成"""
        if self.active_tasks:
            await asyncio.gather(*self.active_tasks.values(), return_exceptions=True)
```

### 6.2 优先级调度

```python
import heapq
from dataclasses import dataclass, field
from typing import Any

@dataclass(order=True)
class PrioritizedTask:
    """优先级任务"""
    priority: int
    event_name: str = field(compare=False)
    coro: Any = field(compare=False)

class PriorityScheduler:
    """优先级调度器"""
    
    def __init__(self):
        self.queue: List[PrioritizedTask] = []
        self.lock = asyncio.Lock()
    
    async def schedule(
        self, 
        event_name: str,
        priority: int,
        coro: Coroutine
    ):
        """调度任务"""
        async with self.lock:
            task = PrioritizedTask(
                priority=-priority,  # 负数使得大的优先级先执行
                event_name=event_name,
                coro=coro
            )
            heapq.heappush(self.queue, task)
    
    async def execute_next(self):
        """执行下一个任务"""
        async with self.lock:
            if not self.queue:
                return None
            
            task = heapq.heappop(self.queue)
            return await task.coro
```

### 6.3 缓存优化

```python
from functools import lru_cache
from datetime import datetime, timedelta

class CronCache:
    """Cron 触发器缓存"""
    
    def __init__(self):
        self._execution_cache: Dict[str, CronExecution] = {}
        self._stats_cache: Dict[str, dict] = {}
        self._cache_ttl = timedelta(minutes=5)
    
    def cache_execution(self, execution: CronExecution):
        """缓存执行记录"""
        self._execution_cache[execution.execution_id] = execution
    
    def get_execution(self, execution_id: str) -> Optional[CronExecution]:
        """获取缓存的执行记录"""
        return self._execution_cache.get(execution_id)
    
    @lru_cache(maxsize=100)
    def get_next_trigger_time(self, expression: str, after: datetime) -> datetime:
        """计算下次触发时间（带缓存）"""
        from croniter import croniter
        return croniter(expression, after).get_next(datetime)
    
    async def get_stats(self, event_name: str) -> dict:
        """获取统计信息（带缓存）"""
        cached = self._stats_cache.get(event_name)
        
        if cached and datetime.utcnow() - cached["cached_at"] < self._cache_ttl:
            return cached["data"]
        
        # 重新计算统计
        stats = await self._calculate_stats(event_name)
        
        self._stats_cache[event_name] = {
            "data": stats,
            "cached_at": datetime.utcnow()
        }
        
        return stats
    
    async def _calculate_stats(self, event_name: str) -> dict:
        """计算统计信息"""
        # 从 Ledger 查询并计算
        pass
```

### 6.4 批量操作

```python
class BatchOperations:
    """批量操作"""
    
    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size
    
    async def batch_record_executions(
        self, 
        executions: List[CronExecution]
    ):
        """批量记录执行"""
        from owlclaw.governance.ledger import ledger
        
        # 分批写入
        for i in range(0, len(executions), self.batch_size):
            batch = executions[i:i + self.batch_size]
            await ledger.batch_record_events([
                {
                    "event_type": "cron_execution",
                    "event_name": e.event_name,
                    "timestamp": e.triggered_at,
                    "data": e.__dict__
                }
                for e in batch
            ])
    
    async def batch_query_executions(
        self, 
        event_names: List[str],
        time_range: tuple[datetime, datetime]
    ) -> Dict[str, List[CronExecution]]:
        """批量查询执行记录"""
        from owlclaw.governance.ledger import ledger
        
        # 一次查询多个 event_name
        events = await ledger.query_events(
            event_type="cron_execution",
            filters={"event_name": {"$in": event_names}},
            time_range=time_range
        )
        
        # 按 event_name 分组
        result = {name: [] for name in event_names}
        for event in events:
            event_name = event.event_name
            if event_name in result:
                result[event_name].append(self._event_to_execution(event))
        
        return result
```


---

## 7. 监控与可观测性

### 7.1 Prometheus 指标

```python
from prometheus_client import Counter, Histogram, Gauge

class CronMetrics:
    """Cron 触发器指标"""
    
    # 执行次数
    executions_total = Counter(
        "owlclaw_cron_executions_total",
        "Total number of cron executions",
        ["event_name", "status", "decision_mode"]
    )
    
    # 执行时长
    execution_duration_seconds = Histogram(
        "owlclaw_cron_execution_duration_seconds",
        "Cron execution duration in seconds",
        ["event_name"],
        buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60, 120, 300]
    )
    
    # 触发延迟
    trigger_delay_seconds = Histogram(
        "owlclaw_cron_trigger_delay_seconds",
        "Delay between scheduled time and actual trigger",
        ["event_name"],
        buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60]
    )
    
    # 成本
    execution_cost_usd = Histogram(
        "owlclaw_cron_execution_cost_usd",
        "Cron execution cost in USD",
        ["event_name"],
        buckets=[0.001, 0.01, 0.1, 0.5, 1, 5, 10]
    )
    
    # LLM 调用次数
    llm_calls_total = Counter(
        "owlclaw_cron_llm_calls_total",
        "Total number of LLM calls in cron executions",
        ["event_name"]
    )
    
    # 活跃任务数
    active_tasks = Gauge(
        "owlclaw_cron_active_tasks",
        "Number of currently active cron tasks"
    )
    
    # 熔断器状态
    circuit_breaker_open = Gauge(
        "owlclaw_cron_circuit_breaker_open",
        "Circuit breaker status (1=open, 0=closed)",
        ["event_name"]
    )
    
    @classmethod
    def record_execution(cls, execution: CronExecution):
        """记录执行指标"""
        # 执行次数
        cls.executions_total.labels(
            event_name=execution.event_name,
            status=execution.status.value,
            decision_mode=execution.decision_mode
        ).inc()
        
        # 执行时长
        if execution.duration_seconds:
            cls.execution_duration_seconds.labels(
                event_name=execution.event_name
            ).observe(execution.duration_seconds)
        
        # 成本
        if execution.cost_usd:
            cls.execution_cost_usd.labels(
                event_name=execution.event_name
            ).observe(execution.cost_usd)
        
        # LLM 调用
        if execution.llm_calls:
            cls.llm_calls_total.labels(
                event_name=execution.event_name
            ).inc(execution.llm_calls)
    
    @classmethod
    def record_trigger_delay(cls, event_name: str, delay_seconds: float):
        """记录触发延迟"""
        cls.trigger_delay_seconds.labels(
            event_name=event_name
        ).observe(delay_seconds)
```

### 7.2 结构化日志

```python
import structlog

logger = structlog.get_logger()

class CronLogger:
    """Cron 触发器日志"""
    
    @staticmethod
    def log_registration(config: CronTriggerConfig):
        """记录注册"""
        logger.info(
            "cron_trigger_registered",
            event_name=config.event_name,
            expression=config.expression,
            focus=config.focus,
            has_fallback=config.fallback_handler is not None
        )
    
    @staticmethod
    def log_trigger(execution: CronExecution):
        """记录触发"""
        logger.info(
            "cron_trigger_fired",
            execution_id=execution.execution_id,
            event_name=execution.event_name,
            triggered_at=execution.triggered_at.isoformat()
        )
    
    @staticmethod
    def log_execution_start(execution: CronExecution):
        """记录执行开始"""
        logger.info(
            "cron_execution_started",
            execution_id=execution.execution_id,
            event_name=execution.event_name,
            decision_mode=execution.decision_mode
        )
    
    @staticmethod
    def log_execution_complete(execution: CronExecution):
        """记录执行完成"""
        logger.info(
            "cron_execution_completed",
            execution_id=execution.execution_id,
            event_name=execution.event_name,
            status=execution.status.value,
            duration_seconds=execution.duration_seconds,
            cost_usd=execution.cost_usd,
            llm_calls=execution.llm_calls
        )
    
    @staticmethod
    def log_execution_failed(execution: CronExecution):
        """记录执行失败"""
        logger.error(
            "cron_execution_failed",
            execution_id=execution.execution_id,
            event_name=execution.event_name,
            error_message=execution.error_message,
            retry_count=execution.retry_count
        )
    
    @staticmethod
    def log_governance_skip(execution: CronExecution):
        """记录治理跳过"""
        logger.warning(
            "cron_execution_skipped",
            execution_id=execution.execution_id,
            event_name=execution.event_name,
            skip_reason=execution.skip_reason,
            governance_checks=execution.governance_checks
        )
    
    @staticmethod
    def log_circuit_breaker_open(event_name: str, reason: str):
        """记录熔断器打开"""
        logger.critical(
            "cron_circuit_breaker_opened",
            event_name=event_name,
            reason=reason
        )
```

### 7.3 健康检查

```python
from typing import Dict, Any

class CronHealthCheck:
    """Cron 触发器健康检查"""
    
    def __init__(self, registry: CronTriggerRegistry):
        self.registry = registry
    
    async def check_health(self) -> Dict[str, Any]:
        """检查健康状态"""
        health = {
            "status": "healthy",
            "checks": {}
        }
        
        # 检查 Hatchet 连接
        hatchet_health = await self._check_hatchet()
        health["checks"]["hatchet"] = hatchet_health
        if not hatchet_health["healthy"]:
            health["status"] = "unhealthy"
        
        # 检查触发器状态
        triggers_health = await self._check_triggers()
        health["checks"]["triggers"] = triggers_health
        
        # 检查熔断器
        circuit_breakers = await self._check_circuit_breakers()
        health["checks"]["circuit_breakers"] = circuit_breakers
        if circuit_breakers["open_count"] > 0:
            health["status"] = "degraded"
        
        return health
    
    async def _check_hatchet(self) -> dict:
        """检查 Hatchet 连接"""
        try:
            # 尝试连接 Hatchet
            from owlclaw.integrations.hatchet import hatchet_client
            # TODO: 实际的健康检查逻辑
            return {"healthy": True, "message": "Connected"}
        except Exception as e:
            return {"healthy": False, "message": str(e)}
    
    async def _check_triggers(self) -> dict:
        """检查触发器状态"""
        triggers = self.registry.list_triggers()
        
        return {
            "total": len(triggers),
            "enabled": sum(1 for t in triggers if t.enabled),
            "disabled": sum(1 for t in triggers if not t.enabled)
        }
    
    async def _check_circuit_breakers(self) -> dict:
        """检查熔断器状态"""
        triggers = self.registry.list_triggers()
        open_breakers = []
        
        for trigger in triggers:
            # 检查熔断器状态
            # TODO: 实际的检查逻辑
            pass
        
        return {
            "open_count": len(open_breakers),
            "open_breakers": open_breakers
        }
```


---

## 8. 测试策略

### 8.1 单元测试

```python
import pytest
from datetime import datetime, timedelta
from owlclaw.triggers.cron import CronTriggerRegistry, CronTriggerConfig

class TestCronTriggerRegistry:
    """CronTriggerRegistry 单元测试"""
    
    @pytest.fixture
    def registry(self, mock_app):
        return CronTriggerRegistry(mock_app)
    
    def test_register_valid_trigger(self, registry):
        """测试注册有效的触发器"""
        registry.register(
            event_name="test_trigger",
            expression="0 * * * *",
            focus="test_focus"
        )
        
        trigger = registry.get_trigger("test_trigger")
        assert trigger is not None
        assert trigger.event_name == "test_trigger"
        assert trigger.expression == "0 * * * *"
        assert trigger.focus == "test_focus"
    
    def test_register_duplicate_trigger(self, registry):
        """测试注册重复的触发器"""
        registry.register(
            event_name="test_trigger",
            expression="0 * * * *"
        )
        
        with pytest.raises(ValueError, match="already registered"):
            registry.register(
                event_name="test_trigger",
                expression="0 * * * *"
            )
    
    def test_register_invalid_expression(self, registry):
        """测试注册非法的 cron 表达式"""
        with pytest.raises(ValueError, match="Invalid cron expression"):
            registry.register(
                event_name="test_trigger",
                expression="invalid"
            )
    
    def test_validate_cron_expression(self, registry):
        """测试 cron 表达式验证"""
        # 有效的表达式
        assert registry._validate_cron_expression("0 * * * *")
        assert registry._validate_cron_expression("*/15 * * * *")
        assert registry._validate_cron_expression("0 9 * * 1-5")
        
        # 无效的表达式
        assert not registry._validate_cron_expression("invalid")
        assert not registry._validate_cron_expression("0 * * *")  # 缺少字段
        assert not registry._validate_cron_expression("60 * * * *")  # 分钟超出范围

class TestCronExecution:
    """CronExecution 单元测试"""
    
    def test_execution_lifecycle(self):
        """测试执行生命周期"""
        execution = CronExecution(
            execution_id="test-123",
            event_name="test_trigger",
            triggered_at=datetime.utcnow(),
            status=ExecutionStatus.PENDING
        )
        
        # 开始执行
        execution.status = ExecutionStatus.RUNNING
        execution.started_at = datetime.utcnow()
        
        # 完成执行
        execution.status = ExecutionStatus.SUCCESS
        execution.completed_at = datetime.utcnow()
        execution.duration_seconds = (
            execution.completed_at - execution.started_at
        ).total_seconds()
        
        assert execution.status == ExecutionStatus.SUCCESS
        assert execution.duration_seconds > 0

class TestCronGovernance:
    """CronGovernance 单元测试"""
    
    @pytest.fixture
    def governance(self, mock_governance_manager, mock_ledger):
        return CronGovernance(mock_governance_manager, mock_ledger)
    
    @pytest.mark.asyncio
    async def test_check_cooldown(self, governance):
        """测试冷却时间检查"""
        config = CronTriggerConfig(
            event_name="test_trigger",
            expression="0 * * * *",
            cooldown_seconds=3600
        )
        
        execution = CronExecution(
            execution_id="test-123",
            event_name="test_trigger",
            triggered_at=datetime.utcnow()
        )
        
        # 模拟上次执行在 30 分钟前
        mock_last_execution = CronExecution(
            execution_id="test-122",
            event_name="test_trigger",
            triggered_at=datetime.utcnow() - timedelta(minutes=30),
            completed_at=datetime.utcnow() - timedelta(minutes=30)
        )
        
        # 应该不通过（冷却时间未满足）
        passed, reason = await governance.check_constraints(config, execution)
        assert not passed
        assert "Cooldown" in reason
    
    @pytest.mark.asyncio
    async def test_check_daily_runs(self, governance):
        """测试每日执行次数检查"""
        config = CronTriggerConfig(
            event_name="test_trigger",
            expression="0 * * * *",
            max_daily_runs=10
        )
        
        execution = CronExecution(
            execution_id="test-123",
            event_name="test_trigger",
            triggered_at=datetime.utcnow()
        )
        
        # 模拟今日已执行 10 次
        # TODO: Mock ledger 返回 10 次执行记录
        
        # 应该不通过（超过每日限制）
        passed, reason = await governance.check_constraints(config, execution)
        assert not passed
        assert "Daily runs" in reason
```

### 8.2 集成测试

```python
import pytest
from owlclaw import OwlClawApp

class TestCronIntegration:
    """Cron 触发器集成测试"""
    
    @pytest.fixture
    async def app(self):
        """创建测试应用"""
        app = OwlClawApp()
        await app.start()
        yield app
        await app.stop()
    
    @pytest.mark.asyncio
    async def test_cron_decorator(self, app):
        """测试 @app.cron 装饰器"""
        executed = []
        
        @app.cron(expression="* * * * *", event_name="test_trigger")
        async def test_handler():
            executed.append(True)
        
        # 验证触发器已注册
        trigger = app.cron_registry.get_trigger("test_trigger")
        assert trigger is not None
        assert trigger.expression == "* * * * *"
    
    @pytest.mark.asyncio
    async def test_manual_trigger(self, app):
        """测试手动触发"""
        executed = []
        
        @app.cron(expression="0 * * * *", event_name="test_trigger")
        async def test_handler():
            executed.append(True)
        
        # 手动触发
        await app.cron_registry.trigger_now("test_trigger")
        
        # 验证已执行
        # TODO: 验证 Agent Run 已创建
    
    @pytest.mark.asyncio
    async def test_focus_loading(self, app):
        """测试 focus 加载 Skills"""
        @app.cron(
            expression="0 * * * *",
            event_name="test_trigger",
            focus="test_focus"
        )
        async def test_handler():
            pass
        
        # 手动触发
        await app.cron_registry.trigger_now("test_trigger")
        
        # 验证只加载了匹配 focus 的 Skills
        # TODO: 验证 Skills 加载逻辑
    
    @pytest.mark.asyncio
    async def test_governance_constraints(self, app):
        """测试治理约束"""
        @app.cron(
            expression="0 * * * *",
            event_name="test_trigger",
            max_cost_per_run=0.1,
            max_daily_cost=1.0
        )
        async def test_handler():
            pass
        
        # 手动触发
        await app.cron_registry.trigger_now("test_trigger")
        
        # 验证约束已应用
        # TODO: 验证治理检查逻辑
```

### 8.3 端到端测试

```python
import pytest
from datetime import datetime, timedelta

class TestCronE2E:
    """Cron 触发器端到端测试"""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_hourly_check_workflow(self, app, hatchet_client):
        """测试每小时检查的完整流程"""
        
        # 1. 注册触发器
        @app.cron(
            expression="0 * * * *",
            event_name="hourly_check",
            focus="inventory_monitor"
        )
        async def hourly_check():
            pass
        
        # 2. 等待 Hatchet 调度（模拟）
        # TODO: 触发 Hatchet workflow
        
        # 3. 验证 Agent Run 已创建
        # TODO: 查询 Agent Run
        
        # 4. 验证 Ledger 记录
        # TODO: 查询 Ledger
        
        # 5. 验证指标
        # TODO: 查询 Prometheus 指标
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_fallback_on_agent_failure(self, app):
        """测试 Agent 失败时的 fallback"""
        
        fallback_executed = []
        
        @app.cron(
            expression="0 * * * *",
            event_name="test_trigger",
            fallback_strategy="on_failure"
        )
        async def test_handler():
            fallback_executed.append(True)
        
        # 模拟 Agent 失败
        # TODO: Mock Agent Runtime 抛出异常
        
        # 手动触发
        await app.cron_registry.trigger_now("test_trigger")
        
        # 验证 fallback 已执行
        assert len(fallback_executed) == 1
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_circuit_breaker(self, app):
        """测试熔断器"""
        
        @app.cron(
            expression="* * * * *",
            event_name="test_trigger"
        )
        async def test_handler():
            raise Exception("Simulated failure")
        
        # 连续触发 10 次，模拟连续失败
        for _ in range(10):
            try:
                await app.cron_registry.trigger_now("test_trigger")
            except:
                pass
        
        # 验证熔断器已打开
        # TODO: 查询熔断器状态
```


---

## 9. 部署与配置

### 9.1 环境变量

```bash
# Hatchet 配置
HATCHET_CLIENT_TOKEN=your_token_here
HATCHET_SERVER_URL=https://hatchet.example.com

# Cron 配置
OWLCLAW_CRON_MAX_CONCURRENT=10          # 最大并发任务数
OWLCLAW_CRON_DEFAULT_TIMEOUT=300        # 默认超时时间（秒）
OWLCLAW_CRON_ENABLE_METRICS=true        # 启用 Prometheus 指标
OWLCLAW_CRON_METRICS_PORT=9090          # 指标端口

# 治理配置
OWLCLAW_CRON_DEFAULT_MAX_COST=1.0       # 默认单次成本上限（USD）
OWLCLAW_CRON_DEFAULT_DAILY_COST=20.0    # 默认每日成本上限（USD）
OWLCLAW_CRON_CIRCUIT_BREAKER_THRESHOLD=0.5  # 熔断器阈值

# 日志配置
OWLCLAW_LOG_LEVEL=INFO
OWLCLAW_LOG_FORMAT=json
```

### 9.2 配置文件

```yaml
# owlclaw.yaml
cron:
  # 全局配置
  max_concurrent: 10
  default_timeout: 300
  enable_metrics: true
  metrics_port: 9090
  
  # 治理配置
  governance:
    default_max_cost_per_run: 1.0
    default_max_daily_cost: 20.0
    circuit_breaker:
      enabled: true
      failure_threshold: 0.5
      window_size: 10
      recovery_timeout: 300
  
  # 重试配置
  retry:
    enabled: true
    max_retries: 3
    base_delay: 60
    max_delay: 300
  
  # 通知配置
  notifications:
    enabled: true
    channels:
      - type: email
        recipients: ["admin@example.com"]
      - type: slack
        webhook_url: "https://hooks.slack.com/..."
```

### 9.3 Docker 部署

```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 暴露指标端口
EXPOSE 9090

# 启动应用
CMD ["python", "-m", "owlclaw.cli", "start"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  owlclaw:
    build: .
    environment:
      - HATCHET_CLIENT_TOKEN=${HATCHET_CLIENT_TOKEN}
      - HATCHET_SERVER_URL=${HATCHET_SERVER_URL}
      - OWLCLAW_CRON_MAX_CONCURRENT=10
      - OWLCLAW_CRON_ENABLE_METRICS=true
    ports:
      - "9090:9090"
    volumes:
      - ./skills:/app/skills
      - ./logs:/app/logs
    depends_on:
      - hatchet
  
  hatchet:
    image: hatchet/hatchet:latest
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/hatchet
    ports:
      - "8080:8080"
    depends_on:
      - postgres
  
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=hatchet
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9091:9090"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'

volumes:
  postgres_data:
  prometheus_data:
```

### 9.4 Kubernetes 部署

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: owlclaw-cron
  labels:
    app: owlclaw-cron
spec:
  replicas: 3
  selector:
    matchLabels:
      app: owlclaw-cron
  template:
    metadata:
      labels:
        app: owlclaw-cron
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9090"
        prometheus.io/path: "/metrics"
    spec:
      containers:
      - name: owlclaw
        image: owlclaw:latest
        ports:
        - containerPort: 9090
          name: metrics
        env:
        - name: HATCHET_CLIENT_TOKEN
          valueFrom:
            secretKeyRef:
              name: owlclaw-secrets
              key: hatchet-token
        - name: HATCHET_SERVER_URL
          value: "http://hatchet:8080"
        - name: OWLCLAW_CRON_MAX_CONCURRENT
          value: "10"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 9090
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 9090
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: owlclaw-cron
  labels:
    app: owlclaw-cron
spec:
  selector:
    app: owlclaw-cron
  ports:
  - port: 9090
    targetPort: 9090
    name: metrics
```


---

## 10. 迁移指南

### 10.1 从传统 Cron 迁移

**阶段 1：评估现有任务**

```python
# 原有的 cron 任务（crontab）
# 0 * * * * /usr/bin/python /app/scripts/hourly_check.py

# 评估清单：
# 1. 任务频率：每小时
# 2. 执行逻辑：检查库存并发送预警
# 3. 依赖：数据库、邮件服务
# 4. 平均执行时长：30 秒
# 5. 失败处理：无（依赖 cron 重试）
```

**阶段 2：保留原逻辑作为 Fallback**

```python
from owlclaw import OwlClawApp

app = OwlClawApp()

# 将原有逻辑封装为函数
async def legacy_hourly_check():
    """原有的库存检查逻辑"""
    # 原有代码
    inventory = check_inventory()
    if inventory < threshold:
        send_alert("Low inventory!")

# 注册为 Cron 触发器，使用 100% fallback
@app.cron(
    expression="0 * * * *",
    event_name="hourly_check",
    focus="inventory_monitor",
    migration_weight=0.0,  # 0% Agent，100% fallback
    fallback_strategy="always"
)
async def hourly_check():
    await legacy_hourly_check()
```

**阶段 3：逐步提高 Agent 权重**

```python
# Week 1: 10% Agent
@app.cron(
    expression="0 * * * *",
    event_name="hourly_check",
    focus="inventory_monitor",
    migration_weight=0.1,  # 10% Agent，90% fallback
    fallback_strategy="on_failure"
)
async def hourly_check():
    await legacy_hourly_check()

# Week 2: 50% Agent（观察效果）
# migration_weight=0.5

# Week 4: 100% Agent（完全迁移）
# migration_weight=1.0
# fallback_strategy="on_failure"  # 只在失败时使用 fallback
```

**阶段 4：移除 Fallback**

```python
# 完全由 Agent 接管
@app.cron(
    expression="0 * * * *",
    event_name="hourly_check",
    focus="inventory_monitor",
    fallback=None  # 不再提供 fallback
)
async def hourly_check():
    pass  # 函数体可以为空
```

### 10.2 迁移检查清单

- [ ] 识别所有现有的 cron 任务
- [ ] 评估每个任务的复杂度和风险
- [ ] 为每个任务创建对应的 Skills
- [ ] 封装原有逻辑为 fallback 函数
- [ ] 注册 Cron 触发器（初始 weight=0）
- [ ] 配置治理约束（成本、频率等）
- [ ] 设置监控和告警
- [ ] 逐步提高 Agent 权重
- [ ] 观察 Agent 决策质量
- [ ] 对比 Agent 和 fallback 的效果
- [ ] 完全切换到 Agent
- [ ] 移除 fallback 代码

### 10.3 回滚策略

```python
# 如果 Agent 决策质量不佳，可以快速回滚

# 方案 1：降低 Agent 权重
@app.cron(
    expression="0 * * * *",
    event_name="hourly_check",
    migration_weight=0.0,  # 回滚到 100% fallback
    fallback_strategy="always"
)
async def hourly_check():
    await legacy_hourly_check()

# 方案 2：暂停触发器
await app.cron_registry.pause_trigger("hourly_check")

# 方案 3：使用熔断器自动降级
# 配置熔断器，失败率 > 50% 时自动切换到 fallback
```

---

## 11. 最佳实践

### 11.1 Cron 表达式设计

```python
# ✅ 好的实践
@app.cron(expression="0 9 * * 1-5")  # 工作日 9:00
@app.cron(expression="*/15 * * * *")  # 每 15 分钟
@app.cron(expression="0 0 * * 0")     # 每周日 0:00

# ❌ 避免的实践
@app.cron(expression="* * * * *")     # 每分钟（太频繁）
@app.cron(expression="0 0 31 2 *")    # 2 月 31 日（不存在）
```

### 11.2 Focus 设计

```python
# ✅ 好的实践：使用清晰的 focus 标识符
@app.cron(
    expression="0 9 * * 1-5",
    focus="trading_decision"  # 明确的业务领域
)

# ✅ 好的实践：在 SKILL.md 中声明 focus
# ---
# focus: 
#   - trading_decision
#   - risk_management
# ---

# ❌ 避免的实践：过于宽泛的 focus
@app.cron(focus="general")  # 太宽泛，无法有效过滤 Skills
```

### 11.3 治理约束配置

```python
# ✅ 好的实践：为高频任务设置约束
@app.cron(
    expression="*/5 * * * *",  # 每 5 分钟
    max_cost_per_run=0.1,      # 单次成本上限
    max_daily_cost=5.0,        # 每日成本上限
    cooldown_seconds=60        # 冷却时间
)

# ✅ 好的实践：为关键任务配置 fallback
@app.cron(
    expression="0 9 * * 1-5",
    fallback_strategy="on_failure",
    max_retries=3
)

# ❌ 避免的实践：无约束的高频任务
@app.cron(expression="* * * * *")  # 无成本限制，可能导致费用失控
```

### 11.4 错误处理

```python
# ✅ 好的实践：提供有意义的 fallback
@app.cron(
    expression="0 * * * *",
    event_name="hourly_check"
)
async def hourly_check():
    """Fallback: 使用保守策略"""
    # 提供一个安全的默认行为
    await send_alert("Using fallback strategy")

# ✅ 好的实践：配置通知
@app.cron(
    expression="0 * * * *",
    event_name="critical_task",
    on_failure_notify=["admin@example.com"]
)

# ❌ 避免的实践：空的 fallback
@app.cron(expression="0 * * * *")
async def task():
    pass  # 失败时无任何处理
```

### 11.5 监控和告警

```python
# ✅ 好的实践：为关键任务配置告警
# prometheus_alerts.yml
groups:
  - name: owlclaw_cron
    rules:
      - alert: CronTaskFailureRate
        expr: |
          rate(owlclaw_cron_executions_total{status="failed"}[5m]) 
          / rate(owlclaw_cron_executions_total[5m]) > 0.5
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Cron task {{ $labels.event_name }} has high failure rate"
      
      - alert: CronTaskHighCost
        expr: |
          sum(rate(owlclaw_cron_execution_cost_usd[1h])) by (event_name) > 1.0
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Cron task {{ $labels.event_name }} has high cost"
```

---

## 12. 安全考虑

### 12.1 权限控制

```python
from owlclaw.governance import require_permission

@app.cron(
    expression="0 0 * * *",
    event_name="sensitive_task"
)
@require_permission("cron:execute:sensitive_task")
async def sensitive_task():
    """需要特定权限才能执行"""
    pass
```

### 12.2 敏感信息保护

```python
# ✅ 好的实践：使用环境变量
import os

@app.cron(expression="0 * * * *")
async def task_with_secrets():
    api_key = os.getenv("API_KEY")  # 从环境变量读取
    # 使用 api_key

# ❌ 避免的实践：硬编码敏感信息
@app.cron(expression="0 * * * *")
async def bad_task():
    api_key = "sk-1234567890"  # 不要硬编码
```

### 12.3 审计日志

```python
# 所有 Cron 执行自动记录到 Ledger
# 包括：
# - 触发时间
# - 执行者（系统/手动）
# - 执行结果
# - 成本和时长
# - 错误信息

# 查询审计日志
from owlclaw.governance.ledger import ledger

audit_logs = await ledger.query_events(
    event_type="cron_execution",
    event_name="sensitive_task",
    time_range=(start_date, end_date)
)
```

---

## 13. 故障排查

### 13.1 常见问题

**问题 1：Cron 任务未触发**

```python
# 检查清单：
# 1. 验证 Hatchet 连接
await app.cron_registry._check_hatchet()

# 2. 检查触发器是否启用
trigger = app.cron_registry.get_trigger("event_name")
print(trigger.enabled)

# 3. 检查 cron 表达式
from croniter import croniter
cron = croniter("0 * * * *")
print(cron.get_next(datetime))  # 下次触发时间

# 4. 查看 Hatchet 日志
# docker logs hatchet
```

**问题 2：Agent 决策失败率高**

```python
# 检查清单：
# 1. 查看执行历史
history = await app.cron_registry.get_execution_history("event_name")
for exec in history:
    if exec.status == ExecutionStatus.FAILED:
        print(exec.error_message)

# 2. 检查 Skills 是否正确加载
skills = await focus_manager.load_skills_for_focus("focus_name")
print(f"Loaded {len(skills)} skills")

# 3. 检查 LLM 调用
# 查看 Agent Run 日志

# 4. 降低 Agent 权重或启用 fallback
@app.cron(
    expression="0 * * * *",
    migration_weight=0.5,  # 降低到 50%
    fallback_strategy="on_failure"
)
```

**问题 3：成本超出预期**

```python
# 检查清单：
# 1. 查看成本统计
today_cost = await governance._sum_today_cost("event_name")
print(f"Today's cost: ${today_cost}")

# 2. 检查 LLM 调用次数
history = await app.cron_registry.get_execution_history("event_name")
avg_llm_calls = sum(e.llm_calls for e in history) / len(history)
print(f"Average LLM calls: {avg_llm_calls}")

# 3. 配置成本限制
@app.cron(
    expression="0 * * * *",
    max_cost_per_run=0.5,
    max_daily_cost=10.0
)

# 4. 优化 Skills（减少不必要的工具调用）
```

### 13.2 调试工具

```python
# 启用调试日志
import logging
logging.getLogger("owlclaw.triggers.cron").setLevel(logging.DEBUG)

# 手动触发并查看详细日志
await app.cron_registry.trigger_now("event_name")

# 查看 Prometheus 指标
# curl http://localhost:9090/metrics | grep owlclaw_cron

# 导出执行历史
history = await app.cron_registry.get_execution_history("event_name", limit=100)
import json
with open("execution_history.json", "w") as f:
    json.dump([e.__dict__ for e in history], f, indent=2, default=str)
```

---

## 14. 参考实现

### 14.1 完整示例

```python
# app.py
from owlclaw import OwlClawApp
from datetime import datetime

app = OwlClawApp()

# 示例 1：库存监控
@app.cron(
    expression="0 * * * *",
    event_name="inventory_check",
    focus="inventory_monitor",
    description="每小时检查库存水平",
    max_cost_per_run=0.5,
    max_daily_cost=10.0,
    cooldown_seconds=3600
)
async def hourly_inventory_check():
    """Fallback: 使用固定阈值检查"""
    from app.inventory import check_inventory_legacy
    await check_inventory_legacy()

# 示例 2：交易决策
@app.cron(
    expression="25 9 * * 1-5",
    event_name="morning_decision",
    focus="trading_decision",
    description="交易日开盘前决策",
    max_cost_per_run=2.0,
    priority=10  # 高优先级
)
async def morning_trading():
    """Fallback: 使用保守策略"""
    from app.trading import conservative_strategy
    await conservative_strategy()

# 示例 3：每日报告
@app.cron(
    expression="0 18 * * *",
    event_name="daily_report",
    focus="reporting",
    description="每日销售报告",
    fallback=None  # 必须由 Agent 生成
)
async def daily_report():
    pass

# 示例 4：数据清理
@app.cron(
    expression="0 2 * * *",
    event_name="data_cleanup",
    description="每日凌晨清理过期数据",
    max_duration=600  # 最多 10 分钟
)
async def data_cleanup():
    """Fallback: 清理 7 天前的数据"""
    from app.cleanup import cleanup_old_data
    await cleanup_old_data(days=7)

if __name__ == "__main__":
    app.run()
```

---

## 15. 总结

Cron Triggers 设计实现了以下核心目标：

1. **简单易用**：通过 `@app.cron` 装饰器，开发者只需几行代码即可注册定时任务
2. **可靠持久**：基于 Hatchet 的持久化 Cron 支持，保证任务不丢失
3. **智能决策**：Agent 根据 Skills 和上下文自主决策，而非执行固定脚本
4. **治理集成**：自动应用成本、频率、时间约束，并记录到 Ledger
5. **平滑迁移**：支持 fallback handler 和渐进式迁移，降低风险

通过这套设计，OwlClaw 将传统的定时任务调度提升到了 Agent 自主决策的新高度，同时保持了系统的可靠性和可控性。
