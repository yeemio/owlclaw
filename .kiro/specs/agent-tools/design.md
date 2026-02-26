# 设计文档

## 文档联动

- requirements: `.kiro/specs/agent-tools/requirements.md`
- design: `.kiro/specs/agent-tools/design.md`
- tasks: `.kiro/specs/agent-tools/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


## 简介

本文档描述了 OwlClaw Agent 内建工具的技术设计。内建工具是 Agent 的核心能力，使 Agent 能够：

1. **自我调度** — 通过 schedule_once/schedule_cron/cancel_schedule 工具
2. **管理记忆** — 通过 remember/recall 工具
3. **查询状态** — 通过 query_state 工具
4. **记录决策** — 通过 log_decision 工具

这些工具通过 LLM function calling 暴露给 Agent，让 Agent 自主决定何时使用。内建工具与业务 capabilities 的关键区别在于：
- **内建工具**：OwlClaw 提供，所有 Agent 都可用，用于 Agent 的自我管理
- **业务 capabilities**：业务应用注册，特定于业务领域，用于执行业务逻辑

## 架构例外声明（实现阶段需固化）

为保证设计与实现一致性，以下例外在本 spec 中显式声明：

1. 工具调度能力依赖 Hatchet 集成层，若调度后端不可用，需降级而非阻断整个 Agent 决策循环。
2. 工具执行审计必须进入治理 Ledger，不得使用独立旁路日志替代。
3. `alembic_version` 属于 Alembic 系统表，不适用业务表约束。

## 架构概览

```
Agent Run
  │
  ├─ LLM Function Calling
  │   ├─ 业务 capabilities (from registry)
  │   └─ 内建工具 (from built-in tools)
  │
  └─ 工具执行
      ├─ schedule_once/schedule_cron → Hatchet 集成
      ├─ cancel_schedule → Hatchet 集成
      ├─ remember → Memory System (MEMORY.md + Vector DB)
      ├─ recall → Memory System (Vector Search)
      ├─ query_state → Capability Registry (state providers)
      └─ log_decision → Governance Ledger
```

### 数据流

```
Agent Run 启动:
  构建 system prompt
    → 包含所有可见工具的 function calling schema
    → 内建工具 + 业务 capabilities

LLM 决策:
  选择工具调用
    → 可能是业务 capability
    → 可能是内建工具
    → 可能是多个工具的组合

工具执行:
  内建工具 → BuiltInTools 类
    → schedule_once → Hatchet.schedule_task()
    → remember → MemorySystem.write()
    → recall → MemorySystem.search()
    → query_state → CapabilityRegistry.get_state()
    → log_decision → GovernanceLedger.record()
  
  执行结果 → 返回给 LLM
    → LLM 可能继续调用更多工具
    → 直到 LLM 认为本次 run 完成
```

## 组件设计

### 1. BuiltInTools 类

**职责：** 实现所有内建工具的逻辑，提供统一的工具注册和调用接口。

#### 1.1 类定义

```python
from typing import Any, Optional
from datetime import timedelta
import asyncio

