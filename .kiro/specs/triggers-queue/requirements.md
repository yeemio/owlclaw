# 需求文档：消息队列触发器

## 简介

消息队列触发器用于从外部消息队列消费事件并触发 OwlClaw Agent Run。该触发器提供统一的队列适配层、消息解析与路由、幂等与重试、治理与可观测集成，以及最小可运行的端到端验证路径。

## 术语表

- **Queue_Trigger**: 消息队列触发器系统
- **Queue_Adapter**: 队列适配层（Kafka/RabbitMQ/SQS 等）
- **Message_Envelope**: 统一消息封装结构
- **Ack_Policy**: 消息确认策略（ack/nack/requeue/dlq）
- **Dead_Letter**: 死信队列
- **Dedup_Key**: 幂等键
- **Consumer_Group**: 消费者组
- **Visibility_Timeout**: 可见性超时（SQS）
- **Offset_Commit**: 位点提交（Kafka）
- **Governance_Layer**: 治理层
- **Ledger_Record**: 执行记录

## 需求

### 需求 1：统一队列适配层

**用户故事：** 作为平台开发者，我希望通过统一接口接入不同消息队列，以便避免多套实现与分叉。

#### 验收标准

1. THE Queue_Trigger SHALL 提供统一的 Queue_Adapter 接口
2. THE Queue_Trigger SHALL 支持至少一种具体实现（Kafka/RabbitMQ/SQS 其一）
3. WHEN 切换队列实现时，业务侧注册 API 不变
4. THE Queue_Trigger SHALL 暴露清晰的适配器能力与限制
5. WHEN 未安装对应依赖时，THE Queue_Trigger SHALL 抛出可理解的错误

### 需求 2：消息订阅与消费生命周期

**用户故事：** 作为系统管理员，我希望能够配置并启动队列消费，以便稳定触发 Agent Run。

#### 验收标准

1. THE Queue_Trigger SHALL 支持配置 queue/topic、consumer_group、并发度
2. THE Queue_Trigger SHALL 支持启动、暂停、恢复与停止消费
3. THE Queue_Trigger SHALL 在进程关闭时优雅停止并释放连接
4. THE Queue_Trigger SHALL 支持健康检查与消费状态查询
5. WHEN 消费异常时，THE Queue_Trigger SHALL 记录错误并继续处理后续消息

### 需求 3：消息解析与统一封装

**用户故事：** 作为集成开发者，我希望能够将不同队列的消息转换为统一结构，以便下游处理一致。

#### 验收标准

1. THE Queue_Trigger SHALL 将原始消息转换为 Message_Envelope
2. THE Message_Envelope SHALL 包含 message_id、payload、headers、received_at、source
3. THE Queue_Trigger SHALL 支持 JSON、文本与二进制消息解析
4. WHEN 消息无法解析时，THE Queue_Trigger SHALL 标记为失败并可路由到死信
5. THE Queue_Trigger SHALL 支持自定义转换规则

### 需求 4：触发 Agent Run 与上下文传递

**用户故事：** 作为业务开发者，我希望队列消息触发后能携带完整上下文，以便 Agent 做出正确决策。

#### 验收标准

1. THE Queue_Trigger SHALL 调用 agent_runtime.trigger_event() 启动 Agent Run
2. THE Queue_Trigger SHALL 将 Message_Envelope 与来源信息传入上下文
3. THE Queue_Trigger SHALL 支持根据消息路由到不同 event_name
4. THE Queue_Trigger SHALL 支持 focus 参数以限定 Skills 范围
5. WHEN Governance_Layer 拒绝执行时，THE Queue_Trigger SHALL 记录并处理 ack_policy

### 需求 5：Ack/Nack 与重试策略

**用户故事：** 作为系统运维人员，我希望队列消费具备可靠确认与重试策略，以便提高成功率。

#### 验收标准

1. THE Queue_Trigger SHALL 支持 ack、nack、requeue、dlq 策略
2. THE Queue_Trigger SHALL 支持按错误类型配置重试次数与退避
3. WHEN 触发失败且可重试时，THE Queue_Trigger SHALL 依据策略重试
4. WHEN 重试次数耗尽时，THE Queue_Trigger SHALL 将消息发送到 dead-letter
5. THE Queue_Trigger SHALL 记录每次重试的原因与次数

### 需求 6：幂等与去重

**用户故事：** 作为业务开发者，我希望重复消息不会导致重复执行，以便保证结果一致。

#### 验收标准

