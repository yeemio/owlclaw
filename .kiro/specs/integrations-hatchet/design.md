# 设计文档

## 简介

本文档描述 OwlClaw 与 Hatchet 的集成设计。Hatchet 为 OwlClaw 提供持久化任务执行、Cron 调度和自我调度能力。集成采用隔离设计，所有 Hatchet 相关代码集中在 `owlclaw/integrations/hatchet.py` 中，便于未来替换或支持其他持久执行引擎（如 Temporal）。

## 架构概览

```
OwlClaw 应用
    ↓
owlclaw/integrations/hatchet.py (隔离层)
    ↓
Hatchet Python SDK
    ↓
Hatchet Server (Go)
    ↓
PostgreSQL (共用实例)
```

### 集成边界

**OwlClaw 自建部分：**
- Agent 运行时（身份、记忆、知识、决策）
- 能力注册和 Skills 挂载
- 治理层（可见性过滤、Ledger）
- 触发器统一层

**Hatchet 提供部分：**
- 持久化任务执行（崩溃恢复、重试）
- Cron 调度（内建一等公民）
- 延迟执行和自我调度
- 任务队列和并发控制

**隔离层职责：**
- 封装 Hatchet SDK 的复杂性
- 提供 OwlClaw 风格的 API
- 处理配置和连接管理
- 记录日志和错误



## 组件设计

### 1. HatchetClient

**职责：** 封装 Hatchet SDK，提供 OwlClaw 风格的 API。

#### 1.1 类定义

```python
from hatchet_sdk import Hatchet
from typing import Optional, Callable, Any
from pathlib import Path
import yaml

class HatchetConfig:
    """Hatchet 连接配置（使用 Pydantic）"""
    
    server_url: str = "http://localhost:7077"
    api_token: Optional[str] = None
    namespace: str = "owlclaw"
    mode: str = "production"  # "production" or "lite"
    
    # PostgreSQL 配置（共用实例）
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "owlclaw"
    postgres_user: str = "owlclaw"
    postgres_password: str = ""
    
    # Worker 配置
    max_concurrent_tasks: int = 10
    worker_name: Optional[str] = None
    
    @classmethod
    def from_yaml(cls, config_path: Path) -> "HatchetConfig":
        """从 owlclaw.yaml 加载配置"""
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        hatchet_config = config.get("hatchet", {})
        return cls(**hatchet_config)


class HatchetClient:
    """OwlClaw 对 Hatchet SDK 的封装客户端"""
    
    def __init__(self, config: HatchetConfig):
        self.config = config
        self._client: Optional[Hatchet] = None
        self._workflows: dict[str, Any] = {}
    
    def connect(self) -> None:
        """建立与 Hatchet Server 的连接"""
        try:
            self._client = Hatchet(
                server_url=self.config.server_url,
                token=self.config.api_token,
                namespace=self.config.namespace,
            )
            print(f"Connected to Hatchet Server at {self.config.server_url}")
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to Hatchet Server: {e}"
            ) from e
    
    def disconnect(self) -> None:
        """优雅关闭连接"""
        if self._client:
            # Hatchet SDK 的清理逻辑
            self._client = None
            print("Disconnected from Hatchet Server")
    
    def task(
        self,
        name: Optional[str] = None,
        cron: Optional[str] = None,
        retries: int = 3,
        timeout: Optional[int] = None,
        priority: int = 0,
    ):
        """
        装饰器：将函数标记为持久化任务
        
        Args:
            name: 任务名称（默认使用函数名）
            cron: Cron 表达式（可选，用于周期性任务）
            retries: 重试次数
            timeout: 超时时间（秒）
            priority: 优先级（数字越大优先级越高）
        
        Example:
            @hatchet.task(name="agent-run", retries=3)
            async def agent_run(ctx, trigger_event):
                # Agent 运行逻辑
                ...
        """
        def decorator(func: Callable) -> Callable:
            task_name = name or func.__name__
            
            # 注册为 Hatchet Workflow
            workflow = self._client.workflow(
                name=task_name,
                on_cron=cron,
                timeout=timeout,
            )
            
            # 注册步骤
            step = workflow.step(
                name=f"{task_name}_step",
                retries=retries,
                timeout=timeout,
            )(func)
            
            self._workflows[task_name] = workflow
            
            return func
        
        return decorator
    
    async def schedule_task(
        self,
        task_name: str,
        delay_seconds: int,
        **kwargs
    ) -> str:
        """
        调度延迟执行的任务
        
        Args:
            task_name: 任务名称
            delay_seconds: 延迟秒数
            **kwargs: 任务参数
        
        Returns:
            任务 ID
        """
        if delay_seconds <= 0:
            raise ValueError("delay_seconds must be positive")
        
        workflow = self._workflows.get(task_name)
        if not workflow:
            raise ValueError(f"Task '{task_name}' not registered")
        
        # 使用 Hatchet 的延迟执行
        run = await self._client.admin.run_workflow(
            workflow_name=task_name,
            input=kwargs,
            options={"delay": f"{delay_seconds}s"},
        )
        
        return run.workflow_run_id
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消已调度的任务"""
        try:
            await self._client.admin.cancel_workflow_run(task_id)
            return True
        except Exception as e:
            print(f"Failed to cancel task {task_id}: {e}")
            return False
    
    async def get_task_status(self, task_id: str) -> dict:
        """查询任务状态"""
        run = await self._client.admin.get_workflow_run(task_id)
        
        return {
            "id": run.workflow_run_id,
            "status": run.status,  # pending, running, completed, failed, cancelled
            "started_at": run.started_at,
            "finished_at": run.finished_at,
        }
    
    async def list_scheduled_tasks(self) -> list[dict]:
        """列出所有已调度的任务"""
        runs = await self._client.admin.list_workflow_runs(
            status="pending"
        )
        
        return [
            {
                "id": run.workflow_run_id,
                "workflow": run.workflow_name,
                "scheduled_at": run.created_at,
            }
            for run in runs
        ]
    
    def start_worker(self) -> None:
        """启动 Worker 进程"""
        worker_name = self.config.worker_name or f"owlclaw-worker-{os.getpid()}"
        
        self._client.worker(
            name=worker_name,
            max_runs=self.config.max_concurrent_tasks,
        ).start()
```