class BuiltInTools:
    """Built-in tools available to all Agents."""
    
    def __init__(
        self,
        hatchet_client,
        memory_system,
        capability_registry,
        governance_ledger,
    ):
        self.hatchet = hatchet_client
        self.memory = memory_system
        self.registry = capability_registry
        self.ledger = governance_ledger
        
        # Tool execution timeout (seconds)
        self.timeout = 30
        
        # Maximum tool calls per Agent Run (防止死循环)
        self.max_calls_per_run = 50
    
    def get_tool_schemas(self) -> list[dict]:
        """
        Get function calling schemas for all built-in tools.
        
        Returns list of OpenAI function calling schema dicts.
        """
        return [
            self._schedule_once_schema(),
            self._schedule_cron_schema(),
            self._cancel_schedule_schema(),
            self._remember_schema(),
            self._recall_schema(),
            self._query_state_schema(),
            self._log_decision_schema(),
        ]
    
    async def execute(
        self, 
        tool_name: str, 
        arguments: dict,
        context: dict,
    ) -> Any:
        """
        Execute a built-in tool by name.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments from LLM function call
            context: Agent run context (agent_id, run_id, etc.)
        
        Returns:
            Tool execution result
        
        Raises:
            ValueError: If tool_name is unknown
            TimeoutError: If tool execution exceeds timeout
            RuntimeError: If tool execution fails
        """
        # Map tool names to methods
        tool_methods = {
            "schedule_once": self.schedule_once,
            "schedule_cron": self.schedule_cron,
            "cancel_schedule": self.cancel_schedule,
            "remember": self.remember,
            "recall": self.recall,
            "query_state": self.query_state,
            "log_decision": self.log_decision,
        }
        
        method = tool_methods.get(tool_name)
        if not method:
            raise ValueError(f"Unknown built-in tool: {tool_name}")
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                method(**arguments, context=context),
                timeout=self.timeout
            )
            
            # Record to ledger
            await self.ledger.record_tool_call(
                agent_id=context["agent_id"],
                run_id=context["run_id"],
                tool_name=tool_name,
                arguments=arguments,
                result=result,
                success=True,
            )
            
            return result
            
        except asyncio.TimeoutError:
            await self.ledger.record_tool_call(
                agent_id=context["agent_id"],
                run_id=context["run_id"],
                tool_name=tool_name,
                arguments=arguments,
                error="Timeout",
                success=False,
            )
            raise TimeoutError(
                f"Tool '{tool_name}' execution exceeded {self.timeout}s timeout"
            )
        
        except Exception as e:
            await self.ledger.record_tool_call(
                agent_id=context["agent_id"],
                run_id=context["run_id"],
                tool_name=tool_name,
                arguments=arguments,
                error=str(e),
                success=False,
            )
            raise RuntimeError(
                f"Tool '{tool_name}' execution failed: {e}"
            ) from e
