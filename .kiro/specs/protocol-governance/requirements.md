# Requirements: Protocol Governance

> **目标**：建立 API + MCP 协议治理基线（版本、兼容、错误域、弃用流程），使协议演进可控且可审计。  
> **优先级**：P0  
> **预估工作量**：3-5 天

---

## 1. 背景与动机

当前 `protocol-first-api-mcp` 已定义总方向，但发布阶段缺少可执行的协议治理规范，导致 breaking change 风险与跨语言不一致风险仍然偏高。

---

## 2. 用户故事

**故事 1**：作为架构负责人，我希望协议变更有统一分级与门禁，这样可以避免破坏客户端。  
**验收标准**：
- [ ] 变更分级（compatible/additive/breaking）可执行并文档化。
- [ ] breaking 变更无迁移计划时可被阻断。

**故事 2**：作为客户端开发者，我希望 API 与 MCP 错误语义一致，这样可以统一重试逻辑。  
**验收标准**：
- [ ] API 与 MCP 错误域映射表完整。
- [ ] 错误对象包含 `category/retryable/incident_id`。

---

## 3. 功能需求

### FR-1: 版本策略规范
- [ ] 输出 `docs/protocol/VERSIONING.md`
- [ ] 定义 API 版本选择策略与 MCP 版本协商策略
- [ ] 定义弃用窗口与兼容承诺

### FR-2: 兼容性政策
- [ ] 输出 `docs/protocol/COMPATIBILITY_POLICY.md`
- [ ] 定义 breaking 变更判定规则
- [ ] 定义迁移公告、灰度窗口、回滚条件

### FR-3: 错误域统一
- [ ] 输出 `docs/protocol/ERROR_MODEL.md`
- [ ] API（Problem Details）与 MCP 错误映射表
- [ ] 定义重试语义与排障字段

### FR-4: 门禁规则
- [ ] 输出 `docs/protocol/GOVERNANCE_GATE_POLICY.md`
- [ ] 定义 CI 阶段 warning/blocking 升级策略

---

## 4. 非功能需求

- **NFR-1 可追溯**：协议规则变更必须有审计记录。
- **NFR-2 一致性**：API/MCP 字段语义一致，避免双标准。
- **NFR-3 可执行**：所有规则可映射到 CI 检查项。

---

## 5. Definition of Done

- [ ] 四份协议治理文档齐全并通过评审。
- [ ] 至少 1 次模拟 breaking 变更被门禁阻断。
- [ ] API/MCP 错误域映射用例通过。

---

**维护者**：OwlClaw 架构组  
**最后更新**：2026-02-26

