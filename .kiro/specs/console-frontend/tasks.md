# Tasks: Console Frontend

> **Spec**: console-frontend  
> **Design**: `design.md`  
> **最后更新**: 2026-02-28

---

## Task 0：工程脚手架

**目标**：初始化前端工程

**文件**：
- `owlclaw/web/frontend/` — 完整前端工程目录

**实现**：
- [x] 0.1 初始化 Vite + React + TypeScript 项目（`owlclaw/web/frontend/`）
- [x] 0.2 配置 Tailwind CSS + 暗色主题
- [x] 0.3 安装并配置 Shadcn/ui 组件库
- [x] 0.4 配置 Vite 构建输出到 `owlclaw/web/static/`
- [x] 0.5 配置开发代理（`/api` → `http://localhost:8000`）
- [x] 0.6 配置 TypeScript 类型生成脚本（从 OpenAPI Schema）

**验收**：
- `pnpm dev` 启动开发服务器
- `pnpm build` 产出静态文件到 `owlclaw/web/static/`
- 暗色主题生效

---

## Task 1：布局系统 + 路由

**目标**：侧边栏导航 + 内容区 + 路由

**文件**：
- `src/App.tsx`
- `src/components/layout/Sidebar.tsx`
- `src/components/layout/Header.tsx`
- `src/components/layout/Layout.tsx`

**实现**：
- [x] 1.1 实现 Layout 组件（Sidebar + Header + Content Area）
- [x] 1.2 实现 Sidebar 导航（9 个页面入口 + 分组分隔线）
- [x] 1.3 配置 React Router 路由
- [x] 1.4 实现 API Client（fetch wrapper + Token 认证）
- [x] 1.5 配置 TanStack Query Provider

**验收**：
- 侧边栏导航可切换页面
- 页面切换无全量刷新
- 暗色主题布局一致

---

## Task 2：Overview 页面

**目标**：系统全局概览

**文件**：
- `src/pages/Overview.tsx`
- `src/components/charts/MetricCard.tsx`
- `src/components/data/HealthIndicator.tsx`

**实现**：
- [ ] 2.1 实现健康指示灯组件（绿/黄/红，对应 healthy/degraded/unhealthy）
- [ ] 2.2 实现指标卡片组件（成本/执行/成功率/Agent，带趋势箭头）
- [ ] 2.3 实现告警横幅组件
- [ ] 2.4 实现首次使用引导卡片（链接 Quick Start/示例/SKILL.md 指南）
- [ ] 2.5 接入 `useOverview()` hook，30s 自动刷新
- [ ] 2.6 接入 WebSocket 实时更新

**验收**：
- Overview 页面数据从 API 正确获取
- 健康状态实时反映
- 自动刷新和 WebSocket 更新生效

---

## Task 3：Governance 页面

**目标**：治理数据可视化

**文件**：
- `src/pages/Governance.tsx`
- `src/components/charts/BudgetTrend.tsx`
- `src/components/data/CircuitBreakerCard.tsx`
- `src/components/data/VisibilityMatrix.tsx`

**实现**：
- [ ] 3.1 实现预算消耗趋势图（Recharts 折线图，支持天/周/月粒度切换）
- [ ] 3.2 实现限流/熔断状态卡片（open/closed/half-open 视觉区分）
- [ ] 3.3 实现能力可见性矩阵（Agent × Capability 热力图）
- [ ] 3.4 实现 migration_weight 进度条
- [ ] 3.5 实现 Skills 质量排行列表

**验收**：
- 趋势图数据正确，粒度切换流畅
- 熔断状态实时反映
- 可见性矩阵正确展示 Agent-Capability 关系

---

## Task 4：Ledger 页面

**目标**：执行审计时间线

**文件**：
- `src/pages/Ledger.tsx`
- `src/components/data/LedgerTimeline.tsx`
- `src/components/data/LedgerFilters.tsx`
- `src/components/data/LedgerDetail.tsx`