```



#### 1.2 调度工具实现

```python
    # ── Schedule Once ──
    
    def _schedule_once_schema(self) -> dict:
        """Function calling schema for schedule_once tool."""
        return {
            "name": "schedule_once",
            "description": (
                "Schedule a one-time delayed Agent run. "
                "Use this when you need to check something later or wait for an event."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "delay_seconds": {
                        "type": "integer",
                        "description": (
                            "Delay in seconds before the next Agent run "
                            "(minimum: 1, maximum: 2592000)"
                        ),
                        "minimum": 1,
                        "maximum": 2592000,
                    },
                    "focus": {
                        "type": "string",
                        "description": (
                            "What to focus on in the next run "
                            "(e.g., 'check entry opportunities', 'review market state')"
                        ),
                    },
                },
                "required": ["delay_seconds", "focus"],
            },
        }
    
    async def schedule_once(
        self,
        delay_seconds: int,
        focus: str,
        context: dict,
    ) -> dict:
        """
        Schedule a one-time delayed Agent run.
        
        Args:
            delay_seconds: Delay in seconds (1 to 2592000)
            focus: What to focus on in the next run
            context: Agent run context
        
        Returns:
            {"schedule_id": str, "scheduled_at": str}
        """
        # Validate delay
        if delay_seconds < 1 or delay_seconds > 2592000:
            raise ValueError(
                f"delay_seconds must be between 1 and 2592000, got {delay_seconds}"
            )
        
        # Schedule via Hatchet
        schedule_id = await self.hatchet.schedule_task(
            task_name="agent_run",
            delay=timedelta(seconds=delay_seconds),
            payload={
                "agent_id": context["agent_id"],
                "trigger": "schedule_once",
                "focus": focus,
                "scheduled_by_run_id": context["run_id"],
            },
        )
        
        return {
            "schedule_id": schedule_id,
            "scheduled_at": f"in {delay_seconds} seconds",
            "focus": focus,
        }
    
    # ── Schedule Cron ──
    
    def _schedule_cron_schema(self) -> dict:
        """Function calling schema for schedule_cron tool."""
        return {
            "name": "schedule_cron",
            "description": (
                "Schedule a recurring Agent run using cron expression. "
                "Use this for periodic checks (e.g., every hour during trading hours)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "cron_expression": {
                        "type": "string",
                        "description": (
                            "Cron expression (format: 'minute hour day month weekday', "
                            "e.g., '0 9 * * 1-5' for 9am on weekdays)"
                        ),
                    },
                    "focus": {
                        "type": "string",
                        "description": (
                            "What to focus on in each run "
                            "(e.g., 'morning market analysis', 'hourly position check')"
                        ),
                    },
                },
                "required": ["cron_expression", "focus"],
            },
        }
    
    async def schedule_cron(
        self,
        cron_expression: str,
        focus: str,
        context: dict,
    ) -> dict:
        """
        Schedule a recurring Agent run using cron expression.
        
        Args:
            cron_expression: Cron expression (standard format)
            focus: What to focus on in each run
            context: Agent run context
        
        Returns:
            {"schedule_id": str, "cron_expression": str}
        """
        # Validate cron expression
        if not self._validate_cron_expression(cron_expression):
            raise ValueError(f"Invalid cron expression: {cron_expression}")
        
        # Schedule via Hatchet
        schedule_id = await self.hatchet.schedule_cron(
            task_name="agent_run",
            cron_expression=cron_expression,
            payload={
                "agent_id": context["agent_id"],
                "trigger": "schedule_cron",
                "focus": focus,
                "scheduled_by_run_id": context["run_id"],
            },
        )
        
        return {
            "schedule_id": schedule_id,
            "cron_expression": cron_expression,
            "focus": focus,
        }
    
    def _validate_cron_expression(self, expr: str) -> bool:
        """Validate cron expression format."""
        # Simple validation: 5 fields separated by spaces
        parts = expr.split()
        if len(parts) != 5:
            return False
        
        # Placeholder: production implementation should validate with croniter
        return True
    
    # ── Cancel Schedule ──
    
    def _cancel_schedule_schema(self) -> dict:
        """Function calling schema for cancel_schedule tool."""
        return {
            "name": "cancel_schedule",
            "description": (
                "Cancel a previously scheduled Agent run. "
                "Use this when the scheduled task is no longer needed."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "schedule_id": {
                        "type": "string",
                        "description": "The ID returned by schedule_once or schedule_cron",
                    },
                },
                "required": ["schedule_id"],
            },
        }
    
    async def cancel_schedule(
        self,
        schedule_id: str,
        context: dict,
    ) -> dict:
        """
        Cancel a previously scheduled Agent run.
        
        Args:
            schedule_id: Schedule ID to cancel
            context: Agent run context
        
        Returns:
            {"success": bool, "message": str}
        """
        # Cancel via Hatchet
        success = await self.hatchet.cancel_task(schedule_id)
        
        if success:
            return {
                "success": True,
                "message": f"Schedule {schedule_id} cancelled successfully",
            }
        else:
            return {
                "success": False,
                "message": f"Schedule {schedule_id} not found or already completed",
            }
