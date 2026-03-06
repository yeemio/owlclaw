# Console 真实验收本地启动指南

> 适用：`console-browser-real-e2e` Task 2.1  
> 日期：2026-03-05

## 1. 前置条件

- Python/Poetry 已安装
- Node.js/npm 已安装
- 可选：本地 PostgreSQL（若不走 `-SkipDbInit`）

## 2. 一键启动

```powershell
# 含 DB 初始化
$env:PG_PASSWORD = "<postgres_password>"
./scripts/console-local-setup.ps1

# 跳过 DB 初始化（仅验证无 DB 降级链路）
./scripts/console-local-setup.ps1 -SkipDbInit -Port 8000
```

## 3. 前端 E2E

```powershell
cd owlclaw/web/frontend
npm run test:e2e:run
```

## 4. WS 消息验证注意项

若要验证 `N-8`（收到 WS 消息类型），需安装 websocket 依赖：

```powershell
poetry run python -m pip install "uvicorn[standard]"
```

否则会出现 `No supported WebSocket library detected`，只能验证连接尝试（`N-7`），无法完成消息接收验证（`N-8`）。
