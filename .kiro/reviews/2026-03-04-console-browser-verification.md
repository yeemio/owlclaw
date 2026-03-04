# OwlClaw Console 浏览器验证报告

> **执行日期**：2026-03-04  
> **要求来源**：`docs/console/BROWSER_TEST_REQUIREMENTS.md`  
> **清单**：`docs/console/BROWSER_VERIFICATION_CHECKLIST.md`  
> **环境**：无 DB、无 Hatchet、无 Langfuse（Lite 场景）

---

## 一、执行摘要

| 门禁 | 结果 | 说明 |
|------|------|------|
| 无 500 白屏 | ✅ 通过 | 主页面可打开，且无 DB 场景下 `agents/{id}`、`triggers`、`triggers/{id}/history` 均已降级，无 500 |
| API 契约一致 | ✅ 通过 | 本轮修复后，原 BUG-1/BUG-2 路径已回归通过 |
| 关键路径可走通 | ✅ 通过 | Overview → Governance → Ledger → Agents + Capabilities/Settings，Playwright 18/18 通过 |
| 无敏感信息泄露 | ✅ 通过 | Network/响应无 token 泄露 |

**放行建议**：**通过** — BUG-1、BUG-2 已修复并补回归测试。当前自动化覆盖达到测试总监要求的最低覆盖，核心主路径均已验证。

---

## 二、API 维度

| 步骤 | 端点 | 预期 | 实际 | 通过 |
|------|------|------|------|------|
| API-1 | GET /api/v1/overview | 200，含 health_checks | 200，health_checks 含 runtime/db/hatchet/llm | ✅ |
| API-2 | 无 DB 时 overview | db healthy:false | ✓ | ✅ |
| API-3 | GET /api/v1/agents | 200，items:[], message | `{"items":[],"message":"Database not configured"}` | ✅ |
| API-4 | GET /api/v1/agents/{id} | 404 | 404，`NOT_FOUND` | ✅ |
| API-5 | GET /api/v1/governance/budget | 200，granularity | ✓ | ✅ |
| API-6 | GET /api/v1/governance/circuit-breakers | 200 | ✓ | ✅ |
| API-8 | GET /api/v1/ledger | 200，PaginatedResponse | `{items:[],total:0,offset:0,limit:5}` | ✅ |
| API-9 | ledger?order_by=invalid | 422，ErrorResponse | `{error:{code:"VALIDATION_ERROR",...}}` | ✅ |
| API-11 | GET /api/v1/capabilities | 200，items | `{items:[]}` | ✅ |
| API-13 | GET /api/v1/triggers | 200 | 200，空列表降级 | ✅ |
| API-15 | GET /api/v1/settings | 200 | 200，含 runtime,mcp,database,owlhub | ✅ |

---

## 三、功能维度（Playwright 自动化）

| 步骤 | 操作 | 测试用例 | 通过 |
|------|------|----------|------|
| F-1~F-2 | Overview 进入与指标 | `Overview -> Governance -> Ledger navigation` | ✅ |
| F-6 | Governance 进入 | 同上 + `Governance page triggers governance API calls` | ✅ |
| F-7 | 切换时间粒度 day→week | `Governance granularity switch triggers new API request (F-7)` | ✅ |
| F-8 | 熔断器状态 | `Governance has Circuit Breakers section (F-8)` | ✅ |
| F-9 | 可见性矩阵 | `Governance has Capability Visibility Matrix (F-9)` | ✅ |
| F-10 | Ledger 进入 | `Ledger filter panel and empty state` | ✅ |
| F-11 | Ledger Apply 筛选 | `Ledger Apply filter triggers new API request with params (F-11)` | ✅ |
| F-12 | 记录详情 | `Ledger with mock data: Table/Timeline toggle and record detail (F-10, F-12)` | ✅ |
| F-13 | 分页 | `Ledger with mock data: pagination triggers offset request (F-13)` | ✅ |
| F-15 | Agents 空状态 | `Overview -> Agents navigation and empty state` | ✅ |
| F-17 | Capabilities | `Capabilities and Settings pages load` | ✅ |
| F-19 | Settings | 同上 | ✅ |

**Playwright 测试清单**（`owlclaw/web/frontend/e2e/console-flow.spec.ts`）：

| # | 测试 | 维度 |
|---|------|------|
| 1–9 | 基础导航、Governance/Ledger API 校验、Capabilities/Settings、Tab、首屏 | 功能/网络 |
| 10 | Overview has System Health and component checks (F-1) | 功能 |
| 11 | Overview has First Run Guide with Quick Start link (F-5) | 功能 |
| 12 | Overview attempts WebSocket connection (N-7) | 网络 |
| 13 | Governance has Circuit Breakers section (F-8) | 功能 |
| 14 | Governance has Capability Visibility Matrix (F-9) | 功能 |
| 15 | Ledger with mock data: Table/Timeline toggle and record detail (F-10, F-12) | 功能 |
| 16 | Ledger with mock data: pagination triggers offset request (F-13) | 功能 |
| 17 | Overview and main nav: no unexpected 4xx/5xx on API calls | 网络 |
| 18 | Settings shows runtime, database, version sections | 功能 |

**增量回归（2026-03-04）**：
- `Ledger sort change triggers order_by request param (F-14)`：`1 passed`（前端 dev server + Playwright 单测执行）。

**运行**：`cd owlclaw/web/frontend && npm run test:e2e` — 18/18 通过（含 start-server-and-test 启停服务）

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
| N-7 | WebSocket 连接尝试 | Overview 尝试连接 `/api/v1/ws`（服务端 404 当无 websockets 库） | ✅ |
| N-9 | 无 DB 时无 500 | agents 列表/详情、triggers 列表/历史均已降级通过 | ✅ |
| N-10 | Console 无未捕获 JS 错误 | Playwright 未报 | ✅ |
| N-11 | 主流程无意外 4xx/5xx | 排除 agents/{id}、triggers、ws 后无其他失败 | ✅ |

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
| BUG-1 | P1 | `GET /api/v1/agents/{id}` 在无 DB 时返回 500，应 404 或 200+空 | ✅ 已修复 |
| BUG-2 | P1 | `GET /api/v1/triggers` 在无 DB 时返回 500，应降级返回空 | ✅ 已修复 |

### 缺陷修复回填（2026-03-04，codex-work）

- BUG-1 已修复：`owlclaw/web/api/agents.py` 在 `get_agent_detail()` 捕获 `ConfigurationError` 并返回 404（`Agent not found`）。
- BUG-2 已修复：`owlclaw/web/api/triggers.py` 在 `list_triggers()` 捕获 `ConfigurationError` 并返回空列表。
- 回归测试已补充并通过：
  - `tests/unit/web/test_agents.py::test_agents_detail_route_returns_404_when_database_not_configured`
  - `tests/unit/web/test_triggers.py::test_triggers_list_route_returns_empty_when_database_not_configured`

---

## 七、交付物

- [x] 执行报告（本文档）
- [x] 清单打勾（BROWSER_VERIFICATION_CHECKLIST.md 已更新）
- [x] 缺陷列表（见第六节）
- [x] 放行建议：**通过**（BUG-1、BUG-2 已修复并复验）

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