```

#### 1.3 记忆工具实现

```python
    # ── Remember ──
    
    def _remember_schema(self) -> dict:
        """Function calling schema for remember tool."""
        return {
            "name": "remember",
            "description": (
                "Store important information in long-term memory. "
                "Use this to remember lessons, patterns, or decisions for future reference."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": (
                            "What to remember (e.g., 'After sharp market drop, "
                            "rebound signals are usually accurate within 2 hours')"
                        ),
                        "maxLength": 2000,
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Optional tags for categorization "
                            "(e.g., ['trading', 'lesson', 'volatility'])"
                        ),
                    },
                },
                "required": ["content"],
            },
        }
    
    async def remember(
        self,
        content: str,
        tags: Optional[list[str]] = None,
        context: dict = None,
    ) -> dict:
        """
        Store information in long-term memory.
        
        Args:
            content: What to remember (max 2000 chars)
            tags: Optional tags for categorization
            context: Agent run context
        
        Returns:
            {"memory_id": str, "timestamp": str}
        """
        # Validate content
        if not content or len(content) == 0:
            raise ValueError("content cannot be empty")
        
        if len(content) > 2000:
            raise ValueError(f"content exceeds 2000 characters (got {len(content)})")
        
        # Write to memory system
        memory_id = await self.memory.write(
            agent_id=context["agent_id"],
            content=content,
            tags=tags or [],
            run_id=context["run_id"],
        )
        
        return {
            "memory_id": memory_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    # ── Recall ──
    
    def _recall_schema(self) -> dict:
        """Function calling schema for recall tool."""
        return {
            "name": "recall",
            "description": (
                "Search long-term memory for relevant past experiences. "
                "Use this when you need to remember similar situations or lessons."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "What to search for (e.g., 'market crash recovery patterns', "
                            "'entry timing lessons')"
                        ),
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of memories to return (default: 5, max: 20)",
                        "minimum": 1,
                        "maximum": 20,
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        }
    
    async def recall(
        self,
        query: str,
        limit: int = 5,
        context: dict = None,
    ) -> dict:
        """
        Search long-term memory for relevant experiences.
        
        Args:
            query: What to search for
            limit: Maximum number of memories to return (1-20)
            context: Agent run context
        
        Returns:
            {"memories": list[dict], "count": int}
        """
        # Validate limit
        if limit < 1 or limit > 20:
            raise ValueError(f"limit must be between 1 and 20, got {limit}")
        
        # Search memory system
        memories = await self.memory.search(
            agent_id=context["agent_id"],
            query=query,
            limit=limit,
        )
        
        return {
            "memories": memories,
            "count": len(memories),
        }
```

#### 1.4 状态查询和决策记录工具实现

```python
    # ── Query State ──
    
    def _query_state_schema(self) -> dict:
        """Function calling schema for query_state tool."""
        return {
            "name": "query_state",
            "description": (
                "Query current business state. "
                "Use this to get up-to-date information before making decisions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "state_name": {
                        "type": "string",
                        "description": (
                            "Name of the state to query "
                            "(e.g., 'market_state', 'position_summary', 'account_balance')"
                        ),
                    },
                },
                "required": ["state_name"],
            },
        }
    
    async def query_state(
        self,
        state_name: str,
        context: dict,
    ) -> dict:
        """
        Query current business state.
        
        Args:
            state_name: Name of the state to query
            context: Agent run context
        
        Returns:
            State data (dict)
        """
        # Query via capability registry
        state_data = await self.registry.get_state(state_name)
        
        return state_data
    
    # ── Log Decision ──
    
    def _log_decision_schema(self) -> dict:
        """Function calling schema for log_decision tool."""
        return {
            "name": "log_decision",
            "description": (
                "Log your decision reasoning for audit and analysis. "
                "Use this to explain why you chose a particular action or decided not to act."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": (
                            "Explanation of your decision (e.g., 'Market volatility is too high, "
                            "waiting for stabilization before entry')"
                        ),
                        "maxLength": 1000,
                    },
                    "decision_type": {
                        "type": "string",
                        "enum": ["capability_selection", "schedule_decision", "no_action", "other"],
                        "description": "Type of decision being logged",
                        "default": "other",
                    },
                },
                "required": ["reasoning"],
            },
        }
    
    async def log_decision(
        self,
        reasoning: str,
        decision_type: str = "other",
        context: dict = None,
    ) -> dict:
        """
        Log decision reasoning for audit.
        
        Args:
            reasoning: Explanation of the decision (max 1000 chars)
            decision_type: Type of decision
            context: Agent run context
        
        Returns:
            {"decision_id": str, "timestamp": str}
        """
        # Validate reasoning
        if not reasoning or len(reasoning) == 0:
            raise ValueError("reasoning cannot be empty")
        
        if len(reasoning) > 1000:
            raise ValueError(f"reasoning exceeds 1000 characters (got {len(reasoning)})")
        
        # Record to ledger
        decision_id = await self.ledger.record_decision(
            agent_id=context["agent_id"],
            run_id=context["run_id"],
            reasoning=reasoning,
            decision_type=decision_type,
        )
        
        return {
            "decision_id": decision_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
```


## 数据模型

### 工具调用上下文

```python
{
    "agent_id": "mionyee-trading",
    "run_id": "run_20260210_173000_abc123",
    "trigger": "schedule_once",  # 或 "cron", "webhook", "heartbeat"
    "focus": "check entry opportunities",  # 可选，来自调度
}
```

### 调度任务 Payload

```python
{
    "agent_id": "mionyee-trading",
    "trigger": "schedule_once",  # 或 "schedule_cron"
    "focus": "check entry opportunities",
    "scheduled_by_run_id": "run_20260210_173000_abc123",
}
```

### 记忆条目结构

```python
{
    "memory_id": "mem_20260210_173000_xyz789",
    "agent_id": "mionyee-trading",
    "content": "After sharp market drop, rebound signals are usually accurate within 2 hours",
    "tags": ["trading", "lesson", "volatility"],
    "timestamp": "2026-02-10T17:30:00Z",
    "run_id": "run_20260210_173000_abc123",
    "embedding": [0.123, 0.456, ...],  # 向量表示
}
```

### 决策日志结构

```python
{
    "decision_id": "dec_20260210_173000_def456",
    "agent_id": "mionyee-trading",
    "run_id": "run_20260210_173000_abc123",
    "reasoning": "Market volatility is too high, waiting for stabilization before entry",
    "decision_type": "no_action",
    "timestamp": "2026-02-10T17:30:00Z",
}
```

### Ledger 记录结构

```python
{
    "record_id": "rec_20260210_173000_ghi789",
    "agent_id": "mionyee-trading",
    "run_id": "run_20260210_173000_abc123",
    "tool_name": "schedule_once",
    "arguments": {
        "delay_seconds": 300,
        "focus": "check entry opportunities"
    },
    "result": {
        "schedule_id": "sch_20260210_173500_jkl012",
        "scheduled_at": "in 300 seconds",
        "focus": "check entry opportunities"
    },
    "success": true,
    "error": null,
    "timestamp": "2026-02-10T17:30:00Z",
    "duration_ms": 45,
}
```

## 错误处理

### 1. 参数验证错误

```python
# 场景：delay_seconds 超出范围
# 行为：抛出 ValueError，不执行工具

ValueError: delay_seconds must be between 1 and 2592000, got 3000000
```

### 2. 工具不存在错误

```python
# 场景：execute() 调用未知工具
# 行为：抛出 ValueError

ValueError: Unknown built-in tool: unknown_tool
```

### 3. 工具执行超时

```python
# 场景：工具执行超过 30 秒
# 行为：抛出 TimeoutError，记录到 Ledger

TimeoutError: Tool 'query_state' execution exceeded 30s timeout
```

### 4. 依赖组件失败

```python
# 场景：Hatchet 调用失败
# 行为：抛出 RuntimeError，包含原始错误信息

RuntimeError: Tool 'schedule_once' execution failed: 
  HatchetError: Failed to schedule task
```

### 5. 状态提供者不存在

```python
# 场景：query_state 调用不存在的 state_name
# 行为：抛出 ValueError（来自 Capability Registry）

ValueError: No state provider registered for 'unknown_state'
```

### 6. 记忆系统错误

```python
# 场景：向量数据库连接失败
# 行为：抛出 RuntimeError

RuntimeError: Tool 'recall' execution failed: 
  VectorDBError: Connection timeout
```

## 性能考虑

### 1. 工具调用延迟

**目标：** P95 < 500ms（不包括状态查询的业务逻辑耗时）

**优化措施：**
- 调度工具（schedule_once/schedule_cron/cancel_schedule）直接调用 Hatchet API，延迟 < 100ms
- 记忆工具（remember）异步写入，不阻塞返回
- 状态查询工具（query_state）支持缓存（由 state provider 配置）
- 决策记录工具（log_decision）批量写入 Ledger

### 2. 向量搜索优化

**目标：** recall 工具 P95 < 200ms

**优化措施：**
- 使用高性能向量数据库（如 pgvector、Qdrant）
- 限制搜索结果数量（最多 20 条）
- 索引优化（HNSW 或 IVF）
- 查询缓存（相同 query 在短时间内返回缓存结果）

### 3. 并发控制

**问题：** 多个工具并发调用可能导致资源竞争。

**解决方案：**
- 调度工具：Hatchet 自身支持高并发
- 记忆工具：向量数据库支持并发写入
- 状态查询工具：只读操作，无竞争
- 决策记录工具：Ledger 支持并发写入

### 4. 内存管理

**问题：** MEMORY.md 文件可能无限增长。

**解决方案：**
- 设置文件大小阈值（如 10MB）
- 超过阈值时自动归档旧记忆
- 归档策略：保留最近 3 个月的记忆，旧记忆移至归档表
- 向量索引仅包含活跃记忆

## 测试策略

### 1. 单元测试

**覆盖范围：**
- 所有工具的 schema 生成
- 所有工具的参数验证
- 所有工具的成功场景
- 所有工具的错误场景
- execute() 方法的路由逻辑
- execute() 方法的超时机制
- execute() 方法的 Ledger 记录

**Mock 对象：**
- Hatchet 客户端（mock schedule_task/schedule_cron/cancel_task）
- Memory System（mock write/search）
- Capability Registry（mock get_state）
- Governance Ledger（mock record_tool_call/record_decision）

**测试框架：**
- pytest + pytest-asyncio
- pytest-mock（mock 对象）
- pytest-cov（覆盖率）

### 2. 集成测试

**测试场景：**
- 调度工具与 Hatchet 的真实集成
- 记忆工具与向量数据库的真实集成
- 状态查询工具与 Capability Registry 的真实集成
- 决策记录工具与 Governance Ledger 的真实集成

**测试环境：**
- Docker Compose（Hatchet Server + PostgreSQL + Vector DB）
- 测试数据库（隔离的 schema）
- 清理策略（每个测试后清理数据）

### 3. 端到端测试

**测试场景：**
- Agent Run 调用 schedule_once → Hatchet 任务执行 → 新的 Agent Run 触发
- Agent Run 调用 remember → 写入 MEMORY.md 和向量数据库 → 后续 Agent Run 调用 recall → 返回记忆
- Agent Run 调用 query_state → 返回状态 → Agent 基于状态做决策
- Agent Run 调用 log_decision → 写入 Ledger → 审计查询返回决策日志

**验证点：**
- 工具调用成功
- 数据持久化正确
- 跨 Agent Run 的数据一致性
- Ledger 记录完整

### 4. 性能测试

**测试指标：**
- 工具调用延迟（P50/P95/P99）
- 向量搜索延迟（P50/P95/P99）
- 并发工具调用吞吐量
- 内存使用情况

**测试工具：**
- locust（负载测试）
- pytest-benchmark（性能基准）

## 依赖关系

### 外部依赖

- **Hatchet Python SDK** (hatchet-sdk): 调度工具依赖
- **向量数据库客户端** (如 pgvector, qdrant-client): 记忆工具依赖
- **asyncio** (标准库): 异步执行和超时控制
- **datetime** (标准库): 时间处理

### 内部依赖

- **owlclaw.integrations.hatchet**: Hatchet 客户端封装
- **owlclaw.agent.memory**: Memory System（待实现）
- **owlclaw.capabilities.registry**: Capability Registry
- **owlclaw.governance.ledger**: Governance Ledger（待实现）
- **owlclaw.agent.runtime**: Agent Runtime 将使用 BuiltInTools

### 依赖注入

BuiltInTools 通过构造函数接受所有依赖，便于测试和替换：

```python
# 生产环境
tools = BuiltInTools(
    hatchet_client=hatchet_client,
    memory_system=memory_system,
    capability_registry=registry,
    governance_ledger=ledger,
)

# 测试环境
tools = BuiltInTools(
    hatchet_client=mock_hatchet,
    memory_system=mock_memory,
    capability_registry=mock_registry,
    governance_ledger=mock_ledger,
)
```

## 未来扩展

### 1. 工具插件机制

**需求：** 允许业务应用注册自定义内建工具。

**实现：**
```python
class BuiltInTools:
    def register_custom_tool(
        self,
        name: str,
        schema: dict,
        handler: Callable,
    ):
        """Register a custom built-in tool."""
        self.tool_methods[name] = handler
        self._custom_schemas.append(schema)
```

### 2. 工具执行的重试机制

**需求：** 对于幂等工具（如 query_state、recall），支持自动重试。

**实现：**
```python
async def execute(self, tool_name: str, arguments: dict, context: dict):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return await self._execute_once(tool_name, arguments, context)
        except RetryableError as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)  # 指数退避
