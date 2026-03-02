# Requirements: Console Frontend

> **目标**：为 OwlClaw Web Console 提供专业的 React SPA 前端，作为治理控制面的展示层  
> **优先级**：P0  
> **预估工作量**：10-15 天

---

## 1. 背景与动机

### 1.1 当前问题

OwlClaw 缺少统一的可视化界面。运维人员需要在 CLI、Langfuse Dashboard、Hatchet UI 之间切换，无法一眼掌握系统全局状态。作为企业级产品，缺少专业的 Web Console 严重影响产品第一印象和客户评估体验。

### 1.2 设计目标

构建一个专业的 React SPA，消费 Console Backend API，提供 9 个核心页面。暗色主题为默认，治理数据为核心叙事，深链接到 Langfuse/Hatchet 而非重造。

---

## 2. 用户故事

### 2.1 作为运维人员

**故事 1**：系统全局概览
```
作为运维人员
我希望打开 Console 首页就能看到系统健康状态和关键指标
这样我可以在 10 秒内判断系统是否正常
```

**验收标准**：
- [ ] Overview 页面显示健康指示灯（绿/黄/红）
- [ ] 关键指标卡片（今日成本/执行次数/成功率/活跃 Agent）
- [ ] 告警横幅（成本超阈值、成功率低于阈值）
- [ ] 自动刷新（30s 间隔）

**故事 2**：治理监控
```
作为运维人员
我希望在 Governance 页面看到预算消耗趋势和熔断状态
这样我可以及时发现治理异常
```

**验收标准**：
- [ ] 预算消耗趋势图（按天/周/月切换）
- [ ] 限流/熔断状态卡片（open/closed/half-open）
- [ ] 能力可见性矩阵（Agent × Capability 热力图）

**故事 3**：执行审计
```
作为运维人员
我希望在 Ledger 页面按多维度筛选执行记录
这样我可以追溯任意一次 Agent 决策
```

**验收标准**：
- [ ] 时间线视图 + 表格视图切换
- [ ] 多维筛选面板（Agent/Capability/时间/成本/状态）
- [ ] 详情展开（输入/输出/成本/模型/延迟/决策推理）

### 2.2 作为开发者

**故事 4**：首次使用引导
```
作为首次使用 OwlClaw 的开发者
我希望 Console 首页有引导卡片链接到 Quick Start 和示例
这样我可以快速上手
```

**验收标准**：
- [ ] Overview 页面包含"Getting Started"引导卡片
- [ ] 链接到 Quick Start、完整示例、SKILL.md 编写指南

---

## 3. 功能需求

### 3.1 工程基础

#### FR-1：前端工程脚手架

**需求**：Vite + React + TypeScript + Tailwind + Shadcn/ui 工程搭建。

**验收标准**：
- [ ] `pnpm dev` 可启动开发服务器
- [ ] `pnpm build` 产出静态文件到 `owlclaw/web/static/`
- [ ] TypeScript 类型从 OpenAPI Schema 自动生成
- [ ] 暗色主题为默认

#### FR-2：路由与布局

**需求**：侧边栏导航 + 内容区布局。

**验收标准**：
- [ ] 侧边栏包含 9 个页面入口
- [ ] 响应式布局（最小宽度 1024px）
- [ ] 页面切换无全量刷新

### 3.2 核心页面

#### FR-3：Overview 页面

**需求**：系统全局概览。

**验收标准**：
- [ ] 健康指示灯（Runtime/DB/Hatchet/LLM/Langfuse）
- [ ] 指标卡片（成本/执行/成功率/Agent）
- [ ] 告警横幅
- [ ] 自动刷新（30s）
- [ ] 首次使用引导卡片

#### FR-4：Governance 页面

**需求**：治理数据可视化。

**验收标准**：
- [ ] 预算消耗趋势图（折线图，支持时间粒度切换）
- [ ] 限流/熔断状态卡片
- [ ] 能力可见性矩阵
- [ ] migration_weight 进度条
- [ ] Skills 质量排行

#### FR-5：Ledger 页面

**需求**：执行审计时间线。

**验收标准**：
- [ ] 时间线/表格视图切换
- [ ] 多维筛选面板
- [ ] 详情展开面板
- [ ] 分页导航

#### FR-6：Agents 页面

**需求**：Agent 列表和详情。

**验收标准**：
- [ ] Agent 卡片列表（身份摘要 + 状态指示）
- [ ] 详情面板（身份配置 + 记忆浏览 + 知识库 + 运行历史）

#### FR-7：Capabilities 页面

**需求**：能力注册可视化。

**验收标准**：
- [ ] Handlers/Skills/Bindings 分类标签页
- [ ] Schema 查看器（JSON 高亮）
- [ ] 调用统计图
- [ ] 扫描结果标签页（cli-scan 产物）
- [ ] 迁移进度标签页（cli-migrate 产物）

