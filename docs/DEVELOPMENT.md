# 本地开发指南

## 前置条件

- Docker Desktop（或兼容 Docker Engine）
- Python 3.10+
- Poetry 2.x
- Git

## 快速开始（3 步）

1. 安装依赖

```bash
poetry install
```

2. 启动测试数据库（与 CI 镜像一致）

```bash
docker compose -f docker-compose.test.yml up -d
```

3. 运行测试

```bash
poetry run pytest tests/unit/ tests/integration/ -m "not e2e"
```

完成后可执行：

```bash
docker compose -f docker-compose.test.yml down
```

## 常用环境模式

### 1) 最小模式（只要数据库）

```bash
docker compose -f docker-compose.minimal.yml up -d
```

适用：只调试核心 runtime/capabilities，不依赖 Hatchet/Langfuse。

### 2) 全量开发模式

```bash
docker compose -f docker-compose.dev.yml up -d
```

包含：PostgreSQL(pgvector) + Hatchet Lite + Langfuse + Redis。

## 服务端口说明

| 服务 | 端口 | 说明 |
|------|------|------|
| PostgreSQL | `5432` | `owlclaw` / `hatchet` / `langfuse` 三库 |
| Hatchet gRPC | `17077` | SDK 连接地址（避免与容器内端口冲突） |
| Hatchet UI | `8888` | 默认账号 `admin@example.com` / `Admin123!!` |
| Langfuse | `3000` | Tracing UI/API |
| Redis | `6379` | Queue trigger 幂等存储 |

## 脚本与命令

- Linux/macOS: `scripts/test-local.sh [--unit-only] [--keep-up]`
- Windows PowerShell: `scripts/test-local.ps1 [-UnitOnly] [-KeepUp]`
- 若系统安装了 GNU make，可用：`make help`

## 常见问题

### Q1: `make` 不可用（Windows 默认）

Windows 默认没有 GNU make，直接使用 PowerShell 命令：

```powershell
scripts/test-local.ps1 -UnitOnly
```

### Q2: Docker 启动后 PostgreSQL 不健康

执行：

```bash
docker compose -f docker-compose.test.yml logs postgres
```

确认端口 `5432` 未被其他实例占用。

### Q3: Hatchet 连接失败

确认 `.env` 中：

- `HATCHET_SERVER_URL=http://localhost:17077`
- `HATCHET_API_TOKEN=<your token>`

Token 在 Hatchet UI (`http://localhost:8888`) 获取。

### Q4: Windows Docker 无法访问 `host.docker.internal`

- 确认 Docker Desktop 已启用
- 若公司安全策略限制，先放行本地防火墙规则
- 如需开放 PostgreSQL 5432 入站，可使用 `deploy/windows-firewall-5432.ps1`
