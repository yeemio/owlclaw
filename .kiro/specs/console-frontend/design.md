# Design: Console Frontend

> **目标**：实现专业的 React SPA 前端，暗色主题，治理控制面为核心叙事  
> **状态**：设计完成  
> **最后更新**：2026-02-28

---

## 1. 架构设计

### 1.1 整体架构

```
owlclaw/web/frontend/          (开发时源码)
├── src/
│   ├── main.tsx               # 入口
│   ├── App.tsx                # 路由 + 布局
│   ├── api/                   # API Client (auto-generated types)
│   │   ├── client.ts          # fetch wrapper + auth
│   │   └── types.ts           # from OpenAPI Schema
│   ├── components/            # 通用组件
│   │   ├── ui/                # Shadcn/ui 组件
│   │   ├── layout/            # Sidebar + Header + Content
│   │   ├── charts/            # Recharts 封装
│   │   └── data/              # DataTable + Pagination + Filters
│   ├── pages/                 # 页面组件
│   │   ├── Overview.tsx
│   │   ├── Governance.tsx
│   │   ├── Ledger.tsx
│   │   ├── Agents.tsx
│   │   ├── Capabilities.tsx
│   │   ├── Triggers.tsx
│   │   ├── Settings.tsx
│   │   └── ExternalDashboard.tsx  # Traces + Workflows
│   ├── hooks/                 # 自定义 hooks
│   │   ├── useApi.ts          # TanStack Query wrappers
│   │   └── useWebSocket.ts    # WebSocket 连接管理
│   └── lib/                   # 工具函数
│       ├── format.ts          # 数字/日期/成本格式化
│       └── theme.ts           # 主题配置
├── index.html
├── vite.config.ts
├── tailwind.config.ts
├── tsconfig.json
└── package.json

owlclaw/web/static/            (构建产物，内嵌 Python 包)
├── index.html
├── assets/
│   ├── index-[hash].js
│   └── index-[hash].css
```

### 1.2 核心组件

#### 组件 1：API Client (`src/api/`)

**职责**：封装 HTTP 请求，自动附加认证 Token，类型安全。

```typescript
// src/api/client.ts
const API_BASE = '/api/v1';

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem('owlclaw_token');
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const err = await res.json();
    throw new ApiError(err.error.code, err.error.message);
  }
  return res.json();
}
```

#### 组件 2：布局系统 (`src/components/layout/`)

**职责**：侧边栏导航 + 顶部状态栏 + 内容区。

```
┌──────────────────────────────────────────────────┐
│  OwlClaw Console                    [status bar] │
├────────────┬─────────────────────────────────────┤
│            │                                      │
│  Overview  │                                      │
│  Agents    │         Content Area                 │
│  Governance│                                      │
│  Capabilit.│                                      │
│  Triggers  │                                      │
│  Ledger    │                                      │
│  ─────────│                                      │
│  Traces    │                                      │
│  Workflows │                                      │
│  ─────────│                                      │
│  Settings  │                                      │
│            │                                      │
└────────────┴─────────────────────────────────────┘
```

#### 组件 3：数据表格 (`src/components/data/`)

**职责**：通用数据表格，支持分页、筛选、排序、详情展开。

#### 组件 4：图表组件 (`src/components/charts/`)

**职责**：Recharts 封装，统一暗色主题配色。

---

## 2. 实现细节

### 2.1 路由定义

```typescript
// src/App.tsx
const routes = [
  { path: '/', element: <Overview /> },
  { path: '/agents', element: <Agents /> },
  { path: '/agents/:id', element: <AgentDetail /> },
  { path: '/governance', element: <Governance /> },
  { path: '/capabilities', element: <Capabilities /> },
  { path: '/triggers', element: <Triggers /> },
  { path: '/ledger', element: <Ledger /> },
  { path: '/ledger/:id', element: <LedgerDetail /> },
  { path: '/traces', element: <ExternalDashboard type="langfuse" /> },
  { path: '/workflows', element: <ExternalDashboard type="hatchet" /> },
  { path: '/settings', element: <Settings /> },
];
```

### 2.2 数据获取策略

使用 TanStack Query 管理服务端状态：

```typescript
// src/hooks/useApi.ts
import { useQuery } from '@tanstack/react-query';

export function useOverview() {
  return useQuery({
    queryKey: ['overview'],
    queryFn: () => apiFetch<OverviewMetrics>('/overview'),
    refetchInterval: 30_000,
  });
}

export function useLedger(filters: LedgerFilters) {
  return useQuery({
    queryKey: ['ledger', filters],
    queryFn: () => apiFetch<PaginatedResponse<LedgerRecord>>('/ledger', {
      params: filters,
    }),
  });
}
```

### 2.3 WebSocket 实时更新

