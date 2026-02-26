# Design: Protocol Governance

> **目标**：把协议治理从“文档共识”升级为“工程门禁”。  
> **状态**：设计中  
> **最后更新**：2026-02-26

---

## 1. 架构设计

### 1.1 整体架构

```text
Contract Source (OpenAPI / MCP)
           |
           v
  Compatibility Classifier
           |
           +--> Governance Policy Engine
           |          |
           |          v
           |      Gate Decision
           |
           +--> Error Domain Mapper
                      |
                      v
                 Consistency Tests
```

### 1.2 核心组件

- **Compatibility Classifier**：判定变更级别。
- **Policy Engine**：按规则生成 warning/blocking 决策。
- **Error Mapper**：维护 API/MCP 错误语义映射。

---

## 2. 实现细节

### 2.1 文件结构

```text
docs/protocol/
├── VERSIONING.md
├── COMPATIBILITY_POLICY.md
├── ERROR_MODEL.md
└── GOVERNANCE_GATE_POLICY.md
```

### 2.2 集成点（何时、何处调用）

- PR 检查阶段：运行 diff -> classifier -> policy engine。
- 合并前检查阶段：运行 error consistency tests。
- 发布前检查阶段：生成 governance summary 报告。

### 2.3 数据模型

- `ChangeLevel`: compatible/additive/breaking
- `GateDecision`: pass/warn/block
- `ProtocolError`: code/category/retryable/incident_id

---

## 3. 数据流

```text
PR -> Contract Diff -> ChangeLevel
                  -> Policy Engine -> GateDecision
                  -> Error Mapper Consistency -> Pass/Fail
```

---

## 4. 错误处理

- 判定冲突：按更严格等级处理。
- 无法判定：返回 `manual-review-required` 并阻断自动通过。

---

## 5. 测试策略

- 单元：分级判断、错误映射。
- 集成：策略门禁决策链。
- 回归：API/MCP 错误一致性。

---

## 6. 迁移计划

- Phase 1：文档和规则草案。
- Phase 2：warning 门禁。
- Phase 3：blocking 门禁 + 演练。

---

## 7. 红军视角

- **攻击面**：人为篡改规则规避 blocking。  
  **防御**：分支保护 + required checks + 审计留痕。

- **攻击面**：错误映射只修文档不修实现。  
  **防御**：映射表与测试绑定，文档变更触发回归。

---

**维护者**：OwlClaw 架构组  
**最后更新**：2026-02-26
