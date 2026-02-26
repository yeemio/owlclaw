# Design: Release Supply Chain

> **目标**：发布过程默认安全，且外部可验证。  
> **状态**：设计中  
> **最后更新**：2026-02-26

## 1. 流程

```text
Tag -> CI Release Workflow -> OIDC Auth -> Publish -> Attestation -> Verify
```

## 2. 关键设计

- 使用 Trusted Publishing（OIDC）替代长期凭据。
- 发布后自动验证 `pip install` 与基础 smoke。
- 生成并存档 attestation 与发布报告。

## 3. 风险

- 仓库权限配置错误导致发布失败。  
  缓解：先 TestPyPI 演练，再切 PyPI。

## 4. 红军视角

- 攻击：工作流被篡改后发布恶意包。  
  防御：分支保护 + required reviewers + provenance 验证。

---

**维护者**：Release 工程组  
**最后更新**：2026-02-26

