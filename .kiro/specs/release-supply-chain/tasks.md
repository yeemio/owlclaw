# Tasks: Release Supply Chain

> **状态**：未开始  
> **预估工作量**：3-4 天  
> **最后更新**：2026-02-26

## 进度概览

- **总任务数**：12
- **已完成**：0
- **进行中**：0
- **未开始**：12

## 1. OIDC 发布

- [ ] 1.1 配置 TestPyPI Trusted Publisher
- [ ] 1.2 配置 PyPI Trusted Publisher
- [ ] 1.3 调整 workflow 使用 OIDC

## 2. 验证与证明

- [ ] 2.1 发布后执行 `pip install` smoke
- [ ] 2.2 生成并上传 provenance/attestation
- [ ] 2.3 归档发布报告（version/commit/run）

## 3. 门禁与保护

- [ ] 3.1 校准 required checks
- [ ] 3.2 校准 release 分支保护
- [ ] 3.3 校准失败回滚策略

## 4. 演练与收口

- [ ] 4.1 TestPyPI 全链路演练
- [ ] 4.2 PyPI 正式链路演练
- [ ] 4.3 更新 `SPEC_TASKS_SCAN` checkpoint

---

**维护者**：Release 工程组  
**最后更新**：2026-02-26
