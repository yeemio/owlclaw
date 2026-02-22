# Design: 安全模型

## 文档联动

- requirements: `.kiro/specs/security/requirements.md`
- design: `.kiro/specs/security/design.md`
- tasks: `.kiro/specs/security/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


> **目标**：为 OwlClaw 提供纵深防御的安全体系  
> **状态**：已完成  
> **最后更新**：2026-02-22

---

## 1. 架构设计

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        外部输入                                    │
│  Webhook Payload / API Body / Queue Message / Cron Context       │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│  Layer 1: Input Sanitizer（输入净化层）                            │
│  - 移除已知 injection 模式                                        │
│  - 自定义正则规则匹配                                              │
│  - 审计日志记录                                                    │
└──────────────────────┬──────────────────────────────────────────┘
                       │ 净化后的输入
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│  Layer 2: Role Isolation（角色隔离层）                              │
│  - system role: SOUL.md + IDENTITY.md + Skills                    │
│  - user role: 外部输入（净化后）+ 触发上下文                        │
│  - 禁止混入，Agent Runtime 强制执行                                 │
└──────────────────────┬──────────────────────────────────────────┘
                       │ 构建好的 messages
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│  Layer 3: Governance Visibility（治理可见性层，已有）               │
│  - 约束过滤 / 预算过滤 / 熔断过滤 / 限流过滤                       │
│  - Agent 只能调用过滤后的工具                                       │
└──────────────────────┬──────────────────────────────────────────┘
                       │ LLM function calling
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│  Layer 4: Output Validator（输出验证层）                            │
│  - 验证工具名在可见列表中                                           │
│  - 验证参数符合 JSON Schema                                        │
│  - 检测可疑参数内容                                                 │
└──────────────────────┬──────────────────────────────────────────┘
                       │ 验证通过的 function call
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│  Layer 5: Risk Gate（风险门控层）                                   │
│  - 读取 capability 的 risk_level / requires_confirmation           │
│  - low: 直接执行                                                    │
│  - medium: 执行并标记审查                                           │
│  - high/critical: 暂停等待确认                                      │
└──────────────────────┬──────────────────────────────────────────┘
                       │ 执行
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│  Layer 6: Data Masker（数据脱敏层）                                 │
│  - 输出到 MCP 通道时脱敏                                           │
│  - Ledger 查询时按配置脱敏                                         │
│  - 记忆查询时按 sensitivity 级别脱敏                                │
└──────────────────────────────────────────────────────────────────┘
```

### 1.2 核心组件

#### 组件 1：InputSanitizer

**职责**：净化外部输入，移除 prompt injection 模式。

```python
class InputSanitizer:
    def __init__(self, rules: list[SanitizationRule] | None = None):
        self._rules = rules or self._default_rules()
    
    def sanitize(self, input_text: str, source: str) -> SanitizeResult:
        """净化输入文本，返回净化结果"""
        ...
    
    def _default_rules(self) -> list[SanitizationRule]:
        """内置规则：ignore previous, system: prefix, role injection 等"""
        ...
```

#### 组件 2：RiskGate

**职责**：根据 capability 的风险等级决定执行策略。

```python
class RiskGate:
    async def evaluate(
        self, capability_name: str, args: dict, context: RunContext
    ) -> RiskDecision:
        """评估操作风险，返回执行/暂停/拒绝决策"""
        ...
    
    async def confirm(self, operation_id: str) -> bool:
        """确认暂停的操作"""
        ...
    
    async def reject(self, operation_id: str, reason: str) -> bool:
        """拒绝暂停的操作"""
        ...
```

#### 组件 3：DataMasker

**职责**：对输出数据进行脱敏处理。

```python
class DataMasker:
    def __init__(self, rules: list[MaskRule] | None = None):
        self._rules = rules or self._default_rules()
    
    def mask(self, data: dict, context: MaskContext) -> dict:
        """对数据字典中的敏感字段进行脱敏"""
        ...
```

---

## 2. 实现细节

### 2.1 文件结构

