# 本地开发指南（Development）

## 前置条件

1. Python 3.10+
2. Poetry 1.8+
3. Docker Desktop（用于本地 PostgreSQL/Hatchet/Langfuse 组合）

## 快速开始（3 步）

1. 安装依赖

```bash
poetry install
```

2. 准备环境变量

```bash
cp .env.example .env
```

3. 启动测试数据库并运行单测

```bash
docker compose -f docker-compose.test.yml up -d
poetry run pytest tests/unit/ -q
```

> 若 Docker 不可用，可先仅执行 `poetry run pytest tests/unit/test_cli_main.py -q` 做 CLI 快速回归。

## 常用端口

| 服务 | 端口 | 说明 |
|---|---|---|
| PostgreSQL（test/minimal） | `5432` | 本地开发数据库 |
| Hatchet Lite UI | `8888` | 管理界面 |
| Hatchet gRPC | `17077` | `HATCHET_SERVER_URL` 默认值 |
| Langfuse Web | `3000` | 本地观测平台 |

## 常见问题

1. Docker Engine 未启动  
现象：`//./pipe/dockerDesktopLinuxEngine` 不可用。  
处理：先启动 Docker Desktop，再执行 compose 命令。

2. PostgreSQL 端口冲突  
现象：`5432 already allocated`。  
处理：停止本机冲突服务或临时调整 compose 映射端口。

3. Hatchet 连接失败  
处理：确认 `.env` 中 `HATCHET_SERVER_URL` 与实际端口一致（默认 `http://localhost:17077`）。

## Windows 说明

1. 使用 PowerShell 运行命令（不要用 CMD）。
2. 若容器访问宿主失败，优先使用 `host.docker.internal`。
3. 本地防火墙可能拦截 5432/8888/17077，必要时手动放行。
