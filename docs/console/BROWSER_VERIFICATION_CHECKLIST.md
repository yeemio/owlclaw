# OwlClaw Console 多维度浏览器验证清单

> **要求来源**：`docs/console/BROWSER_TEST_REQUIREMENTS.md`（测试总监签发）  
> **维度**：功能 · API · 代码/网络 · 效果  
> **Spec 真源**：`console-frontend/requirements.md`、`console-backend-api/design.md`  
> **启动**：`owlclaw start --port 8000` → http://localhost:8000/console/

### E2E 自动化测试运行

```bash
cd owlclaw/web/frontend && npm run test:e2e
```

单命令完成：启动服务 → 等待健康检查 → 运行 Playwright → 结束后关闭服务（`start-server-and-test`）。

手动模式（服务已启动时）：`npm run test:e2e:manual`

---

## 维度说明

| 维度 | 验证内容 | 执行方式 |
|------|----------|----------|
| **功能** | 业务能力、交互逻辑、数据展示 | 浏览器操作 + 目视检查 |
| **API** | 端点契约、参数、响应、错误处理 | 直接 curl 或 DevTools Network |
| **代码/网络** | 请求链、WS 连接、资源加载、错误请求 | DevTools Network + Console |
| **效果** | 视觉、空状态、性能、可访问性 | 目视 + 计时 + Tab 导航 |

---

# 一、API 维度（契约与响应）

## 1.1 Overview

| 步骤 | 端点 | 方法 | 预期响应结构 | 通过 |
|------|------|------|--------------|------|
| API-1 | `/api/v1/overview` | GET | `{total_cost_today, total_executions_today, success_rate_today, active_agents, health_checks[]}`，`health_checks` 含 `component`, `healthy`, `latency_ms?`, `message?` | ☑ |
| API-2 | 无 DB 时 | GET | 仍 200，`health_checks` 中 db 为 `healthy: false`，`message` 含降级说明 | ☑ |

## 1.2 Agents

| 步骤 | 端点 | 方法 | 预期 | 通过 |
|------|------|------|------|------|
| API-3 | `/api/v1/agents` | GET | 无 DB：`{"items":[],"message":"Database not configured"}`，HTTP 200 | ☑ |
| API-4 | `/api/v1/agents/{id}` | GET | 无记录：404，`detail` 或 `error.code` | ☑ |

## 1.3 Governance

| 步骤 | 端点 | 方法 | Query 参数 | 预期 | 通过 |
|------|------|------|------------|------|------|
| API-5 | `/api/v1/governance/budget` | GET | `start_date`, `end_date`, `granularity`(day/week/month) | `{start_date, end_date, granularity, items[]}` | ☑ |
| API-6 | `/api/v1/governance/circuit-breakers` | GET | - | `{items[]}` | ☑ |
| API-7 | `/api/v1/governance/visibility-matrix` | GET | `agent_id?` | 返回 visibility 结构 | ☑ |

## 1.4 Ledger

| 步骤 | 端点 | 方法 | Query 参数 | 预期 | 通过 |
|------|------|------|------------|------|------|
| API-8 | `/api/v1/ledger` | GET | `agent_id`, `capability_name`, `status`, `start_date`, `end_date`, `min_cost`, `max_cost`, `limit`, `offset`, `order_by` | `PaginatedResponse`: `{items, total, offset, limit}`，`order_by` 支持 `created_at_desc|created_at_asc|cost_desc|cost_asc` | ☑ |
| API-9 | 无效 `order_by` | GET | `order_by=invalid` | 422，`ErrorResponse` 格式：`{error: {code, message, details}}` | ☑ |
| API-10 | `/api/v1/ledger/{record_id}` | GET | - | 无记录：404 | ☑ |

## 1.5 Capabilities / Triggers / Settings