### 2. 持久化定时（Durable Sleep）

**实现：** 使用 Hatchet Context 的 `aio_sleep_for` 方法。

```python
@hatchet.task(name="agent-heartbeat")
async def heartbeat_check(ctx):
    """Agent Heartbeat 检查"""
    
    # 检查是否有待处理事件
    pending_events = await collect_pending_events()
    
    if not pending_events:
        # 无事可做，持久化定时 30 分钟后再检查
        await ctx.aio_sleep_for(30 * 60)  # 1800 秒
        
        # 进程重启后会从这里继续执行
        return await heartbeat_check(ctx)
    
    # 有事件，触发 Agent Run
    await agent_run(ctx, trigger="heartbeat", events=pending_events)
```

**关键特性：**
- `ctx.aio_sleep_for()` 将定时状态持久化到 PostgreSQL
- Worker 进程崩溃后，Hatchet Server 会在 Worker 重启后恢复定时
- 定时到期后，任务从 `aio_sleep_for()` 之后的代码继续执行

### 3. Agent 自我调度

**实现：** 任务内部调用 `schedule_task` 实现自我调度。

```python
@hatchet.task(name="agent-run")
async def agent_run(ctx, trigger_event: dict):
    """Agent Run 生命周期"""
    
    # 1. 组装 System Prompt（身份、记忆、知识）
    prompt = build_agent_prompt(trigger_event)
    
    # 2. LLM Function Calling
    response = await llm_function_calling(prompt, available_tools)
    
    # 3. 执行 function calls
    for call in response.function_calls:
        if call.name == "schedule_once":
            # Agent 自我调度
            delay = call.arguments["delay"]
            focus = call.arguments["focus"]
            
            # 调度下一次 Agent Run
            await hatchet.schedule_task(
                task_name="agent-run",
                delay_seconds=delay,
                trigger_event={
                    "type": "self_scheduled",
                    "focus": focus,
                }
            )
        else:
            # 执行业务能力
            await registry.invoke_handler(call.name, **call.arguments)
    
    # 4. 记录到 Ledger
    await ledger.record(run_id, response, results)
```

**关键特性：**
- Agent 通过 `schedule_once` 工具自己决定下次执行时间
- 不需要外部循环或固定的 Cron 表达式
- 支持动态调整检查频率（市场波动大时缩短间隔）



### 4. Cron 触发器集成

**实现：** 使用 Hatchet 的 `on_cron` 参数。

```python
@hatchet.task(
    name="periodic-check",
    cron="*/60 * * * * *",  # 每 60 秒
)
async def periodic_check(ctx):
    """周期性检查（盘中每 60 秒）"""
    
    # 检查约束（交易时间）
    if not is_trading_time():
        # 非交易时间，跳过
        return
    
    # 触发 Agent Run
    await agent_run(ctx, trigger_event={
        "type": "cron",
        "name": "periodic-check",
    })
```

**关键特性：**
- Hatchet 内建 Cron 支持，无需额外的 Cron 守护进程
- Cron 表达式标准格式：`分 时 日 月 周`
- 支持复杂的 Cron 表达式（如 `0 9 * * 1-5` 工作日早上 9 点）

### 5. 配置管理

**owlclaw.yaml 示例：**

