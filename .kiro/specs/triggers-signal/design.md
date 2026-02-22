# Signal 触发器（人工介入）设计文档

## 文档联动

- requirements: `.kiro/specs/triggers-signal/requirements.md`
- design: `.kiro/specs/triggers-signal/design.md`
- tasks: `.kiro/specs/triggers-signal/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`

## 概述

Signal 触发器提供人工介入通道，支持通过 CLI / API / MCP 三种入口对运行中的 Agent 执行 pause、resume、trigger、instruct 四种操作。所有操作经过权限验证并记录到 Ledger。

## 架构概览

```
┌──────────────────────────────────────────────────────────────┐
│                      Signal Sources                            │
│                                                                │
│  ┌─────────┐    ┌─────────────────┐    ┌──────────────────┐ │
│  │  CLI     │    │  HTTP API       │    │  MCP Server      │ │
│  │  owlclaw │    │  /admin/signal  │    │  owlclaw_pause   │ │
│  │  agent   │    │                 │    │  owlclaw_resume  │ │
│  │  pause   │    │                 │    │  owlclaw_trigger │ │
│  └────┬─────┘    └───────┬─────────┘    └────────┬─────────┘ │
│       │                  │                        │           │
│       └──────────────────┼────────────────────────┘           │
│                          │                                     │
│                  ┌───────▼───────┐                            │
│                  │ SignalRouter   │                            │
│                  │ (统一入口)      │                            │
│                  └───────┬───────┘                            │
│                          │                                     │
│                  ┌───────▼───────┐                            │
│                  │ AuthZ Check   │  权限验证                    │
│                  └───────┬───────┘                            │
│                          │                                     │
│          ┌───────┬───────┼───────┬──────────┐                │
│          │       │       │       │          │                │
│      ┌───▼──┐┌───▼──┐┌───▼──┐┌───▼──────┐  │                │
│      │pause ││resume││trigger││instruct  │  │                │
│      │Handle││Handle││Handle ││Handle    │  │                │
│      └───┬──┘└───┬──┘└───┬──┘└───┬──────┘  │                │
│          │       │       │       │          │                │
│          └───────┴───┬───┴───────┘          │                │
│                      │                       │                │
│              ┌───────▼───────┐       ┌──────▼──────┐        │
│              │ Agent State   │       │   Ledger    │        │
│              │ Manager       │       │   Record    │        │
│              └───────────────┘       └─────────────┘        │
└──────────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. Signal 数据模型

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

class SignalType(str, Enum):
    PAUSE = "pause"
    RESUME = "resume"
    TRIGGER = "trigger"
    INSTRUCT = "instruct"

class SignalSource(str, Enum):
    CLI = "cli"
    API = "api"
    MCP = "mcp"

@dataclass
class Signal:
    id: UUID = field(default_factory=uuid4)
    type: SignalType = SignalType.PAUSE
    source: SignalSource = SignalSource.CLI
    agent_id: str = ""
    tenant_id: str = ""
    operator: str = ""              # 操作者标识
    message: str = ""               # trigger/instruct 的消息
    focus: str | None = None        # trigger 的关注点
    ttl_seconds: int = 3600         # instruct 的有效期（默认 1 小时）
    created_at: datetime = field(default_factory=datetime.utcnow)
```

### 2. SignalRouter（统一入口）

```python
class SignalRouter:
    """接收所有来源的 Signal，验证后分发到对应 Handler"""

    def __init__(
        self,
        agent_state: AgentStateManager,
        agent_runner: AgentRunner,
        governance: GovernanceService,
        ledger: Ledger,
        stm_registry: dict[str, STMManager],  # agent_id → STM
    ): ...

    async def dispatch(self, signal: Signal) -> SignalResult:
        # 1. 权限验证
        self._authorize(signal)

        # 2. 分发到 Handler
        handler = self._handlers[signal.type]
        result = await handler.handle(signal)

        # 3. 记录到 Ledger
        self.ledger.record(
            event_type="signal",
            signal_type=signal.type.value,
            source=signal.source.value,
            operator=signal.operator,
            agent_id=signal.agent_id,
            result=result.status,
        )
        return result
```

### 3. PauseHandler

```python
class PauseHandler:
    async def handle(self, signal: Signal) -> SignalResult:
        agent = await self.agent_state.get(signal.agent_id, signal.tenant_id)
        if agent.paused:
            return SignalResult(status="already_paused")

        await self.agent_state.set_paused(signal.agent_id, signal.tenant_id, True)

        # 暂停所有 Hatchet cron（不取消，只暂停）
        await self.hatchet.pause_crons(signal.agent_id)

        return SignalResult(status="paused", message=f"Agent {signal.agent_id} paused")
```

### 4. ResumeHandler

```python
class ResumeHandler:
    async def handle(self, signal: Signal) -> SignalResult:
        agent = await self.agent_state.get(signal.agent_id, signal.tenant_id)
        if not agent.paused:
            return SignalResult(status="already_running")

        await self.agent_state.set_paused(signal.agent_id, signal.tenant_id, False)

        # 恢复 Hatchet cron
        await self.hatchet.resume_crons(signal.agent_id)

        return SignalResult(status="resumed", message=f"Agent {signal.agent_id} resumed")
```

### 5. TriggerHandler

