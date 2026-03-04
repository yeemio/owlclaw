# OwlClaw Console 浏览器验证报告

> **执行日期**：2026-03-04  
> **要求来源**：`docs/console/BROWSER_TEST_REQUIREMENTS.md`  
> **清单**：`docs/console/BROWSER_VERIFICATION_CHECKLIST.md`  
> **环境**：无 DB、无 Hatchet、无 Langfuse（Lite 场景）

---

## 一、执行摘要

| 门禁 | 结果 | 说明 |
|------|------|------|
| 无 500 白屏 | ✅ 通过 | 主页面可打开，agents 列表 API 降级正确；agents/{id}、triggers 在无 DB 时仍返回 500 |
| API 契约一致 | ⚠️ 部分 | 多数通过，agents/{id}、triggers 在无 DB 时返回 500（见 BUG-1、BUG-2） |
| 关键路径可走通 | ✅ 通过 | Overview → Governance → Ledger → Agents + Capabilities/Settings，Playwright 9/9 通过 |
| 无敏感信息泄露 | ✅ 通过 | Network/响应无 token 泄露 |

**放行建议**：**有条件通过** — 修复 P1 缺陷（BUG-1、BUG-2）后可正式放行。当前自动化覆盖达到测试总监要求的最低覆盖，核心主路径均已验证。

---

## 二、API 维度

| 步骤 | 端点 | 预期 | 实际 | 通过 |
|------|------|------|------|------|
| API-1 | GET /api/v1/overview | 200，含 health_checks | 200，health_checks 含 runtime/db/hatchet/llm | ✅ |
| API-2 | 无 DB 时 overview | db healthy:false | ✓ | ✅ |
| API-3 | GET /api/v1/agents | 200，items:[], message | `{"items":[],"message":"Database not configured"}` | ✅ |
| API-4 | GET /api/v1/agents/{id} | 404 | **500**，ConfigurationError | ❌ BUG-1 |
| API-5 | GET /api/v1/governance/budget | 200，granularity | ✓ | ✅ |
| API-6 | GET /api/v1/governance/circuit-breakers | 200 | ✓ | ✅ |
| API-8 | GET /api/v1/ledger | 200，PaginatedResponse | `{items:[],total:0,offset:0,limit:5}` | ✅ |
| API-9 | ledger?order_by=invalid | 422，ErrorResponse | `{error:{code:"VALIDATION_ERROR",...}}` | ✅ |
| API-11 | GET /api/v1/capabilities | 200，items | `{items:[]}` | ✅ |
| API-13 | GET /api/v1/triggers | 200 | **500**，ConfigurationError | ❌ BUG-2 |
| API-15 | GET /api/v1/settings | 200 | 200，含 runtime,mcp,database,owlhub | ✅ |

---

## 三、功能维度（Playwright 自动化）

| 步骤 | 操作 | 测试用例 | 通过 |
|------|------|----------|------|
| F-1~F-2 | Overview 进入与指标 | `Overview -> Governance -> Ledger navigation` | ✅ |
| F-6 | Governance 进入 | 同上 + `Governance page triggers governance API calls` | ✅ |
| F-7 | 切换时间粒度 day→week | `Governance granularity switch triggers new API request (F-7)` | ✅ |
| F-10 | Ledger 进入 | `Ledger filter panel and empty state` | ✅ |
| F-11 | Ledger Apply 筛选 | `Ledger Apply filter triggers new API request with params (F-11)` | ✅ |
| F-15 | Agents 空状态 | `Overview -> Agents navigation and empty state` | ✅ |
| F-17 | Capabilities | `Capabilities and Settings pages load` | ✅ |
| F-19 | Settings | 同上 | ✅ |

**Playwright 测试清单**（`owlclaw/web/frontend/e2e/console-flow.spec.ts`）：

1. Overview → Governance → Ledger navigation
2. Overview → Agents navigation and empty state
3. Governance page triggers governance API calls
4. **Governance granularity switch triggers new API request (F-7)**
5. **Ledger Apply filter triggers new API request with params (F-11)**
6. Ledger filter panel and empty state
7. First load under 5s
8. Capabilities and Settings pages load
9. Tab key traverses sidebar

**运行**：`cd owlclaw/web/frontend && npm run test:e2e` — 9/9 通过（含 start-server-and-test 启停服务）

---

## 四、代码/网络维度

| 步骤 | 检查项 | 结果 | 通过 |
|------|--------|------|------|
| N-1 | GET /api/v1/overview 有请求 | 有 | ✅ |
| N-2 | Governance 有 governance/* 请求 | 有 budget/circuit-breakers/visibility-matrix | ✅ |
| N-3 | Ledger 有 GET /api/v1/ledger | 有 limit、offset | ✅ |
| N-4 | 改 Ledger 筛选 | Apply 后新请求带 agent_id | ✅ |
| N-5 | Agents 有 GET /api/v1/agents | 有 | ✅ |
| N-6 | /console/assets/* 无 404 | 200 | ✅ |
| N-9 | 无 DB 时无 500 | agents 列表 200；agents/{id}、triggers 仍 500 | ❌ |
| N-10 | Console 无未捕获 JS 错误 | Playwright 未报 | ✅ |

---

## 五、效果维度

| 步骤 | 检查项 | 结果 | 通过 |
|------|--------|------|------|
| E-1 | 暗色主题 | 默认 dark，无白底闪屏（Playwright 可见） | ✅ |
| E-4 | Agents 无 DB 空状态 | "No agents found" 友好文案 | ✅ |
| E-5 | Ledger 无数据 | "No ledger records" 或 Reset Filters | ✅ |
| E-7 | 首屏加载 < 5s | `First load under 5s` 通过 | ✅ |
| E-8 | Tab 键遍历 | `Tab key traverses sidebar` 通过 | ✅ |

---

## 六、缺陷列表

| ID | 严重程度 | 描述 | 复现 |
|----|----------|------|------|
| BUG-1 | P1 | `GET /api/v1/agents/{id}` 在无 DB 时返回 500，应 404 或 200+空 | `curl http://localhost:8000/api/v1/agents/nonexistent` |
| BUG-2 | P1 | `GET /api/v1/triggers` 在无 DB 时返回 500，应降级返回空 | `curl http://localhost:8000/api/v1/triggers` |

---

## 七、交付物

- [x] 执行报告（本文档）
- [x] 清单打勾（BROWSER_VERIFICATION_CHECKLIST.md 已更新）
- [x] 缺陷列表（见第六节）
- [x] 放行建议：**有条件通过**，修复 BUG-1、BUG-2 后复验

---

## 八、可追溯性

| 测试项 | Spec 对应 |
|--------|----------|
| F-1~F-5 | console-frontend/requirements.md Overview |
| F-6~F-9 | console-frontend/requirements.md Governance |
| F-10~F-14 | console-frontend/requirements.md Ledger |
| F-15~F-16 | console-frontend/requirements.md Agents |
| F-17、F-19 | console-frontend/requirements.md Capabilities/Settings |
| API-* | console-backend-api/design.md |
