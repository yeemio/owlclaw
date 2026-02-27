# Tasks: Protocol-first API + MCP

> **状态**：已完成（通过子 spec 汇总收口）  
> **预估工作量**：10-15 天  
> **最后更新**：2026-02-27  
> **执行原则**：本清单内所有任务均须专业、认真完成，不区分可选与必选（见规范 §1.4、§4.5）。

---

## 进度概览

- **总任务数**：24
- **已完成**：24
- **进行中**：0
- **未开始**：0

---

## 1. Phase 1 — 协议宪法与门禁基线（2-3 天）

### 1.1 协议治理文档

- [x] 1.1.1 新增 `docs/protocol/VERSIONING.md`（API + MCP 统一版本策略）
- [x] 1.1.2 新增 `docs/protocol/ERROR_MODEL.md`（统一错误语义与映射表）
- [x] 1.1.3 新增 `docs/protocol/COMPATIBILITY_POLICY.md`（breaking 定义、弃用窗口、回滚流程）

### 1.2 契约门禁基础

- [x] 1.2.1 建立 API 契约差异检查脚本与 CI 接入（先 warning 后 blocking）
- [x] 1.2.2 建立 MCP 最小契约测试骨架（initialize/tools/resources）
- [x] 1.2.3 输出首次“协议差异报告”模板与样例

---

## 2. Phase 2 — 最小协议能力面（3-5 天）

### 2.1 API 最小能力面

- [x] 2.1.1 定义最小 API 3 端点契约（trigger/status/ledger query）
- [x] 2.1.2 为 3 端点补齐请求/响应/错误示例
- [x] 2.1.3 完成 3 端点契约测试
- [x] 2.1.4 明确与治理层的调用时机（何处执行 budget/rate-limit/ledger）

### 2.2 MCP 最小能力面

- [x] 2.2.1 明确 MCP 能力收敛范围（保持 tools/resources 核心路径）
- [x] 2.2.2 完成 MCP 核心路径回归（initialize/list/call/read）
- [x] 2.2.3 建立 API/MCP 错误域映射验收用例

### 2.3 集成点显式化

- [x] 2.3.1 在 design 中补充“何时、何处调用”矩阵（Gateway -> Policy -> Runtime）
- [x] 2.3.2 在 tasks 验收中绑定该矩阵的可执行检查

---

## 3. Phase 3 — 跨语言 Golden Path（3-4 天）

### 3.1 Java 接入样板

- [x] 3.1.1 新增 `docs/protocol/JAVA_GOLDEN_PATH.md`
- [x] 3.1.2 提供 Java 调用示例（触发 + 查询 + 错误处理）
- [x] 3.1.3 提供 curl 对照样例与字段对齐说明

### 3.2 可执行验收

- [x] 3.2.1 新增跨语言验证脚本（本地可执行）
- [x] 3.2.2 将至少 1 条跨语言验证接入 CI（nightly 或 main gate）
- [x] 3.2.3 生成跨语言验收记录（请求/响应证据）

---

## 4. Phase 4 — 运维与发布策略（2-3 天）

### 4.1 分阶段发布与回滚

- [x] 4.1.1 定义 canary -> 扩量 -> 全量 的协议发布流程
- [x] 4.1.2 定义协议回滚触发条件（错误率、超时率、兼容失败率）
- [x] 4.1.3 补充运行手册（降级与紧急回滚）

### 4.2 SLO 与可观测

- [x] 4.2.1 定义协议层 SLO 指标（可用性/时延/错误预算）
- [x] 4.2.2 补齐协议层日志字段规范（trace id / client id / error category）
- [x] 4.2.3 验证 SLO 指标可被观测系统采集

---

## 5. Phase 5 — 红军演练与收口（1-2 天）

### 5.1 红军演练

- [x] 5.1.1 演练 breaking 变更注入，验证 CI 门禁阻断
- [x] 5.1.2 演练版本协商失败，验证错误语义与升级指引
- [x] 5.1.3 演练回滚流程，验证 runbook 可执行

### 5.2 收口文档

- [x] 5.2.1 更新 `SPEC_TASKS_SCAN` 进度与 checkpoint
- [x] 5.2.2 输出“协议优先阶段总结”文档（决策、结果、遗留）
- [x] 5.2.3 确认后续 backlog（SDK 维护模式与协议增量路线）

---

## 6. 验收清单

### 6.1 功能验收

- [x] 协议版本策略、错误模型、兼容政策文档全部可执行落地
- [x] API 3 端点契约与回归通过
- [x] MCP 核心路径契约与回归通过
- [x] Java Golden Path 验收通过

### 6.2 性能验收

- [x] 协议层关键路径有基线时延数据
- [x] 协议层错误率与超时率可观测

### 6.3 测试验收

- [x] API 契约差异检测已接入 CI 并可阻断
- [x] MCP 契约测试已接入 CI
- [x] 红军演练用例通过

### 6.4 文档验收

- [x] `docs/protocol/` 下核心文档齐全
- [x] API/MCP 对齐矩阵齐全
- [x] 运行手册与回滚手册齐全

---

## 7. 依赖与阻塞

### 7.1 依赖

- `mcp-server` 既有实现与测试基线
- `triggers-api` 既有入口能力
- `test-infra` CI 能力（契约门禁运行环境）

### 7.2 阻塞

- release 外部凭据阻塞可能影响“发布流程实跑”验收项
- 若无 Java 验证环境，跨语言验收需先补环境

---

## 8. 风险

### 8.1 风险：治理门禁过严影响迭代速度

- **缓解**：Phase 1 先 warning，Phase 2 再升级 blocking。

### 8.2 风险：协议范围扩张失控

- **缓解**：严格限定最小能力面，非核心能力进 backlog。

### 8.3 风险：红军演练流于形式

- **缓解**：每次演练必须产生证据记录（日志、报告、复盘）。

---

## 9. 参考文档

- `docs/ARCHITECTURE_ANALYSIS.md`
- `.kiro/specs/mcp-server/`
- `.kiro/specs/triggers-api/`
- `.kiro/specs/release/`
- `.kiro/specs/test-infra/`

---

## 10. 证据映射（子 spec 汇总）

- protocol-governance：`docs/protocol/VERSIONING.md`、`ERROR_MODEL.md`、`COMPATIBILITY_POLICY.md`、`GOVERNANCE_GATE_POLICY.md`，以及治理演练脚本与报告。
- contract-testing：`scripts/contract_diff.py`、`tests/contracts/api/test_openapi_contract_gate.py`、`tests/contracts/mcp/test_mcp_contract_regression.py`、`docs/protocol/CONTRACT_TESTING_POLICY.md`。
- gateway-runtime-ops：`docs/ops/gateway-rollout-policy.md`、`docs/ops/gateway-runbook.md`、`docs/ops/gateway-slo.md` 与 gate/drill 脚本。
- cross-lang-golden-path：`docs/protocol/JAVA_GOLDEN_PATH.md`、`scripts/verify_cross_lang.ps1`、`docs/protocol/cross_lang_validation_latest.md`。
- 协议阶段总结：`docs/protocol/PROTOCOL_FIRST_PHASE_SUMMARY.md`。

**维护者**：OwlClaw 架构组  
**最后更新**：2026-02-27
