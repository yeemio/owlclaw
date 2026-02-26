# Requirements: Release Supply Chain

> **目标**：将发布链路升级为安全、可验证、可追溯（OIDC Trusted Publishing + provenance）。  
> **优先级**：P0  
> **预估工作量**：2-4 天

## 1. 功能需求

### FR-1 Trusted Publishing
- [ ] 使用 OIDC 发布到 PyPI/TestPyPI
- [ ] 移除长期 token 依赖（或降级为紧急备用）

### FR-2 发布证明
- [ ] 产出发布 provenance/attestation
- [ ] 发布产物可追溯到 commit 与 workflow run

### FR-3 发布门禁
- [ ] 分支保护 required checks 对齐发布需求
- [ ] 发布前必须通过契约与安全检查

## 2. DoD

- [ ] 从 tag 到 PyPI 发布链路全自动通过
- [ ] 产物可验证来源
- [ ] 发布失败具备回滚/重试手册

---

**维护者**：Release 工程组  
**最后更新**：2026-02-26

