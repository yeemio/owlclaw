# Mionyee 治理叠加 — 设计文档

> **Spec**: mionyee-governance-overlay
> **阶段**: Phase 8.1
> **接入模式**: 增强模式（Handler 轨）
> **接入口径**: L3（少量胶水代码）

---

## 1. 架构概览

```
Mionyee AI Service
    │
    ▼
OwlClaw Governance Proxy (sidecar)
    ├── Budget Gate (预算拦截)
    ├── Rate Limiter (限流)
    ├── Circuit Breaker (熔断)
    └── Ledger (审计记录)
    │
    ▼
litellm → LLM Provider
```

OwlClaw 治理代理作为 Mionyee LLM 调用的代理层，不修改 Mionyee 的业务逻辑，仅在 LLM 调用路径上插入治理检查。

## 2. 接入方式

### 2.1 Handler 轨注册

Mionyee 的 LLM 调用通过 `mionyee_platform/ai/client.py` 统一发出。接入方式：

```python
from owlclaw.governance import GovernanceProxy

proxy = GovernanceProxy.from_config("owlclaw.yaml")

# Mionyee 原有调用
# response = await litellm.acompletion(model=model, messages=messages)

# 治理代理包裹
response = await proxy.acompletion(model=model, messages=messages, caller="mionyee.ai.trading_decision")
```

改动量：Mionyee 侧约 5-10 行胶水代码（替换 LLM 调用入口）。

### 2.2 治理配置

```yaml
# owlclaw.yaml (Mionyee sidecar)
governance:
  budget:
    daily_limit_usd: 10.0
    monthly_limit_usd: 200.0
    alert_threshold: 0.8
  rate_limit:
    default_qps: 10
    per_service:
      trading_decision: 5
      knowledge_learning: 20
  circuit_breaker:
    failure_threshold: 5
    recovery_timeout_seconds: 60
    half_open_max_calls: 3
```

## 3. 核心组件

### 3.1 GovernanceProxy

封装 `owlclaw.governance.visibility` 的预算/限流/熔断能力，提供与 litellm 兼容的 `acompletion` 接口。

### 3.2 降级策略

OwlClaw 治理层不可用时（进程崩溃、配置错误）：
- GovernanceProxy 降级为直通模式（passthrough）
- 记录降级事件到本地日志
- 不阻塞 Mionyee 业务

### 3.3 Ledger 集成

每次调用记录到 OwlClaw Ledger（复用 `owlclaw.governance.ledger` 已有实现）：
- 成功调用：model, tokens, cost, latency
- 拦截事件：reason, rule, budget_remaining
- 熔断事件：failure_count, state_transition

## 4. 部署架构

Phase 1 采用 sidecar 部署（D2 附加条件）：

```
[Mionyee 服务器]
  ├── Mionyee FastAPI (port 8000)
  ├── OwlClaw Governance Proxy (in-process / sidecar)
  └── PostgreSQL (owlclaw database)
```

OwlClaw 使用独立 database（`owlclaw`），不与 Mionyee 数据库混用。

## 5. 测试策略

- **单元测试**：GovernanceProxy 的预算/限流/熔断逻辑
- **集成测试**：与 Mionyee LLM 调用链路的端到端验证
- **降级测试**：治理层故障时的 passthrough 行为
- **性能测试**：治理判定延迟 p99 < 10ms