| 步骤 | 端点 | 预期 | 通过 |
|------|------|------|------|
| API-11 | `/api/v1/capabilities` | `?category` 可选，返回 capabilities 列表 | ☑ |
| API-12 | `/api/v1/capabilities/{name}/schema` | 404 当不存在 | ☑ |
| API-13 | `/api/v1/triggers` | 返回 triggers 列表 | ☑ |
| API-14 | `/api/v1/triggers/{id}/history` | `limit`, `offset`，返回历史 + 分页 | ☑ |
| API-15 | `/api/v1/settings` | 返回配置树/系统信息 | ☑ |

## 1.6 认证与错误

| 步骤 | 场景 | 预期 | 通过 |
|------|------|------|------|
| API-16 | `OWLCLAW_CONSOLE_TOKEN` 设置时，无 Authorization | 401，`{error: {code: "UNAUTHORIZED", message}}` | ☑ |
| API-17 | 任意 4xx/5xx | 统一 `ErrorResponse` 结构，非裸文本 | ☑ |

---

# 二、功能维度（业务与交互）

## 2.1 Overview

| 步骤 | 操作 | 预期（功能） | 通过 |
|------|------|--------------|------|
| F-1 | 进入 Overview | 健康指示灯（Runtime/DB/Hatchet/LLM/Langfuse），每项有绿/黄/红或等价状态 | ☑ |
| F-2 | 检查指标卡片 | 今日成本、执行次数、成功率、活跃 Agent 有数值或 0，非空白 | ☑ |
| F-3 | 检查告警 | 成本超阈值或成功率低时出现告警横幅；否则无或隐藏 | ☐ |
| F-4 | 等待 30s+ | 数据自动刷新（Network 有新请求或 WS 推送） | ☐ |
| F-5 | 检查引导 | "Getting Started" 或类似引导卡片，含 Quick Start / 示例 / SKILL 指南 链接 | ☐ |

## 2.2 Governance

| 步骤 | 操作 | 预期（功能） | 通过 |
|------|------|--------------|------|
| F-6 | 进入 Governance | 预算消耗趋势图，或有空状态说明 | ☑ |
| F-7 | 切换时间粒度 | 日/周/月切换，对应新 API 请求 `granularity=day|week|month` | ☑ |
| F-8 | 检查限流/熔断 | 状态卡片显示 open/closed/half-open 或等价 | ☑ |
| F-9 | 检查能力可见性矩阵 | Agent × Capability 热力图或表格 | ☑ |

## 2.3 Ledger

| 步骤 | 操作 | 预期（功能） | 通过 |
|------|------|--------------|------|
| F-10 | 进入 Ledger | 时间线/表格视图可切换 | ☑ |
| F-11 | 使用筛选 | Agent/Capability/时间/状态 筛选，触发新请求且参数正确 | ☑ |
| F-12 | 点击某条记录 | 详情展开：输入/输出/成本/模型/延迟/决策推理 | ☑ |
| F-13 | 分页 | 有分页控件，切换触发 `limit`/`offset` 请求 | ☑ |
| F-14 | 排序切换 | `order_by` 参数随切换变化 | ☐ |

## 2.4 Agents

| 步骤 | 操作 | 预期（功能） | 通过 |
|------|------|--------------|------|
| F-15 | 进入 Agents | Agent 卡片列表或空状态（无 DB 时为友好提示，非 500 白屏） | ☑ |
| F-16 | 点击某 Agent | 详情面板：身份配置、记忆浏览、知识库、运行历史 | ☐ |

## 2.5 Capabilities / Triggers / Settings / Traces

| 步骤 | 操作 | 预期（功能） | 通过 |
|------|------|--------------|------|
| F-17 | Capabilities 标签页 | Handlers / Skills / Bindings 分类，Schema 查看器（JSON 高亮） | ☑ |
| F-18 | Triggers | 6 类触发器统一列表，执行历史表，下次触发倒计时 | ☐ |
| F-19 | Settings | 配置树、MCP 连接、DB 状态、版本信息、OwlHub 状态、文档链接 | ☑ |
| F-20 | Traces/Workflows | Langfuse / Hatchet 深链接或 iframe，连接状态指示 | ☐ |

