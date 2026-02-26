# Design: Release Supply Chain

> **目标**：把发布链路提升到“默认安全 + 可追溯”。  
> **状态**：设计中  
> **最后更新**：2026-02-26

## 1. 发布链路

```text
Tag -> Release Workflow -> OIDC Auth -> Publish -> Attestation -> Verification
```

## 2. 集成点

- workflow 开始：校验 tag/branch/required checks
- publish 后：执行安装 smoke + provenance 归档
- 失败路径：触发回滚/重试 runbook

## 3. 错误处理

- OIDC 失败：阻断发布并输出配置诊断
- 发布后安装失败：标记发布失败并触发回滚策略

## 4. 红军视角

- 攻击：工作流或凭据篡改。  
  防御：分支保护、最小权限、来源证明验证。

---

## 5. 故障处置剧本（T+0 ~ T+15）

- `T+0`：发布失败（OIDC/上传/安装 smoke）自动中断。
- `T+3`：定位失败阶段并冻结后续 tag 发布。
- `T+6`：执行 TestPyPI 回放验证配置。
- `T+10`：确认回滚或重试策略并执行。
- `T+15`：发布状态公告与复盘记录。

---

**维护者**：Release 工程组  
**最后更新**：2026-02-26