```yaml
# OwlClaw 配置
app:
  name: mionyee-trading
  
# Hatchet 集成配置
hatchet:
  # 连接配置
  server_url: http://localhost:7077
  api_token: ${HATCHET_API_TOKEN}  # 从环境变量读取
  namespace: owlclaw
  mode: production  # "production" or "lite"
  
  # PostgreSQL 配置（共用实例）
  postgres_host: localhost
  postgres_port: 5432
  postgres_db: owlclaw
  postgres_user: owlclaw
  postgres_password: ${POSTGRES_PASSWORD}
  
  # Worker 配置
  max_concurrent_tasks: 10
  worker_name: owlclaw-worker-1
```

**配置加载：**

```python
from owlclaw.integrations.hatchet import HatchetClient, HatchetConfig

# 从 owlclaw.yaml 加载配置
config = HatchetConfig.from_yaml("owlclaw.yaml")

# 初始化客户端
hatchet = HatchetClient(config)
hatchet.connect()
```



## 部署架构

### 开发模式（Hatchet Lite）

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: owlclaw
      POSTGRES_USER: owlclaw
      POSTGRES_PASSWORD: owlclaw
    ports:
      - "5432:5432"
  
  hatchet-lite:
    image: ghcr.io/hatchet-dev/hatchet/hatchet-lite:latest
    environment:
      DATABASE_URL: postgresql://owlclaw:owlclaw@postgres:5432/owlclaw
      SERVER_PORT: 7077
    ports:
      - "7077:7077"
    depends_on:
      - postgres
```

**启动：**
```bash
docker-compose up -d
```

### 生产模式

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: owlclaw
      POSTGRES_USER: owlclaw
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
  
  hatchet-server:
    image: ghcr.io/hatchet-dev/hatchet/hatchet-engine:latest
    environment:
      DATABASE_URL: postgresql://owlclaw:${POSTGRES_PASSWORD}@postgres:5432/owlclaw
      SERVER_PORT: 7077
      SERVER_MSGQUEUE_KIND: postgres  # 不使用 RabbitMQ
    ports:
      - "7077:7077"
      - "8080:8080"  # Dashboard
    depends_on:
      - postgres

volumes:
  postgres_data:
```

**关键配置：**
- `SERVER_MSGQUEUE_KIND=postgres`：使用 PostgreSQL 作为消息队列，避免额外的 RabbitMQ 依赖
- Hatchet 在独立的 schema 中创建表，不影响 OwlClaw 的 Ledger 和 Memory 表
- Dashboard 在 8080 端口提供任务监控界面



## 错误处理

### 1. 连接失败

```python
# 场景：Hatchet Server 不可达
# 行为：抛出 ConnectionError

ConnectionError: Failed to connect to Hatchet Server: 
  Connection refused (http://localhost:7077)
```

### 2. 任务执行失败

```python
# 场景：任务执行时抛出异常
# 行为：Hatchet 自动重试（根据 retries 配置）

# 第 1 次失败
[ERROR] Task 'agent-run' failed (attempt 1/3): DatabaseError

# 第 2 次失败
[ERROR] Task 'agent-run' failed (attempt 2/3): DatabaseError

# 第 3 次失败
[ERROR] Task 'agent-run' failed (attempt 3/3): DatabaseError
[ERROR] Task 'agent-run' exhausted retries, marking as failed
```

### 3. 无效的 Cron 表达式

```python
# 场景：Cron 表达式格式错误
# 行为：注册时抛出 ValueError

ValueError: Invalid cron expression '*/60 * * *': 
  Expected 5 fields (minute hour day month weekday), got 4
```

### 4. 调度不存在的任务

```python
# 场景：schedule_task 指定的任务未注册
# 行为：抛出 ValueError

ValueError: Task 'non-existent-task' not registered
```

### 5. Worker 崩溃恢复

```python
# 场景：Worker 进程在任务执行中崩溃
# 行为：Hatchet Server 检测到 Worker 离线，将任务重新分配给其他 Worker

[INFO] Worker owlclaw-worker-1 disconnected
[INFO] Task 'agent-run' (run_id=abc123) reassigned to worker owlclaw-worker-2
[INFO] Task 'agent-run' resumed from last checkpoint
```



## 性能考虑

### 1. 任务调度延迟

**问题：** 调度任务后，实际执行可能有延迟。

**影响因素：**
- Worker 并发数（`max_concurrent_tasks`）
- 队列中等待的任务数
- 任务优先级

**优化：**
- 为高优先级任务（如 Agent Run）设置更高的 priority
- 增加 Worker 实例数以提高并发处理能力
- 使用 Hatchet Dashboard 监控队列长度

### 2. PostgreSQL 连接池

**问题：** Hatchet 和 OwlClaw 共用 PostgreSQL，可能导致连接池耗尽。