```typescript
// src/hooks/useWebSocket.ts
export function useConsoleWebSocket() {
  const queryClient = useQueryClient();

  useEffect(() => {
    const ws = new WebSocket(`ws://${location.host}/api/v1/ws`);
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      switch (msg.type) {
        case 'overview_update':
          queryClient.setQueryData(['overview'], msg.data);
          break;
        case 'ledger_new':
          queryClient.invalidateQueries({ queryKey: ['ledger'] });
          break;
      }
    };
    return () => ws.close();
  }, [queryClient]);
}
```

### 2.4 暗色主题

Tailwind CSS 暗色主题配置，Shadcn/ui 组件自动适配：

```typescript
// tailwind.config.ts
export default {
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: 'hsl(222.2 84% 4.9%)',
        foreground: 'hsl(210 40% 98%)',
        card: 'hsl(222.2 84% 4.9%)',
        primary: 'hsl(217.2 91.2% 59.8%)',
        destructive: 'hsl(0 62.8% 30.6%)',
        muted: 'hsl(217.2 32.6% 17.5%)',
      },
    },
  },
};
```

### 2.5 TypeScript 类型生成

从 OpenAPI Schema 自动生成类型，确保前后端类型一致：

```json
// package.json scripts
{
  "generate:types": "openapi-typescript /api/v1/openapi.json -o src/api/types.ts"
}
```

---

## 3. 数据流

### 3.1 页面数据加载

```
用户导航到页面
    │
    ▼
React Router 匹配路由 → 渲染页面组件
    │
    ▼
页面组件调用 useQuery hook
    │
    ▼
TanStack Query 检查缓存
    │
    ├─ 缓存有效 → 直接渲染
    │
    └─ 缓存过期/无缓存 → fetch API
        │
        ▼
    API Client → /api/v1/xxx → JSON response
        │
        ▼
    更新缓存 → 触发重渲染
```

### 3.2 实时更新

```
WebSocket 连接建立
    │
    ▼
服务端推送消息 (overview_update / ledger_new / trigger_event)
    │
    ▼
onmessage handler
    │
    ├─ overview_update → setQueryData(['overview'], newData)
    │
    ├─ ledger_new → invalidateQueries(['ledger'])
    │
    └─ trigger_event → invalidateQueries(['triggers'])
```

---

## 4. 错误处理

### 4.1 API 错误

**处理**：全局错误边界 + Toast 通知。401 错误自动跳转到 Token 输入页。

### 4.2 网络断连

**处理**：TanStack Query 自动重试（3 次，指数退避）。WebSocket 断线自动重连。

### 4.3 数据为空

**处理**：空状态组件（图标 + 说明文字 + 引导操作）。

---

## 5. 配置

### 5.1 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `VITE_API_BASE` | API 基础路径 | `/api/v1` |

### 5.2 构建配置

```typescript
// vite.config.ts
export default defineConfig({
  base: '/console/',
  build: {
    outDir: '../static',
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
});
```

---

## 6. 测试策略

### 6.1 组件测试

- Vitest + React Testing Library
- 核心交互组件（DataTable、Filters、Charts）

### 6.2 E2E 测试

- Playwright
- 关键用户流程：登录 → Overview → Governance → Ledger 筛选

---

## 7. 迁移计划

### 7.1 Phase 1：工程搭建（2-3 天）

- [ ] Vite + React + TypeScript + Tailwind + Shadcn/ui 初始化
- [ ] 布局系统（Sidebar + Content）
- [ ] API Client + 类型生成
- [ ] 暗色主题配置

### 7.2 Phase 2：核心页面（4-5 天）

- [ ] Overview 页面
- [ ] Governance 页面（趋势图 + 熔断卡片 + 可见性矩阵）
- [ ] Ledger 页面（时间线 + 筛选 + 详情）

### 7.3 Phase 3：扩展页面（3-4 天）

- [ ] Agents 页面
- [ ] Capabilities 页面
- [ ] Triggers 页面
- [ ] Settings 页面
- [ ] Traces/Workflows 深链接页面

### 7.4 Phase 4：打磨与测试（1-3 天）

- [ ] WebSocket 实时更新
- [ ] 空状态 + 错误状态
- [ ] 组件测试
- [ ] 构建优化（代码分割 + Tree-shaking）

---

## 8. 风险与缓解

### 8.1 Shadcn/ui 版本兼容

**影响**：Shadcn/ui 更新可能破坏组件

**缓解**：锁定版本，使用 `components.json` 管理

### 8.2 图表性能

**影响**：大数据量图表渲染慢

**缓解**：后端预聚合，前端只渲染聚合后的数据点（最多 100 个点）

---

**维护者**：yeemio  
**最后更新**：2026-02-28
