# Design: Protocol Governance

> **目标**：将协议治理从“文档建议”变成“可执行门禁”。  
> **状态**：设计中  
> **最后更新**：2026-02-26

---

## 1. 架构设计

```text
Contract Source (OpenAPI/MCP schema)
              |
              v
      Compatibility Analyzer
              |
      +-------+-------+
      |               |
  Governance Rules   Error Domain Mapper
      |               |
      +-------+-------+
              v
           CI Gate
```

核心思想：规则先文档化，再工具化，再门禁化。

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

### 2.2 关键规则

- `breaking`：字段删除/语义改变/默认行为逆转
- `additive`：新增可选字段/新增方法（默认不破坏）
- `compatible`：文案、示例、非语义变动

### 2.3 集成点

- PR 阶段：运行差异分析 -> 输出等级
- CI 阶段：依据等级和 gate policy 决定 warning/blocking

---

## 3. 错误处理

- 规则冲突：默认按更严格等级处理
- 无法判定：标记 `manual-review-required`

---

## 4. 测试策略

- 单元：分级规则判断
- 集成：模拟协议 diff -> gate 决策
- 回归：API/MCP 错误映射一致性

---

## 5. 风险与缓解

- 风险：规则过严影响速度  
  缓解：先 warning 再 blocking。

- 风险：映射表与实现漂移  
  缓解：契约测试强制校验。

---

## 6. 红军视角

- 如果团队绕过门禁直接合并怎么办？  
  答：将关键分支保护与 required checks 绑定，避免旁路。

---

**维护者**：OwlClaw 架构组  
**最后更新**：2026-02-26

