# Console Browser Real E2E Precheck (review-work)

> 目的：对 `console-browser-real-e2e` 的 B1~B4 做一键预审  
> 适用分支：`review-work`  
> 最后更新：2026-03-05

## 0. 基础信息

- 审校人：
- 审校时间：
- 目标分支：`codex-work`
- 对照 spec：`.kiro/specs/console-browser-real-e2e/`

## 1. 一键执行

```powershell
git merge main
git log --oneline main..codex-work
git diff --stat main..codex-work

cd owlclaw/web/frontend
npm run test:e2e:run
```

通过门槛：
- `test:e2e:run` 为 `33 passed`
- 手工报告存在且包含失败复现列表
- checklist 已回写最新状态

## 2. 证据清单

- 自动化证据：
  - `.kiro/reviews/2026-03-05-console-browser-automation-codex-work.md`
  - `owlclaw/web/frontend/e2e/console-flow.spec.ts`
- 手工证据：
  - `.kiro/reviews/2026-03-05-console-browser-manual-codex-work.md`
  - `docs/console/BROWSER_VERIFICATION_CHECKLIST.md`
  - `scripts/console-local-setup.ps1`
  - `docs/console/REAL_E2E_LOCAL_SETUP.md`

## 3. 风险核对

- [ ] 无 DB 降级路径无 500 白屏
- [ ] 无敏感信息泄露（token/key）
- [ ] WS 风险已显式记录（`N-8` 阻塞原因明确）
- [ ] 手工未通过项均有复现与建议

## 4. 结论模板

### PASS

```text
review(console-browser-real-e2e): PASS — 自动化与手工证据完整，阻断项已清零
```

### CONDITIONAL_PASS

```text
review(console-browser-real-e2e): CONDITIONAL_PASS — 核心路径通过，剩余项已登记风险与复验计划
```

### FAIL

```text
review(console-browser-real-e2e): FAIL — 存在阻断级缺口（自动化红灯/无复现证据/高风险未收敛）
```
