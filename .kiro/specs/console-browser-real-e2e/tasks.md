# console-browser-real-e2e — 任务清单

> **状态**: 已完成（Conditionally Passed）  
> **预估工作量**: 2-3 天  
> **最后更新**: 2026-03-05（审校收口）

---

## 进度概览

- **总任务数**: 13
- **已完成**: 13
- **进行中**: 0
- **未开始**: 0

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
  - 执行：`npm run test:e2e:run`（38 passed）
  - 摘要：`.kiro/reviews/2026-03-05-console-browser-automation-codex-work.md`

---

## 2. codex-gpt-work（真实环境脚本 + 手工维度）

- [x] 2.1 强化本地真实环境启动脚本与步骤文档
  - 脚本：`scripts/console-local-setup.ps1`
  - 文档：`docs/console/REAL_E2E_LOCAL_SETUP.md`、`docs/console/BROWSER_VERIFICATION_CHECKLIST.md`（2026-03-05 执行补充）
- [x] 2.2 执行 Checklist 中手工项（WS/效果/可访问性）
  - 证据：`.kiro/reviews/artifacts/2026-03-05-console-browser/api-checks.json`
  - 报告：`.kiro/reviews/2026-03-05-console-browser-verification.md`
- [x] 2.3 记录失败项与复现步骤
  - M-1：`/api/v1/ws` 返回 404（WS 通道未建立）
  - M-2：`npm run test:e2e` 缺少 `start-server-and-test`

---

## 3. review-work（审校放行）

- [x] 3.1 审查自动化与手工证据完整性
  - codex-work Task 1.1~1.4：33/33 E2E 测试通过
  - codex-gpt-work Task 2.1~2.3：报告完整，失败项已记录
  - 轻量修复：Triggers selector 添加 `exact: true`（review-work 9f4df5a）
- [x] 3.2 复核高风险项（无 DB 降级、无敏感泄露、无白屏）
  - 无 DB 降级：✅ API 返回友好错误，无 500 白屏
  - 无敏感泄露：✅ 配置/密钥未在前端暴露
  - 无白屏：✅ 所有页面有空状态或降级文案
  - 待补项：N-8（WS 消息）、F-16（Agent 详情）、F-18（Triggers 真实数据）、F-20（外链可达性）、E-2/E-9（响应式/对比度）
- [x] 3.3 输出 `.kiro/reviews/YYYY-MM-DD-console-browser-verification.md`
  - 已输出：`docs/console/2026-03-05-console-browser-verification.md`（codex-gpt-work）
  - 审校结论：CONDITIONAL_PASS

---

## 4. 验收清单

- [x] 4.1 浏览器四维验收闭环完成
  - 功能维度：F-1/F-2/F-5/F-6/F-7/F-8/F-9/F-10/F-11/F-12/F-13/F-14/F-15/F-17/F-19 ✅
  - API 维度：API-1~API-17 ✅
  - 代码/网络：N-1~N-7/N-9/N-10 ✅，N-8 待补
  - 效果维度：E-1/E-3/E-4/E-5/E-6/E-7/E-8 ✅，E-2/E-9 待补
- [x] 4.2 产出放行结论（PASS/CONDITIONAL_PASS/FAIL）
  - **结论**: CONDITIONAL_PASS
  - 条件：待补 6 项（N-8、F-16、F-18、F-20、E-2、E-9）需在有 DB/WS 环境补验收
- [x] 4.3 SPEC_TASKS_SCAN 与 WORKTREE_ASSIGNMENTS 对齐

---

**维护者**: orchestrator  
**最后更新**: 2026-03-05（审校收口）