**解决方案：**
- 配置 PostgreSQL 的 `max_connections`（建议 ≥ 100）
- Hatchet 使用独立的连接池配置
- OwlClaw 使用 SQLAlchemy 的连接池管理

### 3. 持久化定时的精度

**问题：** `aio_sleep_for` 的精度受 Hatchet Server 轮询间隔影响。

**实际精度：**
- 短定时（< 1 分钟）：精度约 ±5 秒
- 长定时（≥ 1 分钟）：精度约 ±10 秒

**适用场景：**
- ✅ Agent Heartbeat（30 分钟间隔）
- ✅ 自我调度（5 分钟后检查）
- ❌ 高精度定时（秒级精度）



## 测试策略

### 1. 单元测试

```python
def test_hatchet_config_from_yaml():
    # Given: 有效的 owlclaw.yaml
    # When: 加载配置
    # Then: 返回 HatchetConfig 对象
    
def test_hatchet_client_connect():
    # Given: 有效的配置
    # When: 调用 connect()
    # Then: 成功连接到 Hatchet Server
    
def test_task_decorator():
    # Given: 函数被 @hatchet.task() 装饰
    # When: 注册任务
    # Then: 任务被添加到 workflows 字典
    
def test_schedule_task():
    # Given: 已注册的任务
    # When: 调用 schedule_task()
    # Then: 返回任务 ID
    
def test_schedule_task_invalid_delay():
    # Given: delay_seconds <= 0
    # When: 调用 schedule_task()
    # Then: 抛出 ValueError
```

### 2. 集成测试

```python
@pytest.mark.integration
async def test_end_to_end_task_execution():
    # Given: Hatchet Server 运行中
    # When: 
    #   1. 注册任务
    #   2. 调度任务
    #   3. Worker 执行任务
    # Then: 任务成功完成
    
@pytest.mark.integration
async def test_durable_sleep():
    # Given: 任务使用 ctx.aio_sleep_for()
    # When: Worker 在定时期间重启
    # Then: 定时恢复并继续执行
    
@pytest.mark.integration
async def test_cron_trigger():
    # Given: 任务配置 cron 表达式
    # When: 到达 Cron 触发时间
    # Then: 任务自动执行
```

### 3. 性能测试

```python
@pytest.mark.performance
async def test_task_scheduling_throughput():
    # 测试：1000 个任务的调度吞吐量
    # 目标：≥ 100 tasks/second
    
@pytest.mark.performance
async def test_concurrent_task_execution():
    # 测试：10 个并发任务的执行
    # 目标：所有任务在 30 秒内完成
```



## 依赖关系

### 外部依赖

- **hatchet-sdk** (`hatchet-sdk`): Hatchet Python SDK
- **pyyaml** (`pyyaml`): 配置文件解析
- **pydantic** (`pydantic`): 配置验证

### 内部依赖

- **owlclaw.agent.runtime**: Agent 运行时将使用 HatchetClient 注册 Agent Run 任务
- **owlclaw.triggers.cron**: Cron 触发器将使用 HatchetClient 的 cron 参数
- **owlclaw.agent.tools**: schedule_once 工具将调用 HatchetClient.schedule_task()

## 未来扩展

### 1. Temporal 支持

**需求：** 企业用户可能需要 Temporal 的高级能力（Signal/Query/子工作流）。

**实现：**
- 创建 `owlclaw/integrations/temporal.py`
- 实现相同的接口（task、schedule_task、cancel_task）
- 通过配置切换持久执行引擎

### 2. 任务依赖和 DAG

**需求：** 支持任务之间的依赖关系（A 完成后执行 B）。

**实现：**
- 使用 Hatchet 的 Workflow 多步骤功能
- 定义任务依赖图
- 自动编排执行顺序

### 3. 任务批处理

**需求：** 批量调度多个任务，减少 API 调用次数。

**实现：**
- `schedule_tasks_batch(tasks: list[dict])`
- 单次 API 调用调度多个任务

## 安全考虑

### 1. API Token 管理

**风险：** API Token 泄露可能导致未授权访问 Hatchet Server。

**缓解：**
- 从环境变量读取 Token（不写入配置文件）
- 使用 Hatchet 的 RBAC 限制 Token 权限
- 定期轮换 Token

### 2. 任务参数注入

**风险：** 恶意任务参数可能导致代码注入。

**缓解：**
- 使用 Pydantic 验证任务参数
- 不使用 `eval()` 或 `exec()` 处理参数
- 任务参数序列化为 JSON（不支持任意 Python 对象）

### 3. Worker 隔离

**风险：** 恶意任务可能影响其他任务或系统资源。

**缓解：**
- Worker 在业务应用的权限范围内运行（不提供额外隔离）
- 使用 Docker 容器隔离 Worker 进程
- 配置资源限制（CPU、内存）

