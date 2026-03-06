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

## 5. Console 多租户与 tenant_id

- 当前行为：Console API 通过 `x-owlclaw-tenant` 请求头读取 tenant_id（缺省回落为 `default`），服务端不对该 header 做租户身份校验。
- 适用场景：单租户或自托管环境中，将 tenant_id 作为命名空间标签使用，而非安全边界。
- 多租户要求：生产多租户部署必须从认证上下文推导 tenant_id（例如 session/JWT/API key scope），不要信任客户端直接传入的 `x-owlclaw-tenant`。
