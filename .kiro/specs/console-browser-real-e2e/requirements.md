# console-browser-real-e2e — 真实浏览器验收

> **目标**: 以真实浏览器+真实服务链路完成 Console 发布前验收闭环  
> **优先级**: P1（发布质量门，非代码功能新增）  
> **预估工作量**: 2-3 天

---

## 1. 背景与动机

当前 Console 验收主要依赖 pytest 与局部 E2E，缺少对 `docs/console/BROWSER_TEST_REQUIREMENTS.md` 的完整落地执行与证据化留存。

---

## 2. 用户故事

### 2.1 作为发布负责人
```
作为 发布负责人
我希望 在真实浏览器环境下完成 Console 全维度验收
这样我可以 基于证据而非主观判断决定放行
```

**验收标准**：
- [ ] 浏览器验证覆盖功能/API/网络/效果四维
- [ ] 报告落盘到 `.kiro/reviews/YYYY-MM-DD-console-browser-verification.md`

---

## 3. 功能需求

### FR-B1：自动化覆盖关键路径
- Overview → Governance → Ledger → Agents 四条主路径须有 Playwright 自动化覆盖。
- 验收：
- [ ] 自动化脚本稳定运行（至少 1 次完整通过）
- [ ] 关键 API 调用与参数断言可追溯

### FR-B2：手工探索覆盖剩余检查项
- 自动化未覆盖项（视觉、空状态、可访问性、WS 退化等）由手工验收补齐。
- 验收：
- [ ] 手工项有明确“通过/失败/风险”记录

### FR-B3：真实环境脚本化启动
- 提供一键化本地准备与启动步骤（DB 初始化、服务启动、E2E 运行）。
- 验收：
- [ ] 文档和脚本可在新会话复现

### FR-B4：放行结论标准化
- 审校 worktree 输出 PASS/CONDITIONAL_PASS/FAIL 与阻塞项。
- 验收：
- [ ] 审校报告可直接用于发布决策

---

## 4. 非功能需求

### NFR-B1：证据可追溯
- 每个检查项关联日志、截图、请求摘要或测试输出。
- [ ] 证据索引完整

### NFR-B2：最小侵入
- 不改变业务行为语义，仅补充测试与验证保障。
- [ ] 变更主要集中在测试/文档/脚本

---

## 5. 验收总览

- [ ] 自动化验收通过
- [ ] 手工验收通过或给出条件放行
- [ ] 审校报告完成并归档

---

## 6. 依赖与风险

### 依赖
- `docs/console/BROWSER_TEST_REQUIREMENTS.md`
- `docs/console/BROWSER_VERIFICATION_CHECKLIST.md`
- `owlclaw/web/frontend/playwright.config.ts`

### 风险
- 本地环境差异导致偶发失败：通过固定端口、健康检查、重试策略缓解。

---

**维护者**: orchestrator  
**最后更新**: 2026-03-05
