# Console E2E 深度测试差距分析

> **依据**：BROWSER_TEST_REQUIREMENTS.md 四维度 + Playwright 官方实践 + 行业最佳实践  
> **日期**：2026-03-04

---

## 一、当前覆盖 vs 要求的差距

### 1. API 契约维度

| 要求 | 现状 | 差距 |
|------|------|------|
| 每端点 ≥1 成功 + 1 边界/错误 | 仅验证请求发出、部分验证 URL 参数 | **未校验响应 schema**：overview/agents/ledger 等返回的 JSON 结构是否符合契约 |
| 前端请求格式与 Backend 一致 | 仅验证 agent_id、granularity 等参数存在 | **未校验完整 request body/query**：缺 Zod/Ajv 等 schema 校验 |
| 422/404 等错误响应结构 | 未在 E2E 中显式校验 | **未校验 ErrorResponse 结构**：`{error:{code, message}}` |

### 2. 负向路径 / 错误边界

| 场景 | 要求 | 现状 |
|------|------|------|
| API 500 | UI 显示友好错误，不白屏 | 仅 agents 列表有空状态；**未测 overview/governance 500 时的降级** |
| API 超时 | 显示重试或错误提示 | 未测 |
| 响应格式异常（缺字段、类型错误） | 不崩溃、友好降级 | 未测 |
| 无效参数（如 order_by=invalid） | 422 + 前端不崩溃 | 未在 E2E 中测 |

### 3. 可访问性（效果维度）

| 要求 | 现状 |
|------|------|
| WCAG AA 对比度、标签、键盘 | 仅有 Tab 键遍历；**未用 axe-core 做自动化 a11y 扫描** |
| 对比度、重复 ID、无 label | 未覆盖 |

### 4. 代码/网络维度

| 要求 | 现状 |
|------|------|
| Console 无未捕获 JS 错误 | 隐式（Playwright 未报即通过）；**未显式监听 page.on('pageerror')** |
| 每页 Network 无意外 4xx/5xx | 已有，但未逐页、逐请求记录 |
| HAR/截图作为证据 | **未产出**：无 HAR 录制、无失败时截图 |

### 5. 测试设计

| 最佳实践 | 现状 |
|----------|------|
| 每测独立 storage/cookies | 默认共用 context，可能有状态泄露 |
| 正负路径配对 | 仅有正路径，负路径极少 |
| Page Object 复用 | 无 POM，选择器分散 |
| 契约即测试（Contract as Test） | 未用 schema 驱动断言 |

---

## 二、行业参考

- **Playwright 官方**：axe-core 做 a11y；route/fulfill 做 API mock；page.on('response') 做网络监控；waitForRequest 可校验 request 契约
- **深度 vs 广度**：先广度（关键路径）再深度（边界、负向、契约）
- **负向测试**：一次只翻转一个假设（如 valid→invalid、available→timeout），验证**安全失败**而非崩溃

---

## 三、学习与实践（2026-03-04 更新）

### 3.1 行业参考

| 来源 | 要点 |
|------|------|
| **QA Wolf** | 先广度后深度：先覆盖所有关键用户流程，再对单点深入；风险模型（复杂度/新近度/安全/依赖/收入/用户活跃） |
| **Playwright 官方** | `page.route('**/api/v1/xxx')` 用 glob 拦截，`route.fulfill()` mock 响应；注册 route **必须在** 触发请求之前 |
| **负向测试** | 一次只翻转一个假设（valid→invalid）；验证**安全失败**（友好错误、不白屏）而非崩溃 |
| **Happy/Sad/Edge** | 每主流程应覆盖：happy path + sad path（500/422/timeout）+ edge（异常响应、缺字段） |

### 3.2 已补深度用例

| 类型 | 用例 | 实现 |
|------|------|------|
| 负向 | Overview 500 → 友好错误 | `page.route("**/api/v1/overview")` 返回 500 |
| 负向 | Governance 500 | `page.route("**/api/v1/governance/**")` 返回 500 |
| 负向 | Ledger 422 | `page.route("**/api/v1/ledger*")` 返回 422 |
| 契约 | Governance API | budget: start_date/end_date/granularity/items；circuit-breakers: items[] |
| 效果 | axe WCAG | Overview / Governance / Ledger 三页 axe 扫描 |
| Edge | 畸形 JSON | 200 + "not valid json" → 不白屏、显示错误态 |

### 3.3 Route 匹配要点

- 使用 glob `**/api/v1/overview` 比 regex 更稳定
- `page.route` / `context.route` 必须在 `page.goto` 之前注册
- Ledger 带 query：`**/api/v1/ledger*` 可匹配
- **Governance/Ledger 负向**：用 `page.context().route()` + 直接 navigate 到 `/console/governance`、`/console/ledger`，避免先加载 Overview 再点击导致的拦截不稳定

---

## 四、建议补齐（按优先级）

| 优先级 | 项 | 实现方式 |
|--------|------|----------|
| P0 | API 响应 schema 校验 | waitForResponse + JSON 结构断言（或 Zod parse） |
| P0 | 负向：API 500 时 UI 不白屏 | route.fulfill 500 → 断言有错误文案或空状态 |
| P0 | Console 未捕获错误 | page.on('pageerror') → expect 无触发 |
| P1 | axe-core WCAG 扫描 | @axe-core/playwright，至少 Overview/Governance/Ledger |
| P1 | Request 契约校验 | waitForRequest + 校验 query/body 符合预期 |
| P2 | HAR 录制（失败时） | playwright.config reporter 或 testInfo.attach |
| P2 | 测试隔离 | test.describe.configure 或 beforeEach 清理 |
| P2 | Ledger order_by 422 | 前端未暴露 order_by 时，可 mock 422 验证错误态 |
