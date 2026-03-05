# console-browser-real-e2e — 任务清单

> **状态**: 进行中  
> **预估工作量**: 2-3 天  
> **最后更新**: 2026-03-05

---

## 进度概览

- **总任务数**: 13
- **已完成**: 7
- **进行中**: 0
- **未开始**: 6

---

## 0. 文档准备

- [x] 0.1 requirements.md
- [x] 0.2 design.md
- [x] 0.3 tasks.md

---

## 1. codex-work（自动化主路径 + 网络断言）

- [x] 1.1 修复/增强 Playwright 场景基址与导航断言
- [x] 1.2 增加 Overview/Governance/Ledger/Agents 核心断言
- [x] 1.3 增加关键 API 请求参数断言（筛选/分页/order_by）
- [x] 1.4 产出自动化执行结果摘要
  - 代码：`owlclaw/web/frontend/e2e/console-flow.spec.ts`、`owlclaw/web/frontend/e2e/console.spec.ts`
  - 执行：`npm run test:e2e:run`（33 passed）
  - 摘要：`.kiro/reviews/2026-03-05-console-browser-automation-codex-work.md`

---

## 2. codex-gpt-work（真实环境脚本 + 手工维度）

- [ ] 2.1 强化本地真实环境启动脚本与步骤文档
- [ ] 2.2 执行 Checklist 中手工项（WS/效果/可访问性）
- [ ] 2.3 记录失败项与复现步骤

---

## 3. review-work（审校放行）

- [ ] 3.1 审查自动化与手工证据完整性
- [ ] 3.2 复核高风险项（无 DB 降级、无敏感泄露、无白屏）
- [ ] 3.3 输出 `.kiro/reviews/YYYY-MM-DD-console-browser-verification.md`

---

## 4. 验收清单

- [ ] 4.1 浏览器四维验收闭环完成
- [ ] 4.2 产出放行结论（PASS/CONDITIONAL_PASS/FAIL）
- [ ] 4.3 SPEC_TASKS_SCAN 与 WORKTREE_ASSIGNMENTS 对齐

---

**维护者**: orchestrator  
**最后更新**: 2026-03-05
