# Tasks: Release Supply Chain

> **状态**：进行中  
> **预估工作量**：3-4 天  
> **最后更新**：2026-02-27

## 进度概览

- **总任务数**：15
- **已完成**：10
- **进行中**：0
- **未开始**：5

## 1. OIDC 发布

- [ ] 1.1 配置 TestPyPI Trusted Publisher
- [ ] 1.2 配置 PyPI Trusted Publisher
- [x] 1.3 调整 workflow 使用 OIDC

## 2. 验证与证明

- [x] 2.1 发布后执行 `pip install` smoke
- [x] 2.2 生成并上传 provenance/attestation
- [x] 2.3 归档发布报告（version/commit/run）

## 3. 门禁与保护

- [x] 3.1 校准 required checks
  - 验证（2026-02-27）：`gh api repos/yeemio/owlclaw/branches/main/protection` 返回 `200`，`required_status_checks.contexts = [Lint, Test, Build]`，`strict = true`
- [ ] 3.2 校准 release 分支保护
  - 当前状态（2026-02-27）：`gh api repos/yeemio/owlclaw/rulesets` 返回空数组 `[]`，未发现规则集保护（外部仓库设置项）
- [x] 3.3 校准失败回滚策略

## 4. 演练与收口

- [ ] 4.1 TestPyPI 全链路演练
  - 演练记录（2026-02-26）：run `22446541468` 在 `Publish to TestPyPI` 返回 `HTTP 403 Forbidden`，阻塞点为 Trusted Publisher 绑定未完成（对应 Task 1.1）
  - 演练记录（2026-02-27）：run `22471143360` 在 `Publish to TestPyPI` 再次返回 `HTTP 403 Forbidden`，说明 workflow 和分支保护已就绪，但 TestPyPI Trusted Publisher 仍未绑定
- [ ] 4.2 PyPI 正式链路演练
  - 当前状态（2026-02-27）：前置 TestPyPI OIDC 未打通，正式链路演练顺延（依赖 Task 1.2/3.2）
- [x] 4.3 更新 `SPEC_TASKS_SCAN` checkpoint

## 5. 阈值与剧本固化

- [x] 5.1 固化成功率与时延阈值
- [x] 5.2 新增验收矩阵并绑定发布证据
- [x] 5.3 完成 T+0~T+15 处置剧本演练

---

**维护者**：Release 工程组  
**最后更新**：2026-02-27
