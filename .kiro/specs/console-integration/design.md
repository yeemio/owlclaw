# Design: Console Integration

> **目标**：将 Console 前后端集成到 OwlClaw 主进程，实现一键启动  
> **状态**：设计完成  
> **最后更新**：2026-02-28

---

## 1. 架构设计

### 1.1 整体架构

```
owlclaw start
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  uvicorn (single port, e.g., :8000)                      │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  Starlette/FastAPI Application                       │ │
│  │                                                       │ │
│  │  /api/v1/*     → Console REST API (FastAPI sub-app)  │ │
│  │  /console/*    → Static Files (SPA)                  │ │
│  │  /mcp/*        → MCP Protocol Server                 │ │
│  │  /webhook/*    → Webhook Trigger endpoints            │ │
│  │  /             → Redirect to /console/                │ │
│  └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 核心组件

#### 组件 1：Console 挂载器 (`owlclaw/web/mount.py`)

**职责**：检测静态文件，挂载 Console API 和前端到主应用。

```python
import logging
from pathlib import Path
from starlette.applications import Starlette
from starlette.staticfiles import StaticFiles
from starlette.responses import FileResponse

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


def mount_console(app: Starlette) -> bool:
    """Mount Console routes if static files exist. Returns True if mounted."""
    if not (STATIC_DIR / "index.html").exists():
        logger.info("Console static files not found, skipping mount")
        return False

    from owlclaw.web.app import create_console_app
    console_api = create_console_app()

    app.mount("/api/v1", console_api)
    app.mount("/console", StaticFiles(directory=str(STATIC_DIR), html=True))

    logger.info("Console mounted at /console/ (API at /api/v1/)")
    return True
```

#### 组件 2：CLI 命令 (`owlclaw/cli/console.py`)

**职责**：`owlclaw console` 命令。

```python
import webbrowser
import click

@click.command()
@click.option("--port", default=8000, help="Console port")
def console(port: int) -> None:
    """Open OwlClaw Console in browser."""
    url = f"http://localhost:{port}/console/"
    click.echo(f"Opening Console: {url}")
    webbrowser.open(url)
```

#### 组件 3：SPA Fallback 中间件

**职责**：非 API 路径返回 `index.html`，支持 SPA 客户端路由。

---

## 2. 实现细节

### 2.1 文件结构

```
owlclaw/web/
├── mount.py           # mount_console() — 检测 + 挂载
├── static/            # 前端构建产物（内嵌 Python 包）
│   ├── index.html
│   └── assets/
owlclaw/cli/
├── console.py         # owlclaw console 命令
```

### 2.2 路由优先级

1. `/api/v1/*` — Console REST API（最高优先级）
2. `/mcp/*` — MCP Protocol Server
3. `/webhook/*` — Webhook Trigger endpoints
4. `/console/*` — Static Files（SPA）
5. `/` — Redirect to `/console/`

### 2.3 pyproject.toml 变更

```toml
[tool.poetry.extras]
console = []  # Console 前端无额外 Python 依赖（静态文件）

[tool.poetry.plugins."owlclaw.cli"]
console = "owlclaw.cli.console:console"

[tool.poetry.package-data]
owlclaw = ["web/static/**/*"]
```

### 2.4 构建流程

```
开发时：
  cd owlclaw/web/frontend && pnpm dev
  → Vite dev server (:5173) + proxy /api → :8000

生产构建：
  cd owlclaw/web/frontend && pnpm build
  → 输出到 owlclaw/web/static/

Python 包发布：
  poetry build
  → owlclaw/web/static/** 包含在 wheel 中
```

---

## 3. 数据流

### 3.1 启动流程

```
owlclaw start
    │
    ▼
创建 Starlette/FastAPI 主应用
    │
    ▼
挂载 MCP Server 路由
    │
    ▼
挂载 Webhook 路由
    │
    ▼
调用 mount_console(app)
    │
    ├─ 静态文件存在 → 挂载 API + Static → 日志 INFO
    │
    └─ 静态文件不存在 → 跳过 → 日志 INFO
    │
    ▼
启动 uvicorn
```

---

## 4. 错误处理

### 4.1 无静态文件

**处理**：`mount_console()` 返回 `False`，日志 INFO 提示，不影响其他功能。

### 4.2 端口冲突

**处理**：由 `owlclaw start` 的端口配置处理，Console 不额外占用端口。

---

## 5. 测试策略

### 5.1 单元测试

- `mount_console()` 有/无静态文件两种场景
- CLI `console` 命令参数解析

### 5.2 集成测试

- 完整启动流程：`owlclaw start` → Console 可访问
- 降级场景：无静态文件 → Agent 运行时正常

---

## 6. 迁移计划

### 6.1 Phase 1：挂载与 CLI（1-2 天）

- [ ] 实现 `mount_console()`
- [ ] 实现 SPA fallback
- [ ] 实现 `owlclaw console` CLI
- [ ] 集成到 `owlclaw start`

### 6.2 Phase 2：打包与分发（1-2 天）

- [ ] 配置 pyproject.toml package-data
- [ ] 配置 extras
- [ ] 构建流程文档
- [ ] 验证 `pip install owlclaw[console]`

---

**维护者**：yeemio  
**最后更新**：2026-02-28