#### FR-8：Triggers 页面

**需求**：触发器统一视图。

**验收标准**：
- [ ] 6 类触发器统一列表
- [ ] 执行历史表格
- [ ] 下次触发倒计时

#### FR-9：Settings 页面

**需求**：配置与诊断。

**验收标准**：
- [ ] 配置树形展示
- [ ] MCP 连接列表
- [ ] DB 状态
- [ ] 版本与供应链信息
- [ ] OwlHub 状态
- [ ] 开发者文档链接区域

#### FR-10：Traces/Workflows 页面

**需求**：外部 Dashboard 深链接。

**验收标准**：
- [ ] Langfuse Dashboard 深链接（或 iframe）
- [ ] Hatchet Dashboard 深链接（或 iframe）
- [ ] 连接状态指示

---

## 4. 非功能需求

### 4.1 性能

**NFR-1：首屏加载**
- 首屏加载时间 < 3s（gzip 后 bundle < 500KB）

**验收标准**：
- [ ] `pnpm build` 产出 gzip 后 < 500KB

### 4.2 可访问性

**NFR-2：键盘导航**
- 核心操作支持键盘导航

**验收标准**：
- [ ] Tab 键可遍历侧边栏和主要交互元素

### 4.3 主题

**NFR-3：暗色主题**
- 暗色主题为默认，企业运维场景专业且护眼

**验收标准**：
- [ ] 所有页面暗色主题一致
- [ ] 对比度满足 WCAG AA 标准

---

## 5. 验收标准总览

### 5.1 功能验收
- [ ] **FR-1**：工程脚手架可构建
- [ ] **FR-2**：路由和布局正常
- [ ] **FR-3~FR-10**：8 个页面均可访问且数据正确

### 5.2 非功能验收
- [ ] **NFR-1**：首屏 < 3s
- [ ] **NFR-2**：键盘导航可用
- [ ] **NFR-3**：暗色主题一致

### 5.3 测试验收
- [ ] 组件单元测试覆盖核心交互
- [ ] E2E 测试覆盖关键用户流程

---

## 6. 约束与假设

### 6.1 约束
- 前端代码位于 `owlclaw/web/frontend/`（开发时）
- 构建产物输出到 `owlclaw/web/static/`（打包时）
- 用户无需安装 Node.js（静态文件内嵌 Python 包）
- MVP 只读，无写入操作

### 6.2 假设
- Console Backend API（console-backend-api spec）已实现
- OpenAPI Schema 可从 `/api/v1/openapi.json` 获取

---

## 7. 依赖

### 7.1 外部依赖
- React 19+
- Vite 6+
- Tailwind CSS 4+
- Shadcn/ui
- Recharts（图表）
- TanStack Query（数据获取）

### 7.2 内部依赖
- console-backend-api — REST API 数据源
- console-integration — 构建流程和部署

---

## 8. 风险与缓解

### 8.1 风险：API 接口变更

**影响**：后端 API 变更导致前端类型不匹配

**缓解**：
- TypeScript 类型从 OpenAPI Schema 自动生成
- CI 中加入类型生成 + 类型检查步骤

### 8.2 风险：Bundle 体积过大

**影响**：首屏加载慢

**缓解**：
- 路由级代码分割（React.lazy）
- 图表库按需加载
- Tree-shaking 优化

---

## 9. Definition of Done

### 9.1 工程基础
- [ ] `pnpm dev` 启动开发服务器
- [ ] `pnpm build` 产出静态文件 < 500KB (gzip)
- [ ] TypeScript 类型从 OpenAPI 自动生成

### 9.2 页面完整性
- [ ] 9 个页面均可访问
- [ ] 数据从 Backend API 正确获取和展示
- [ ] 暗色主题一致

### 9.3 验收矩阵

| 页面 | 数据展示 | 交互 | 响应式 | 暗色主题 | 测试 |
|------|---------|------|--------|---------|------|
| Overview | [ ] | [ ] | [ ] | [ ] | [ ] |
| Governance | [ ] | [ ] | [ ] | [ ] | [ ] |
| Ledger | [ ] | [ ] | [ ] | [ ] | [ ] |
| Agents | [ ] | [ ] | [ ] | [ ] | [ ] |
| Capabilities | [ ] | [ ] | [ ] | [ ] | [ ] |
| Triggers | [ ] | [ ] | [ ] | [ ] | [ ] |
| Settings | [ ] | [ ] | [ ] | [ ] | [ ] |
| Traces/Workflows | [ ] | [ ] | [ ] | [ ] | [ ] |

---

## 10. 参考文档

- `docs/ARCHITECTURE_ANALYSIS.md` §4.15 — Web Console 设计原则
- `.kiro/specs/console-backend-api/` — Backend API spec
- `.kiro/specs/console-integration/` — 集成与部署 spec

---

**维护者**：yeemio  
**最后更新**：2026-02-28