```
owlclaw/
├── security/
│   ├── __init__.py
│   ├── sanitizer.py         # InputSanitizer 输入净化
│   ├── risk_gate.py         # RiskGate 风险门控
│   ├── data_masker.py       # DataMasker 数据脱敏
│   ├── audit.py             # SecurityAuditLog 审计日志
│   └── rules.py             # 内置规则定义
```

### 2.2 集成点

| 集成位置 | 安全组件 | 调用时机 |
|---------|---------|---------|
| `agent.runtime.runtime.py` | InputSanitizer | 构建 prompt 前，对外部输入净化 |
| `agent.runtime.runtime.py` | Role Isolation | 构建 messages 时，强制 system/user 分离 |
| `agent.runtime.runtime.py` | OutputValidator | LLM 返回 function call 后，执行前验证 |
| `governance.visibility.py` | RiskGate | 工具执行前，检查风险等级 |
| `integrations.langfuse.py` / MCP | DataMasker | 数据对外输出时脱敏 |

---

## 3. 数据流

### 3.1 Agent Run 安全流程

```
触发事件（含外部输入）
    │
    ▼
InputSanitizer.sanitize(external_input)
    │ → 审计日志（如有修改）
    ▼
Role Isolation: system=[SOUL+IDENTITY+Skills], user=[sanitized_input]
    │
    ▼
LLM function calling
    │
    ▼
OutputValidator.validate(tool_name, args)
    │ → 不在可见列表 → 拒绝
    │ → Schema 验证失败 → 拒绝
    ▼
RiskGate.evaluate(capability, args, context)
    │ → low → 直接执行
    │ → high/critical → 暂停等待确认
    ▼
执行 capability handler
    │
    ▼
DataMasker.mask(output) → 对外输出
```

---

## 4. 错误处理

### 4.1 Sanitization 失败

**场景**：自定义规则正则表达式语法错误

**处理**：跳过该规则，记录错误日志，使用剩余规则继续净化。安全组件不应因自身错误阻断 Agent 执行。

### 4.2 风险门控超时

**场景**：高风险操作等待确认超时

**处理**：自动取消操作，记录到 Ledger 和审计日志，Agent Run 继续（该 function call 返回 timeout error）。

---

## 5. 配置

### 5.1 配置文件

```yaml
# owlclaw.yaml
security:
  sanitizer:
    enabled: true
    custom_rules:
      - pattern: "ignore all previous"
        action: remove
      - pattern: "\\bsudo\\b"
        action: flag
  
  risk_gate:
    enabled: true
    confirmation_timeout_seconds: 300
    default_risk_level: low
    notification_channels:
      - type: log
  
  data_masker:
    enabled: true
    rules:
      - field_pattern: "phone"
        mask: "***"
      - field_pattern: "id_card"
        mask: "partial"
```

---

## 6. 测试策略

### 6.1 单元测试

- InputSanitizer：已知 injection 模式列表的检测率
- DataMasker：各类型数据的脱敏正确性
- RiskGate：各风险等级的决策正确性

### 6.2 安全测试

- 使用 OWASP LLM Top 10 攻击向量作为测试用例
- 模拟多步骤 injection 攻击（间接注入）
- 验证角色隔离在各种边界条件下的有效性

---

## 7. 迁移计划

### 7.1 Phase 1：基础防护（2-3 天）
- InputSanitizer + 内置规则
- Role Isolation（Agent Runtime 集成）
- 审计日志

### 7.2 Phase 2：风险门控（2-3 天）
- RiskGate + 确认策略
- DataMasker + 内置脱敏规则
- 配置系统集成

---

## 8. 风险与缓解

### 8.1 风险：安全组件引入延迟

**影响**：每次 Agent Run 增加安全检查耗时

**缓解**：所有安全检查总延迟 < 100ms，不成为瓶颈

---

## 9. 契约与 Mock

### 9.1 Mock 策略

- 单元测试中 mock LLM 返回，测试 sanitization 和 validation 流程
- 集成测试中使用 `mock_mode=true` 模拟 Agent Run

---

**维护者**：OwlClaw Team  
**最后更新**：2026-02-22
