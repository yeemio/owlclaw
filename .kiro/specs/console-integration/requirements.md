# Requirements: Console Integration

> **目标**：将 Console 前后端集成到 OwlClaw 主进程，实现一键启动和 Python 包分发  
> **优先级**：P0  
> **预估工作量**：3-5 天

---

## 1. 背景与动机

### 1.1 当前问题

Console 后端 API 和前端 SPA 作为独立组件开发，需要集成到 OwlClaw 主进程中，使用户通过 `owlclaw start` 一键启动完整系统（Agent 运行时 + Console），无需额外安装 Node.js 或手动配置。

### 1.2 设计目标

实现 Console 的零配置集成：静态文件内嵌 Python 包，`owlclaw start` 自动检测并挂载，CLI 提供便捷的 Console 访问命令。

---

## 2. 用户故事

### 2.1 作为运维人员

**故事 1**：一键启动
```
作为运维人员
我希望 `owlclaw start` 自动启动 Console
这样我不需要额外配置就能访问 Web 界面
```

**验收标准**：
- [ ] `owlclaw start` 检测到静态文件时自动挂载 Console 路由
- [ ] Console 和 Agent 运行时共用同一端口
- [ ] 无静态文件时优雅降级（不报错，日志提示）

**故事 2**：便捷访问
```
作为运维人员
我希望通过 `owlclaw console` 命令快速打开 Console
这样我不需要记住 URL
```

**验收标准**：
- [ ] `owlclaw console` 自动打开浏览器
- [ ] 支持 `--port` 参数
- [ ] 显示 Console URL

### 2.2 作为开发者

**故事 3**：前端开发体验
```
作为前端开发者
我希望 `pnpm dev` 独立开发前端，热更新
这样我不需要每次重启 Python 进程
```

**验收标准**：
- [ ] 开发时 Vite dev server 代理 API 到 Python 后端
- [ ] 生产时静态文件由 Python 进程直接服务

**故事 4**：可选安装
```
作为只需要 CLI 的用户
我希望 Console 是可选依赖
这样我不需要安装前端相关的包
```

**验收标准**：
- [ ] `pip install owlclaw` 不包含 Console 前端依赖
- [ ] `pip install owlclaw[console]` 包含 Console

---

## 3. 功能需求

### 3.1 自动挂载

#### FR-1：静态文件检测与挂载

**需求**：`owlclaw start` 启动时检测 `owlclaw/web/static/` 是否存在，存在则自动挂载。

**验收标准**：
- [ ] 检测 `owlclaw/web/static/index.html` 存在
- [ ] 挂载到 `/console/` 路径
- [ ] SPA 路由 fallback（所有非 API 路径返回 `index.html`）
- [ ] 无静态文件时跳过挂载，日志 INFO 级别提示

#### FR-2：API 路由集成

**需求**：Console API 路由与 Agent 运行时共用同一 FastAPI/Starlette 应用。

**验收标准**：
- [ ] `/api/v1/*` 路由由 Console API 处理
- [ ] `/console/*` 路由由静态文件处理
- [ ] 其他路由由 Agent 运行时处理（MCP、Webhook 等）

### 3.2 CLI 命令

#### FR-3：`owlclaw console` 命令

**需求**：CLI 命令打开 Console。

**验收标准**：
- [ ] `owlclaw console` 打开默认浏览器
- [ ] `owlclaw console --port 9000` 指定端口
- [ ] 输出 Console URL 到终端

### 3.3 构建与打包

#### FR-4：前端构建流程

**需求**：前端构建产物集成到 Python 包。

**验收标准**：
- [ ] `pnpm build` 输出到 `owlclaw/web/static/`
- [ ] `pyproject.toml` 包含 `owlclaw/web/static/**` 在 package data 中
- [ ] `pip install owlclaw[console]` 后静态文件可用

#### FR-5：pyproject.toml extras

**需求**：Console 作为可选依赖。

**验收标准**：
- [ ] `[tool.poetry.extras]` 新增 `console` 组
- [ ] Console 特有依赖（如有）在 extras 中声明

---

## 4. 非功能需求

### 4.1 零配置

**NFR-1：开箱即用**
- 安装 `owlclaw[console]` 后无需额外配置即可使用 Console

**验收标准**：
- [ ] 无需设置环境变量即可启动（认证默认关闭）
- [ ] 无需安装 Node.js

### 4.2 优雅降级

**NFR-2：无 Console 时不影响核心功能**
- 未安装 Console extras 时，`owlclaw start` 正常启动 Agent 运行时

**验收标准**：
- [ ] 无静态文件时不报错
- [ ] `owlclaw console` 提示需要安装 `owlclaw[console]`

---

## 5. 验收标准总览

### 5.1 功能验收
- [ ] **FR-1**：静态文件自动挂载
- [ ] **FR-2**：API + Console + Agent 路由共存
- [ ] **FR-3**：CLI 命令可用
- [ ] **FR-4**：构建流程正确
- [ ] **FR-5**：extras 配置正确

### 5.2 非功能验收
- [ ] **NFR-1**：零配置启动
- [ ] **NFR-2**：优雅降级

### 5.3 测试验收
- [ ] 集成测试覆盖挂载/降级场景
- [ ] CLI 命令测试

---

## 6. 约束与假设

### 6.1 约束
- 静态文件路径固定为 `owlclaw/web/static/`
- Console 路径固定为 `/console/`
- API 路径固定为 `/api/v1/`

### 6.2 假设
- console-backend-api 和 console-frontend 已实现
- `owlclaw start` 命令已存在（gateway-runtime-ops spec）

---

## 7. 依赖

### 7.1 内部依赖
- console-backend-api — REST API
- console-frontend — 前端 SPA 构建产物
- gateway-runtime-ops — `owlclaw start` 命令

---

## 8. 风险与缓解

### 8.1 风险：静态文件体积影响 PyPI 包大小

**影响**：前端构建产物可能增加 Python 包体积

**缓解**：
- 前端 gzip 后 < 500KB
- 作为 extras 可选安装

---

## 9. Definition of Done

### 9.1 集成
- [ ] `owlclaw start` 自动挂载 Console（有静态文件时）
- [ ] `owlclaw start` 优雅降级（无静态文件时）
- [ ] `owlclaw console` 打开浏览器

### 9.2 打包
- [ ] `pip install owlclaw[console]` 包含静态文件
- [ ] `pip install owlclaw` 不包含 Console 依赖

---

## 10. 参考文档

- `docs/ARCHITECTURE_ANALYSIS.md` §4.15 — Console 部署方案
- `.kiro/specs/console-backend-api/` — Backend API spec
- `.kiro/specs/console-frontend/` — Frontend spec
- `.kiro/specs/gateway-runtime-ops/` — `owlclaw start` 命令

---

**维护者**：yeemio  
**最后更新**：2026-02-28