```

### 3. 工具执行的 A/B 测试

**需求：** 支持不同 Agent 实例使用不同版本的工具。

**实现：**
```python
class BuiltInTools:
    def __init__(self, ..., version: str = "v1"):
        self.version = version
        if version == "v2":
            self.tool_methods["schedule_once"] = self.schedule_once_v2
```

### 4. 工具执行的限流

**需求：** 防止 Agent 滥用工具（如频繁调用 schedule_once）。

**实现：**
```python
class BuiltInTools:
    def __init__(self, ..., rate_limiter):
        self.rate_limiter = rate_limiter
    
    async def execute(self, tool_name: str, ...):
        if not await self.rate_limiter.check(tool_name, context["agent_id"]):
            raise RateLimitError(f"Tool '{tool_name}' rate limit exceeded")
        ...
```

### 5. 工具执行的成本追踪

**需求：** 追踪每个工具调用的成本（LLM token、数据库查询、API 调用）。

**实现：**
```python
async def execute(self, tool_name: str, ...):
    cost_tracker = CostTracker()
    result = await method(**arguments, context=context, cost_tracker=cost_tracker)
    
    await self.ledger.record_tool_call(
        ...,
        cost=cost_tracker.total_cost,
    )
```

## 安全考虑

### 1. 参数 Sanitization

**风险：** 恶意参数可能导致注入攻击。

**缓解：**
- remember 工具的 content 进行 HTML/SQL 转义
- schedule_once 的 focus 限制长度和字符集
- query_state 的 state_name 仅允许字母数字和下划线

### 2. 调度频率限制

**风险：** Agent 可能创建大量调度任务，耗尽资源。

**缓解：**
- 单个 Agent 实例最多 100 个活跃调度任务
- schedule_cron 的最小间隔为 1 分钟
- 超过限制时返回错误

### 3. 记忆容量限制

**风险：** Agent 可能写入大量记忆，耗尽存储。

**缓解：**
- 单条记忆最大 2000 字符
- 单个 Agent 实例最多 10,000 条记忆
- 超过限制时自动清理最旧的记忆

### 4. 状态查询范围限制

**风险：** query_state 可能暴露敏感内部状态。

**缓解：**
- 仅允许查询注册的 state providers
- state providers 负责过滤敏感字段
- 治理层可以进一步限制可见的 state

### 5. 审计日志完整性

**风险：** 工具调用未被记录，导致审计缺失。

**缓解：**
- 所有工具调用都记录到 Ledger（成功和失败）
- Ledger 记录不可篡改（append-only）
- 定期审计 Ledger 完整性

### 6. 权限验证

**风险：** Agent 可能取消其他 Agent 的调度任务。

**缓解：**
- cancel_schedule 验证 schedule_id 是否属于当前 Agent
- Hatchet payload 包含 scheduled_by_run_id，用于验证所有权
- 跨 Agent 操作需要额外权限（企业版）

## 与 Agent Runtime 的集成

BuiltInTools 将被 Agent Runtime 使用，集成方式如下：

```python
# owlclaw/agent/runtime/runtime.py
class AgentRuntime:
    def __init__(self, ...):
        self.built_in_tools = BuiltInTools(
            hatchet_client=self.hatchet,
            memory_system=self.memory,
            capability_registry=self.registry,
            governance_ledger=self.ledger,
        )
    
    async def run(self, trigger: str, context: dict):
        # 1. 构建 system prompt
        tool_schemas = self.built_in_tools.get_tool_schemas()
        capability_schemas = self.registry.get_capability_schemas()
        
        system_prompt = self._build_prompt(
            tools=tool_schemas + capability_schemas,
            ...
        )
        
        # 2. LLM function calling
        response = await self.llm.chat(
            messages=[{"role": "system", "content": system_prompt}, ...],
            tools=tool_schemas + capability_schemas,
        )
        
        # 3. 执行工具调用
        for tool_call in response.tool_calls:
            if tool_call.name in [t["name"] for t in tool_schemas]:
                # 内建工具
                result = await self.built_in_tools.execute(
                    tool_name=tool_call.name,
                    arguments=tool_call.arguments,
                    context=context,
                )
            else:
                # 业务 capability
                result = await self.registry.invoke_handler(
                    skill_name=tool_call.name,
                    **tool_call.arguments,
                )
            
            # 4. 将结果返回给 LLM（可能继续调用更多工具）
            ...
```

## 参考

- 业界 Agent 框架的 memory-tool 和 schedule-tool 实现
- OpenAI Function Calling 文档
- Hatchet Python SDK 文档
- OwlClaw 架构文档 docs/ARCHITECTURE_ANALYSIS.md §5.2.1（Agent 内建工具）
- Agent Skills 规范（agentskills.io）
