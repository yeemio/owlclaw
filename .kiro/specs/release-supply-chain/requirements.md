# Requirements: Release Supply Chain

> **目标**：建立发布供应链安全基线（OIDC Trusted Publishing + provenance + release gate）。  
> **优先级**：P0  
> **预估工作量**：3-4 天

## 1. 功能需求

### FR-1 Trusted Publishing
- [ ] 配置 TestPyPI/PyPI OIDC 发布
- [ ] 降低长期 token 依赖

### FR-2 产物可验证
- [ ] 生成并保存 provenance/attestation
- [ ] 发布产物可追溯到 commit 与 workflow run

### FR-3 发布门禁
- [ ] 发布前通过契约测试、安全检查、基础安装验证

## 2. DoD

- [ ] 从 tag 到发布链路自动通过
- [ ] 产物可验证来源
- [ ] 失败具备回滚/重试手册

---

**维护者**：Release 工程组  
**最后更新**：2026-02-26
