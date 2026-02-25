# Tasks: 安全模型

## 文档联动

- requirements: `.kiro/specs/security/requirements.md`
- design: `.kiro/specs/security/design.md`
- tasks: `.kiro/specs/security/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


> **状态**：已完成  
> **预估工作量**：5-7 天  
> **最后更新**：2026-02-23  
> **执行原则**：本清单内所有任务均须专业、认真完成，不区分可选与必选。

---

## 进度概览

- **总任务数**：44
- **已完成**：44
- **进行中**：0
- **未开始**：0

---

## 1. 基础设施（1 天）

### 1.1 创建安全模块目录
- [x] 1.1.1 创建 `owlclaw/security/__init__.py`
- [x] 1.1.2 创建 `owlclaw/security/sanitizer.py`
- [x] 1.1.3 创建 `owlclaw/security/risk_gate.py`
- [x] 1.1.4 创建 `owlclaw/security/data_masker.py`
- [x] 1.1.5 创建 `owlclaw/security/audit.py`
- [x] 1.1.6 创建 `owlclaw/security/rules.py`

---

## 2. 输入净化（2 天）

### 2.1 InputSanitizer 实现
- [x] 2.1.1 实现 `SanitizationRule` 数据模型（pattern, action, description）
- [x] 2.1.2 实现 `SanitizeResult` 数据模型（original, sanitized, modifications）
- [x] 2.1.3 实现 `InputSanitizer.__init__` 加载规则（内置 + 自定义）
- [x] 2.1.4 实现 `InputSanitizer.sanitize()` 方法
- [x] 2.1.5 实现 `_default_rules()` 内置规则集（至少 10 条已知 injection 模式）

### 2.2 Agent Runtime 集成
- [x] 2.2.1 在 `owlclaw/agent/runtime.py` 的 prompt 构建流程中集成 InputSanitizer
- [x] 2.2.2 确保 system/user 角色隔离在 `_build_messages()` 中强制执行
- [x] 2.2.3 sanitization 修改时写入审计日志

### 2.3 单元测试
- [x] 2.3.1 测试已知 injection 模式检测（至少 10 个攻击向量）
- [x] 2.3.2 测试自定义规则加载和应用
- [x] 2.3.3 测试角色隔离（system/user 不可混入）

---

## 3. 风险门控（2 天）

### 3.1 RiskGate 实现
- [x] 3.1.1 实现 `RiskDecision` 枚举（execute, pause, reject）
- [x] 3.1.2 实现 `RiskGate.evaluate()` 根据 risk_level 返回决策
- [x] 3.1.3 实现 `RiskGate.confirm()` 和 `RiskGate.reject()` 确认/拒绝接口
- [x] 3.1.4 实现确认超时自动取消逻辑

### 3.2 Governance 集成
- [x] 3.2.1 在 `governance/visibility.py` 执行 function call 前调用 RiskGate
- [x] 3.2.2 从 SKILL.md frontmatter 读取 `risk_level` 和 `requires_confirmation`

### 3.3 单元测试
- [x] 3.3.1 测试各风险等级的决策正确性
- [x] 3.3.2 测试确认/拒绝/超时流程

---

## 4. 数据脱敏（1 天）

### 4.1 DataMasker 实现
- [x] 4.1.1 实现 `MaskRule` 数据模型（field_pattern, mask_type, replacement）
- [x] 4.1.2 实现 `DataMasker.mask()` 方法（递归处理 dict）
- [x] 4.1.3 实现内置脱敏规则（手机号、身份证、银行卡、邮箱）

### 4.2 集成
- [x] 4.2.1 在 MCP Server 输出层集成 DataMasker
- [x] 4.2.2 记忆 `remember()` 工具支持 `sensitivity` 参数

### 4.3 单元测试
- [x] 4.3.1 测试各类型数据的脱敏正确性
- [x] 4.3.2 测试嵌套 dict 的递归脱敏

---

## 5. 配置与审计（1 天）

### 5.1 安全配置
- [x] 5.1.1 在 `owlclaw.yaml` 中添加 `security` 配置节
- [x] 5.1.2 实现配置加载和验证

### 5.2 审计日志
- [x] 5.2.1 实现 `SecurityAuditLog` 类
- [x] 5.2.2 所有安全事件写入审计日志（sanitization、risk gate、masking）

---

## 6. 验收清单

### 6.1 功能验收
- [x] InputSanitizer 正确移除已知 injection 模式
- [x] system/user 角色隔离在 Agent Runtime 中强制执行
- [x] RiskGate 按风险等级正确拦截高风险操作
- [x] DataMasker 正确脱敏敏感数据
- [x] 审计日志完整记录安全事件

### 6.2 测试验收
- [x] 单元测试覆盖率 > 80%
- [x] 包含 OWASP LLM Top 10 攻击向量测试

### 6.3 文档验收
- [x] 安全配置文档完整

---

## 7. 依赖与阻塞

### 7.1 依赖
- `owlclaw.agent.runtime`：prompt 构建流程（角色隔离集成点）
- `owlclaw.governance.visibility`：function call 执行流程（RiskGate 集成点）
- `owlclaw.governance.ledger`：审计日志存储

### 7.2 阻塞
- 无

---

## 8. 风险

### 8.1 安全检查性能开销
- **缓解**：Sanitization + Validation 总延迟 < 100ms，异步非阻塞设计

---

**维护者**：OwlClaw Team  
**最后更新**：2026-02-23
