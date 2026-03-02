# 总架构师审计报告 — 2026-03-02

> **审计范围**：架构设计 → Spec 文档 → 代码实现 三层全面审视
> **审计方法**：架构文档对照、核心模块代码深度阅读、集成隔离验证、Console 端到端可用性验证、测试质量抽样

---

## 问题清单

### Critical（必须修复）

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| C1 | 熔断器永远不会打开 | `governance/constraints/circuit_breaker.py:82` | CircuitBreaker 检查 `"failure"` 但 Runtime 写 `"error"/"timeout"` |
| C2 | Console API 无法挂载 | `web/mount.py:49` | 导入 `owlclaw.web.api.app`（不存在），API 全部 404 |

### High（应尽快修复）

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| H1 | Heartbeat 4/5 事件源 stub | `agent/runtime/heartbeat.py:191-273` | Heartbeat 机制形同虚设 |
| H2 | 成本追踪未实现 | `agent/runtime/runtime.py` | estimated_cost 永远为 0，预算限制不触发 |
| H3 | litellm embedding 绕过集成层 | `agent/memory/embedder_litellm.py:60` | 违反架构隔离规则 |
| H4 | Console Governance 数据映射错误 | `web/frontend/src/hooks/useApi.ts` | 熔断器显示 unknown，矩阵结构不匹配 |
| H5 | 治理评估器 fail-open | `governance/visibility.py:277-284` | 异常时 capability 保持可见 |

### Medium（建议修复）

| # | 问题 |
|---|------|
| M1 | 架构文档 Heartbeat 接口漂移 |
| M2 | 架构文档未覆盖多个已实现模块 |
| M3 | `owlclaw.tools` stub 与 `owlclaw.agent.tools` 冲突 |
| M4 | Ledger fallback 日志路径硬编码 |
| M5 | Queue/DB Change 触发器依赖抽象适配器 |

---

## 评分

| 维度 | 评分 |
|------|------|
| 包结构 vs 架构文档 | 96% |
| 核心模块实现真实性 | 85% |
| 集成层隔离 | 92% |
| 治理层有效性 | 60% |
| Console 可用性 | 30% |
| 测试覆盖质量 | 70% |

---

## 修复 Spec

- `audit-fix-critical`：C1 + C2（1 天，P0）
- `audit-fix-high`：H1-H5（3-5 天，P1）
