# Tasks: Release Supply Chain

> **状态**：进行中  
> **预估工作量**：3-4 天  
> **最后更新**：2026-02-26

## 进度概览

- **总任务数**：15
- **已完成**：8
- **进行中**：0
- **未开始**：7

## 1. OIDC 发布

- [ ] 1.1 配置 TestPyPI Trusted Publisher
- [ ] 1.2 配置 PyPI Trusted Publisher
- [x] 1.3 调整 workflow 使用 OIDC

## 2. 验证与证明

- [x] 2.1 发布后执行 `pip install` smoke
- [x] 2.2 生成并上传 provenance/attestation
- [x] 2.3 归档发布报告（version/commit/run）

## 3. 门禁与保护

- [ ] 3.1 校准 required checks
- [ ] 3.2 校准 release 分支保护
- [x] 3.3 校准失败回滚策略

## 4. 演练与收口

- [ ] 4.1 TestPyPI 全链路演练
- [ ] 4.2 PyPI 正式链路演练
- [ ] 4.3 更新 `SPEC_TASKS_SCAN` checkpoint

## 5. 阈值与剧本固化

- [x] 5.1 固化成功率与时延阈值
- [x] 5.2 新增验收矩阵并绑定发布证据
- [x] 5.3 完成 T+0~T+15 处置剧本演练

---

**维护者**：Release 工程组  
**最后更新**：2026-02-26
