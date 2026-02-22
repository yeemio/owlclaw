# Requirements: Signal 触发器（人工介入）

> **目标**：提供人工介入机制，支持暂停、恢复、强制触发和指令注入 Agent Run  
> **优先级**：P1-P2  
> **预估工作量**：4-6 天

---

## 1. 背景与动机

### 1.1 当前问题

架构文档 §5.2.2 事件触发层定义了五类触发源，其中「Signal 触发 → 人工介入（暂停/恢复/强制执行）」是生产环境至关重要的人机协作机制。当前缺少系统化的人工介入通道。

### 1.2 设计目标

- 提供 CLI 和 API 两种人工介入方式
- 支持暂停、恢复、强制触发、注入指令四种 Signal 类型
- Signal 操作经过权限验证和审计记录
- 与 MCP Server 协同，支持通过对话暂停/恢复 Agent

---

## 2. 用户故事

### 2.1 作为平台运维人员

**故事 1**：暂停 Agent 自主调度
```
作为平台运维人员
我希望能随时暂停 Agent 的所有自主调度
这样我可以在紧急情况下阻止 Agent 执行任何操作
```

**验收标准**：
- [ ] `owlclaw agent pause [--agent-id <id>]` 暂停 Agent 所有自主触发
- [ ] 暂停期间 Heartbeat、Cron、自我调度均不触发 Agent Run
- [ ] 外部请求（MCP/API）仍可查询 Agent 状态（只读）

**故事 2**：恢复 Agent 调度
```
作为平台运维人员
我希望确认安全后恢复 Agent 的自主调度
这样 Agent 可以从下一个调度周期继续工作
```

**验收标准**：
- [ ] `owlclaw agent resume [--agent-id <id>]` 恢复自主调度
- [ ] 恢复后从下一个 cron/heartbeat 周期开始

**故事 3**：强制触发
```
作为平台运维人员
我希望能手动触发一次 Agent Run 并指定关注点
这样我可以在特殊情况下让 Agent 处理特定事务
```

**验收标准**：
- [ ] `owlclaw agent trigger --focus <focus> --message <msg>` 立即触发
- [ ] 强制触发不受暂停状态影响
- [ ] 触发上下文标记 `trigger_type="signal_manual"`

**故事 4**：注入指令
```
作为平台运维人员
我希望能向正在运行的 Agent 注入额外指令
这样我可以在不中断 Agent 的情况下调整其行为
```

**验收标准**：
- [ ] `owlclaw agent instruct --message <msg>` 注入指令
- [ ] 指令在下一次 Agent Run 的上下文中出现
- [ ] 指令带时效性，过期自动清除

---

## 3. 功能需求

#### FR-1：Signal 注册与分发

**需求**：统一的 Signal 处理管道，接收 CLI/API/MCP 来源的 Signal 并分发给 Agent。

**验收标准**：
- [ ] Signal 类型：`pause`, `resume`, `trigger`, `instruct`
- [ ] 每个 Signal 携带来源（cli/api/mcp）、操作者、时间戳
- [ ] Signal 处理结果写入 Ledger

#### FR-2：暂停/恢复状态管理

**需求**：Agent 维护 `paused` 状态标志，暂停时所有自主触发被跳过。

**验收标准**：
- [ ] `paused` 状态持久化（进程重启后保持）
- [ ] 暂停期间的 Cron/Heartbeat 触发记录 status=SKIPPED
- [ ] API/MCP 只读查询不受暂停影响

#### FR-3：强制触发

**需求**：无视暂停状态，手动发起一次 Agent Run。

**验收标准**：
- [ ] 支持指定 focus 和自由文本 message
- [ ] 经过治理层检查（预算/限流）
- [ ] 执行记录标记 `trigger_type="signal_manual"`

#### FR-4：指令注入

**需求**：向 Agent 的下一次 Run 注入额外指令。

**验收标准**：
- [ ] 指令存储在 Agent 状态中，下次 Run 时注入 prompt
- [ ] 支持 TTL（默认 1 小时），过期自动清除
- [ ] 指令一次性消费（注入后标记已消费）

#### FR-5：MCP Server 集成

**需求**：MCP Server 的 `owlclaw_pause`/`owlclaw_resume`/`owlclaw_trigger` 工具调用 Signal 系统。

**验收标准**：
- [ ] MCP 工具调用转化为 Signal 并分发
- [ ] Signal 来源标记为 `mcp`

---

## 4. 依赖

- `owlclaw.agent.runtime`：Agent 状态管理和 Run 触发
- `owlclaw.governance.ledger`：操作审计
- `owlclaw.cli`：CLI 命令注册
- `owlclaw-mcp`：MCP Server 工具暴露

---

## 5. 参考文档

- [OwlClaw 架构分析](../../docs/ARCHITECTURE_ANALYSIS.md) §5.2.2 事件触发层
- [OwlClaw 架构分析](../../docs/ARCHITECTURE_ANALYSIS.md) §5.2.6 OpenClaw 通道
- [MCP Server Spec](../mcp-server/)

---

**维护者**：OwlClaw Team  
**最后更新**：2026-02-22