```python
class TriggerHandler:
    async def handle(self, signal: Signal) -> SignalResult:
        # 强制触发不受 paused 状态影响
        # 但仍需经过治理检查（预算/限流）
        if not await self.governance.check("signal_manual"):
            return SignalResult(status="governance_blocked")

        run_id = await self.agent_runner.trigger(
            event_name="signal_manual",
            trigger_type="signal_manual",
            payload={"message": signal.message},
            focus=signal.focus,
        )
        return SignalResult(status="triggered", run_id=run_id)
```

### 6. InstructHandler

```python
class InstructHandler:
    async def handle(self, signal: Signal) -> SignalResult:
        # 将指令写入 Agent 的 pending_instructions 队列
        instruction = PendingInstruction(
            content=signal.message,
            operator=signal.operator,
            source=signal.source,
            created_at=signal.created_at,
            expires_at=signal.created_at + timedelta(seconds=signal.ttl_seconds),
        )
        await self.agent_state.add_instruction(
            signal.agent_id, signal.tenant_id, instruction
        )
        return SignalResult(
            status="instruction_queued",
            message=f"Instruction queued, expires in {signal.ttl_seconds}s",
        )
```

### 7. AgentStateManager（Agent 状态持久化）

```python
class AgentStateManager:
    """管理 Agent 的运行状态，持久化到 PostgreSQL"""

    async def get(self, agent_id: str, tenant_id: str) -> AgentState: ...
    async def set_paused(self, agent_id: str, tenant_id: str, paused: bool) -> None: ...
    async def add_instruction(self, agent_id: str, tenant_id: str, instruction: PendingInstruction) -> None: ...
    async def consume_instructions(self, agent_id: str, tenant_id: str) -> list[PendingInstruction]:
        """消费所有未过期的指令（一次性，消费后标记已执行）"""
        ...
    async def cleanup_expired_instructions(self, agent_id: str, tenant_id: str) -> int: ...
```

### 8. Instruction 注入到 Agent Run

指令在 Agent Runtime 的 Run 启动阶段注入：

```python
# 在 AgentRuntime._start_run() 中
async def _start_run(self, trigger_event, focus):
    # 1. 创建 STM
    stm = self.memory_service.create_stm()

    # 2. 消费 pending instructions
    instructions = await self.agent_state.consume_instructions(
        self.agent_id, self.tenant_id
    )
    for inst in instructions:
        stm.inject(f"[OPERATOR INSTRUCTION from {inst.operator}]: {inst.content}")

    # 3. 构建 Memory Snapshot
    snapshot = await self.memory_service.build_snapshot(...)

    # 4. 正常 Run 流程...
```

## 数据库 Schema

```sql
-- Agent 状态表（可与 agents 表合并）
ALTER TABLE agents ADD COLUMN paused BOOLEAN NOT NULL DEFAULT FALSE;

-- Pending instructions 表
CREATE TABLE pending_instructions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   VARCHAR(64) NOT NULL DEFAULT 'default',
    agent_id    VARCHAR(64) NOT NULL,
    content     TEXT NOT NULL,
    operator    VARCHAR(255),
    source      VARCHAR(20),  -- cli | api | mcp
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at  TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ,
    consumed    BOOLEAN NOT NULL DEFAULT FALSE,

    CONSTRAINT fk_agent FOREIGN KEY (agent_id, tenant_id)
        REFERENCES agents(agent_id, tenant_id)
);

CREATE INDEX idx_instructions_pending
    ON pending_instructions (tenant_id, agent_id, expires_at)
    WHERE NOT consumed AND expires_at > now();

CREATE INDEX idx_instructions_tenant_created
    ON pending_instructions (tenant_id, created_at DESC);
```

## CLI 命令

```bash
# 暂停 Agent
owlclaw agent pause --agent mionyee-trading
# → Agent mionyee-trading paused

# 恢复 Agent
owlclaw agent resume --agent mionyee-trading
# → Agent mionyee-trading resumed

# 强制触发
owlclaw agent trigger --agent mionyee-trading --focus "urgent_check" --message "市场异常波动，立即检查"
# → Agent Run triggered: run_id=abc123

# 注入指令
owlclaw agent instruct --agent mionyee-trading --message "今天暂停所有买入操作" --ttl 3600
# → Instruction queued, expires in 3600s

# 查看 Agent 状态
owlclaw agent status --agent mionyee-trading
# → Agent: mionyee-trading
# → Status: running (not paused)
# → Pending Instructions: 1
# → Last Run: 2026-02-22T10:30:00Z (completed)
```

## 配置模型

```yaml
triggers:
  signal:
    default_instruct_ttl_seconds: 3600
    max_pending_instructions: 10
    require_auth_for_cli: false     # CLI 默认信任本地操作
    require_auth_for_api: true
```

## 测试策略

| 层级 | 覆盖 | 工具 |
|------|------|------|
| 单元测试 | Signal 创建/验证、各 Handler 逻辑 | pytest |
| 单元测试 | AgentStateManager pause/resume/instruction | pytest + mock DB |
| 单元测试 | Instruction TTL 过期清理 | pytest + freezegun |
| 集成测试 | CLI → SignalRouter → Handler → State 变更 | pytest + Click CliRunner |
| 集成测试 | API → SignalRouter → Handler | pytest + httpx TestClient |
| 集成测试 | Instruction → Agent Run 注入验证 | 端到端 mock |
| E2E 测试 | pause → cron 不触发 → resume → cron 恢复 | 集成测试套件 |