---

# 三、代码/网络维度（请求链与实现）

## 3.1 请求链

| 步骤 | 检查项 | 预期 | 通过 |
|------|--------|------|------|
| N-1 | 打开 Overview | Network 有 `GET /api/v1/overview`，200 | ☑ |
| N-2 | 进入 Governance | 有 `/governance/budget`、`/governance/circuit-breakers`、`/governance/visibility-matrix` 中至少一个 | ☑ |
| N-3 | 进入 Ledger | 有 `GET /api/v1/ledger`，带 `limit`、`offset` | ☑ |
| N-4 | 改 Ledger 筛选 | 新请求带 `agent_id`/`capability_name`/`status` 等 | ☑ |
| N-5 | 进入 Agents | 有 `GET /api/v1/agents` | ☑ |
| N-6 | 静态资源 | 无 404，`/console/assets/*` 均 200 | ☑ |

## 3.2 WebSocket（如已实现）

| 步骤 | 检查项 | 预期 | 通过 |
|------|--------|------|------|
| N-7 | WS 连接 | 有 `ws://.../api/v1/ws`，状态 Connected | ☑ (尝试连接，服务端 404 当无 websockets 库) |
| N-8 | 消息类型 | 收到 `overview` / `triggers` / `ledger` 之一 | ☐ (需 uvicorn[standard] 启用 WS) |

## 3.3 错误与降级

| 步骤 | 检查项 | 预期 | 通过 |
|------|--------|------|------|
| N-9 | 无 DB 时各页 | 无 500，API 返回降级数据或 `message` | ☑ |
| N-10 | Console 面板 | 无未捕获 JS 错误 | ☑ |

---

# 四、效果维度（视觉与体验）

## 4.1 主题与布局

| 步骤 | 检查项 | 预期 | 通过 |
|------|--------|------|------|
| E-1 | 暗色主题 | 所有页面暗色一致，无白底闪屏 | ☑ |
| E-2 | 响应式 | 最小宽度 1024px 下布局正常，侧栏 + 内容区 | ☐ |
| E-3 | 页面切换 | 无全量刷新，URL 或路由变化 | ☐ |

## 4.2 空状态与错误展示

| 步骤 | 检查项 | 预期 | 通过 |
|------|--------|------|------|
| E-4 | Agents 无 DB | 友好文案（如 "Database not configured"），非 raw 500 | ☑ |
| E-5 | Ledger 无数据 | 空表格或 "暂无记录" 说明 | ☑ |
| E-6 | Governance 无数据 | 图表空或提示 | ☐ |

## 4.3 性能与可访问性

| 步骤 | 检查项 | 预期 | 通过 |
|------|--------|------|------|
| E-7 | 首屏加载 | 从导航到内容可交互 < 5s（E2E 断言） | ☑ |
| E-8 | Tab 键 | 可遍历侧栏与主要交互元素 | ☑ |
| E-9 | 对比度 | 文本与背景对比度满足 WCAG AA（目视或工具） | ☐ |

---

# 五、执行与报告

## curl 快速校验（API 维度）

```bash
# 无 DB 场景
curl -s http://localhost:8000/api/v1/agents
# 预期: {"items":[],"message":"Database not configured"}

curl -s http://localhost:8000/api/v1/overview
# 预期: JSON 含 total_cost_today, health_checks 等

curl -s "http://localhost:8000/api/v1/ledger?order_by=invalid"
# 预期: 422, {"error": {...}}

curl -s http://localhost:8000/api/v1/governance/budget
# 预期: {start_date, end_date, granularity, items}
```

## 报告产出

执行后更新 `.kiro/reviews/YYYY-MM-DD-console-browser-verification.md`，按维度汇总：

- API：每步 通过/失败 + 实际响应摘要
- 功能：每步 通过/失败 + 截图或现象描述
- 网络：请求列表 + 异常
- 效果：计时、空状态、可访问性结论
