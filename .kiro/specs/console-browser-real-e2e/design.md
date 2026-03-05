# console-browser-real-e2e — 设计文档

> **目标**: 建立真实浏览器验收流水线（自动化 + 手工 + 审校）  
> **状态**: 设计完成  
> **最后更新**: 2026-03-05

---

## 1. 架构设计

```text
Env Setup -> Service Up -> Playwright Auto -> Manual Checklist -> Review Verdict
```

### 组件职责
- 自动化组件：Playwright 场景与断言。
- 手工组件：Checklist 执行与证据采集。
- 审校组件：汇总结果并给放行结论。

---

## 2. 实现细节

### 2.1 自动化覆盖
- 修正/增强 `owlclaw/web/frontend/e2e/console.spec.ts`：
- 使用 `baseURL + /console/`，避免硬编码端口。
- 增加关键页面断言与网络请求断言。

### 2.2 真实环境脚本
- 复用并扩展 `scripts/console-local-setup.ps1`。
- 目标：从“初始化 DB -> 启动服务 -> 执行 e2e”一条链路可执行。

### 2.3 手工检查
- 按 `BROWSER_VERIFICATION_CHECKLIST.md` 填充未覆盖项：
- WS 退化行为
- 视觉/响应式/可访问性
- 空状态与错误展示

### 2.4 审校报告
- 统一输出到 `.kiro/reviews/YYYY-MM-DD-console-browser-verification.md`。
- 结论分级：PASS / CONDITIONAL_PASS / FAIL。

---

## 3. 测试策略

- 自动化测试：`npm run test:e2e`、`npm run test:e2e:manual`
- 辅助 API 校验：curl 检查关键接口与错误码
- 审校验证：检查证据完整性和可复现性

---

## 4. 风险与缓解

- 端口/环境漂移：统一使用 8000 与健康检查门禁。
- 外部依赖缺失：明确降级预期，不以 500 失败收口。

---

**维护者**: orchestrator  
**最后更新**: 2026-03-05