1. THE Queue_Trigger SHALL 支持 dedup_key 幂等策略
2. WHEN dedup_key 已处理时，THE Queue_Trigger SHALL 跳过执行并 ack
3. THE Queue_Trigger SHALL 支持基于 message_id 的默认幂等
4. THE Queue_Trigger SHALL 记录去重命中次数
5. THE Queue_Trigger SHALL 支持可配置的幂等窗口期

### 需求 7：治理层与 Ledger 集成

**用户故事：** 作为安全管理员，我希望所有队列触发都经过治理与审计。

#### 验收标准

1. THE Queue_Trigger SHALL 在执行前调用 Governance_Layer 进行校验
2. THE Queue_Trigger SHALL 将关键上下文写入 Ledger_Record
3. THE Queue_Trigger SHALL 记录消费延迟、执行耗时、LLM 调用次数
4. WHEN 执行被拒绝时，THE Queue_Trigger SHALL 记录拒绝原因
5. THE Queue_Trigger SHALL 支持按 tenant_id 进行隔离

### 需求 8：监控与可观测性

**用户故事：** 作为运维人员，我希望对消费与执行指标进行监控，以便快速定位问题。

#### 验收标准

1. THE Queue_Trigger SHALL 暴露消费速率、失败率、重试率指标
2. THE Queue_Trigger SHALL 记录每条消息处理的 trace_id
3. THE Queue_Trigger SHALL 提供队列积压与延迟指标
4. THE Queue_Trigger SHALL 提供健康检查端点
5. THE Queue_Trigger SHALL 记录关键日志（消费、解析、执行、确认）

### 需求 9：安全与权限

**用户故事：** 作为安全管理员，我希望系统安全接入队列并限制访问。

#### 验收标准

1. THE Queue_Trigger SHALL 支持通过环境变量配置访问凭证
2. THE Queue_Trigger SHALL 避免在日志中输出敏感凭证
3. THE Queue_Trigger SHALL 支持最小权限访问策略
4. THE Queue_Trigger SHALL 支持 TLS 连接（如适配器支持）
5. THE Queue_Trigger SHALL 支持在配置中禁用明文连接

### 需求 10：运行模式与本地验证

**用户故事：** 作为开发者，我希望在本地或 CI 中能以最小成本验证队列触发路径。

#### 验收标准

1. THE Queue_Trigger SHALL 支持 mock queue 运行模式
2. THE Queue_Trigger SHALL 提供最小可运行示例
3. THE Queue_Trigger SHALL 支持以脚本方式触发一条消息
4. THE Queue_Trigger SHALL 在无外部服务时可完成验收流程
5. THE Queue_Trigger SHALL 提供明确的验证步骤

---

## 非功能需求

### NFR-1：吞吐与延迟

- THE Queue_Trigger SHALL 在单实例下支持至少 500 msg/min（基准）
- THE Queue_Trigger SHALL 保证消息触发延迟 P95 < 5s（队列可达前提）

### NFR-2：可靠性

- THE Queue_Trigger SHALL 保证 at-least-once 处理语义
- THE Queue_Trigger SHALL 支持故障恢复后继续消费

### NFR-3：可维护性

- THE Queue_Trigger SHALL 将队列实现隔离在 adapters 内
- THE Queue_Trigger SHALL 提供清晰的配置说明与默认值

---

## 约束与假设

### 约束

- OwlClaw 不直接依赖具体队列 SDK，必须通过集成隔离层
- 触发器不得在 Heartbeat 中执行外部 I/O

### 假设

- 队列服务可用且有稳定的网络连接
- Governance 与 Ledger 已按既有规范运行

---

## 依赖

### 内部依赖

- owlclaw.agent.runtime
- owlclaw.governance
- owlclaw.integrations.hatchet（用于持久执行或调度）

### 外部依赖

- Kafka 或 RabbitMQ 或 SQS（待选型）

---

## 风险与缓解

### 风险 1：队列语义差异

- **影响**：不同队列的 ack/offset 语义导致行为不一致
- **缓解**：统一 Message_Envelope 与 Ack_Policy 适配层

### 风险 2：重复消息与幂等

- **影响**：重复执行导致业务副作用
- **缓解**：默认 message_id 幂等 + 可配置 dedup_key

---

## Definition of Done

- [ ] 需求 1-10 的验收标准全部通过
- [ ] NFR-1/2/3 验收通过
- [ ] 单元测试覆盖率 ≥ 80%
- [ ] 端到端验证在本地与 CI 可复现

---

## 参考文档

- docs/ARCHITECTURE_ANALYSIS.md
- .kiro/specs/triggers-cron/requirements.md
- .kiro/specs/triggers-webhook/requirements.md

---

**维护者**：平台研发
**最后更新**：2026-02-22
