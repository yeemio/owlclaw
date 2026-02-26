# Design: Gateway Runtime Ops

> **目标**：将网关运行从“人工经验”转为“标准流程 + 自动门控”。  
> **状态**：设计中  
> **最后更新**：2026-02-26

---

## 1. 架构设计

```text
Deploy Pipeline -> Canary Stage -> Expansion Stage -> Full Rollout
                          |                |               |
                        SLO Gate         SLO Gate        SLO Gate
                          |                |               |
                     rollback if fail  rollback if fail   stable
```

---

## 2. 实现细节

- 运行手册：`docs/ops/gateway-runbook.md`
- 指标定义：`docs/ops/gateway-slo.md`
- 发布策略：`docs/ops/gateway-rollout-policy.md`

关键集成点：
- 发布 pipeline 在每阶段读取同一套 SLO 门槛。
- 回滚由统一脚本触发并记录事件。

---

## 3. 错误处理

- 指标采集故障 -> 默认阻断扩量
- 探针异常 -> 自动触发降级/回滚

---

## 4. 测试策略

- 演练：一次 canary 失败自动回滚
- 演练：一次正常扩量到全量
- 演练：手动回滚路径

---

## 5. 红军视角

- 攻击：在监控延迟期间快速扩量。  
  防御：扩量前必须满足连续窗口稳定条件。

---

**维护者**：平台运维组  
**最后更新**：2026-02-26

