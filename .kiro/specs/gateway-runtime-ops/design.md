# Design: Gateway Runtime Ops

> **目标**：让发布决策从经验判断升级为 SLO 驱动。  
> **状态**：设计中  
> **最后更新**：2026-02-26

---

## 1. 架构设计

```text
Release Pipeline
   -> Canary Gate (SLO Check)
   -> Expansion Gate (SLO Check)
   -> Full Rollout Gate (SLO Check)
   -> Post Verification
           |
       rollback if fail
```

## 2. 实现细节

- `docs/ops/gateway-rollout-policy.md`
- `docs/ops/gateway-runbook.md`
- `docs/ops/gateway-slo.md`

### 集成点（何时、何处调用）

- 在每个发布阶段结束后调用 SLO evaluator。
- Gate 失败时调用 rollback executor。
- 回滚完成后调用 post-rollback verifier。

## 3. 数据流

```text
Deploy -> Metrics Window -> Gate Decision -> (Promote | Rollback)
```

## 4. 错误处理

- 指标缺失：默认阻断晋级。
- 告警系统故障：仅允许人工审批扩量。

## 5. 测试策略

- 演练 1：canary 触发错误率超阈，自动回滚。
- 演练 2：全路径晋级到全量。
- 演练 3：人工回滚路径。

## 6. 红军视角

- 攻击：缩短观察窗口绕过门控。  
  防御：窗口参数纳入受保护配置并审计。

---

**维护者**：平台运维组  
**最后更新**：2026-02-26
