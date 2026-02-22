# Requirements: 安全模型

## 文档联动

- requirements: `.kiro/specs/security/requirements.md`
- design: `.kiro/specs/security/design.md`
- tasks: `.kiro/specs/security/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


> **目标**：为 OwlClaw Agent 基础设施提供系统性的安全保障，覆盖 Prompt Injection 防护、高风险操作二次确认、敏感数据保护  
> **优先级**：P1  
> **预估工作量**：5-7 天

---

## 1. 背景与动机

### 1.1 当前问题

OwlClaw 作为面向业务应用的 Agent 基础设施，Agent 会执行真实的业务操作（如建仓交易、发送通知、修改数据）。安全风险包括：

- **Prompt Injection**：外部输入（webhook payload、API 请求体、用户消息）可能包含恶意指令，劫持 Agent 决策
- **越权执行**：Agent 可能绕过约束执行高风险操作
- **数据泄露**：Agent 的记忆（MEMORY.md）、Ledger 和 MCP 通道可能暴露敏感业务数据

### 1.2 设计目标

- 建立纵深防御体系，多层安全机制互相补充
- 安全措施对业务开发者透明，不增加接入负担
- 与现有治理层（governance）协同，不重复建设

---

## 2. 用户故事

### 2.1 作为平台安全负责人

**故事 1**：Prompt Injection 防护
```
作为平台安全负责人
我希望外部输入不能劫持 Agent 的系统指令
这样我可以确保 Agent 始终在预设的安全边界内决策
```

**验收标准**：
- [ ] 外部输入（webhook payload、API body）作为 `user` 角色消息传入，不混入 `system` prompt
- [ ] 系统 prompt（SOUL.md、IDENTITY.md、Skills）与外部输入严格分离
- [ ] 输入经过 sanitization 处理，移除已知的 injection 模式

**故事 2**：高风险操作确认
```
作为平台安全负责人
我希望高风险操作（如交易执行、数据删除）需要额外确认
这样我可以防止 Agent 因误判导致不可逆的业务损失
```

**验收标准**：
- [ ] 能力的 SKILL.md 或 constraints 中可标记 `requires_confirmation: true`
- [ ] 高风险操作触发时，治理层拦截并等待人工审批或自动策略确认
- [ ] 确认超时时操作自动取消并记录

**故事 3**：敏感数据保护
```
作为平台安全负责人
我希望 Agent 的记忆和执行记录中的敏感数据被适当保护
这样我可以满足数据安全合规要求
```

**验收标准**：
- [ ] MCP 通道暴露的数据经过脱敏处理（如掩码手机号、身份证号、金额）
- [ ] Ledger 支持配置敏感字段脱敏规则
- [ ] Agent 记忆写入时支持标记敏感级别

---

## 3. 功能需求

### 3.1 Prompt Injection 防护

#### FR-1：输入/系统隔离

**需求**：Agent 的 system prompt 与外部输入严格隔离在不同的消息角色中。

**验收标准**：
- [ ] SOUL.md、IDENTITY.md、Skills 知识注入 `system` 角色消息
- [ ] 外部输入（触发器 payload、webhook body、API 请求）注入 `user` 角色消息
- [ ] Agent Runtime 构建 prompt 时强制执行角色分离，不提供绕过接口

#### FR-2：输入 Sanitization

**需求**：外部输入在传递给 Agent 前经过 sanitization 处理。

**验收标准**：
- [ ] 移除已知的 prompt injection 模式（如 "ignore previous instructions"、"system:" 前缀）
- [ ] 支持自定义 sanitization 规则（正则表达式列表）
- [ ] sanitization 应用于所有触发器的外部输入（cron context、webhook payload、queue message、API body）
- [ ] sanitization 日志记录被移除的内容（用于审计）

#### FR-3：输出验证

**需求**：Agent 的 function calling 输出经过验证，确保调用的工具和参数在合法范围内。

**验收标准**：
- [ ] Agent 只能调用当前可见工具列表中的工具（已由 governance visibility 保证）
- [ ] 工具参数经过 JSON Schema 验证（如果 capability 定义了 schema）
- [ ] 参数中包含可疑内容（如 SQL 注入模式）时记录告警

### 3.2 高风险操作确认

#### FR-4：操作风险等级标记

**需求**：Capability 可在 SKILL.md 的 owlclaw 扩展字段中标记操作风险等级。

**验收标准**：
- [ ] 支持 `risk_level: low | medium | high | critical` 标记
- [ ] 支持 `requires_confirmation: true` 标记
- [ ] 未标记的 capability 默认为 `low` 风险

#### FR-5：确认策略引擎

**需求**：根据操作风险等级应用不同的确认策略。

**验收标准**：
- [ ] `low`：直接执行（默认行为）
- [ ] `medium`：记录到 Ledger 并标记需审查
- [ ] `high`：在预算 80% 以上时暂停执行等待确认
- [ ] `critical`：始终暂停执行等待人工确认
- [ ] 确认超时（默认 5 分钟）后自动取消

#### FR-6：确认通知与回调

**需求**：高风险操作被拦截时，系统发送通知并提供确认/拒绝接口。

**验收标准**：
- [ ] 支持通知渠道配置（日志、webhook 回调）
- [ ] 提供 CLI 命令 `owlclaw confirm <operation_id>` 和 `owlclaw reject <operation_id>`
- [ ] 确认/拒绝结果记录到 Ledger

### 3.3 敏感数据保护

#### FR-7：数据脱敏引擎

**需求**：提供可配置的数据脱敏引擎，应用于 MCP 通道输出和 Ledger 记录。

**验收标准**：
- [ ] 支持内置脱敏规则（手机号、身份证、银行卡、邮箱）
- [ ] 支持自定义正则脱敏规则
- [ ] 脱敏在数据输出层执行，原始数据在存储层保持完整

#### FR-8：记忆安全分级

**需求**：Agent 通过 `remember()` 工具写入的记忆支持安全分级标记。

**验收标准**：
- [ ] `remember(content, sensitivity="public|internal|confidential")` 支持敏感度参数
- [ ] `confidential` 级别的记忆在 MCP 通道查询时自动脱敏
- [ ] 提供 `owlclaw memory audit` CLI 命令审查敏感记忆

#### FR-9：审计日志

**需求**：所有安全相关事件产生不可篡改的审计日志。

**验收标准**：
- [ ] 记录 sanitization 触发事件（输入被修改）
- [ ] 记录高风险操作确认/拒绝事件
- [ ] 记录数据脱敏应用事件
- [ ] 审计日志独立于业务 Ledger，防止被清理

---

## 4. 非功能需求

### 4.1 性能

**NFR-1：零感知延迟**
- Sanitization 处理延迟 < 10ms
- 数据脱敏处理延迟 < 50ms
- 安全检查不应成为 Agent Run 的性能瓶颈

### 4.2 可配置性

**NFR-2：安全策略可配置**
- 所有安全策略通过 `owlclaw.yaml` 配置
- 支持 `owlclaw reload` 热更新安全规则

### 4.3 向后兼容

**NFR-3：默认安全**
- 即使未配置任何安全规则，系统默认启用基础防护（角色隔离）
- 安全模块的引入不破坏现有 API

---

## 5. 验收标准总览

### 5.1 功能验收
- [ ] **FR-1**：system/user 角色隔离已强制执行
- [ ] **FR-2**：输入 sanitization 可移除已知 injection 模式
- [ ] **FR-3**：工具调用输出经过验证
- [ ] **FR-4**：Capability 风险等级标记可用
- [ ] **FR-5**：确认策略引擎按风险等级正确拦截
- [ ] **FR-6**：确认通知和回调机制可用
- [ ] **FR-7**：数据脱敏引擎正确脱敏
- [ ] **FR-8**：记忆安全分级功能可用
- [ ] **FR-9**：审计日志完整记录安全事件

### 5.2 测试验收
- [ ] 单元测试覆盖 sanitization 规则、脱敏规则
- [ ] 集成测试覆盖端到端的 injection 防护流程
- [ ] 包含已知 prompt injection 攻击向量的测试用例

---

## 6. 约束与假设

### 6.1 约束
- 安全模块不替代业务层的安全措施（如业务系统的 RBAC）
- OwlClaw 不做业务层回滚，只提供决策记录和告警
- MVP 阶段不实现完整的 RBAC（属于企业版）

### 6.2 假设
- Agent Runtime 已实现 system/user 消息分离
- Governance 层的 VisibilityFilter 已实现

---

## 7. 依赖

### 7.1 内部依赖
- `owlclaw.agent.runtime`：消息构建（角色隔离）
- `owlclaw.governance.visibility`：可见性过滤（工具范围限制）
- `owlclaw.governance.ledger`：执行记录（审计日志）

---

## 8. 风险与缓解

### 8.1 风险：未知 Injection 攻击向量

**影响**：已知模式无法覆盖所有攻击

**缓解**：
- 角色隔离是第一道防线（架构层面），不依赖模式匹配
- 持续跟踪 OWASP LLM Top 10 更新 sanitization 规则
- 治理层的可见性过滤从根本上限制了 Agent 的行动范围

---

## 10. 参考文档

- [OwlClaw 架构分析](../../docs/ARCHITECTURE_ANALYSIS.md) §8.5 安全模型
- [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [Governance Spec](../governance/)
- [Agent Runtime Spec](../agent-runtime/)

---

**维护者**：OwlClaw Team  
**最后更新**：2026-02-22