**实现**：
- [ ] 4.1 实现多维筛选面板（Agent/Capability/时间范围/成本范围/状态）
- [ ] 4.2 实现表格视图（DataTable + 分页）
- [ ] 4.3 实现详情展开面板（输入/输出/成本/模型/延迟/决策推理）
- [ ] 4.4 实现时间线视图（可选）

**验收**：
- 筛选参数正确传递到 API
- 分页导航正常
- 详情展开显示完整执行信息

---

## Task 5：Agents 页面

**目标**：Agent 列表和详情

**文件**：
- `src/pages/Agents.tsx`
- `src/pages/AgentDetail.tsx`

**实现**：
- [ ] 5.1 实现 Agent 卡片列表（身份摘要 + 状态指示灯）
- [ ] 5.2 实现 Agent 详情页（身份配置 + 记忆统计 + 知识库 + 运行历史）

**验收**：
- Agent 列表正确展示
- 详情页运行历史从 Ledger 聚合

---

## Task 6：Capabilities 页面

**目标**：能力注册可视化

**文件**：
- `src/pages/Capabilities.tsx`
- `src/components/data/SchemaViewer.tsx`

**实现**：
- [ ] 6.1 实现 Handlers/Skills/Bindings 分类标签页
- [ ] 6.2 实现 JSON Schema 查看器（语法高亮）
- [ ] 6.3 实现调用统计图（执行次数/成功率/平均延迟）
- [ ] 6.4 实现扫描结果标签页（cli-scan 产物）
- [ ] 6.5 实现迁移进度标签页（cli-migrate 产物）

**验收**：
- 三类能力正确分类展示
- Schema 查看器可读性好
- 统计图数据正确

---

## Task 7：Triggers + Settings + External 页面

**目标**：触发器、配置、外部链接页面

**文件**：
- `src/pages/Triggers.tsx`
- `src/pages/Settings.tsx`
- `src/pages/ExternalDashboard.tsx`

**实现**：
- [ ] 7.1 实现 Triggers 页面（6 类统一列表 + 执行历史 + 下次触发倒计时）
- [ ] 7.2 实现 Settings 页面（配置树 + MCP 状态 + DB 状态 + 版本信息 + 文档链接）
- [ ] 7.3 实现 Traces/Workflows 页面（Langfuse/Hatchet 深链接 + 连接状态）

**验收**：
- 触发器列表包含所有 6 类
- Settings 敏感字段已脱敏
- 外部链接正确跳转

---

## Task 8：WebSocket + 空状态 + 构建优化

**目标**：实时更新、边界状态、性能优化

**文件**：
- `src/hooks/useWebSocket.ts`
- `src/components/data/EmptyState.tsx`

**实现**：
- [ ] 8.1 实现 WebSocket 连接管理（自动重连 + 认证）
- [ ] 8.2 实现 Overview/Ledger/Triggers 实时更新
- [ ] 8.3 实现空状态组件（图标 + 说明 + 引导操作）
- [ ] 8.4 实现错误边界（全局 ErrorBoundary + Toast）
- [ ] 8.5 构建优化（路由级代码分割 + 图表按需加载）
- [ ] 8.6 验证 gzip 后 bundle < 500KB

**验收**：
- WebSocket 实时更新生效
- 空状态和错误状态有良好的用户体验
- `pnpm build` 产出 gzip 后 < 500KB

---

## Task 9：测试

**目标**：组件测试和 E2E 测试

**文件**：
- `src/__tests__/` — 组件测试
- `e2e/` — Playwright E2E 测试

**实现**：
- [ ] 9.1 核心组件单元测试（DataTable、Filters、MetricCard、HealthIndicator）
- [ ] 9.2 页面组件测试（mock API，验证数据渲染）
- [ ] 9.3 E2E 测试：Overview → Governance → Ledger 筛选流程

**验收**：
- 组件测试覆盖核心交互
- E2E 测试覆盖关键用户流程
- `pnpm test` 通过

---

**维护者**：yeemio  
**最后更新**：2026-02-28
