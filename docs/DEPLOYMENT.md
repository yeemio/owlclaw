# 部署指南

## 依赖矩阵（必须 vs 可选）

| 组件 | 本地开发 | 最小生产 | 增强生产 |
|------|---------|---------|---------|
| PostgreSQL(pgvector) | 必须 | 必须 | 必须 |
| Hatchet | 可选 | 可选 | 推荐 |
| Langfuse | 可选 | 可选 | 推荐 |
| Redis | 可选 | 可选 | 推荐（Queue 幂等） |
| Kafka/RabbitMQ/SQS | 可选 | 按需 | 按需 |

## 关键原则

- `pip install owlclaw` 本身 **零 Docker 依赖**。
- Docker Compose 仅用于本地快速启动依赖服务。
- 生产可以用托管服务替代（托管 PostgreSQL、托管 Redis、SaaS Langfuse 等）。

## 三种部署路径

### 路径 A：本地全量开发

```bash
docker compose -f docker-compose.dev.yml up -d
```

适用：功能联调、集成测试、演示环境。

### 路径 B：最小依赖生产（仅 PG）

- 必需：`pgvector/pgvector:pg16` 或兼容 PostgreSQL + pgvector
- OwlClaw 通过 `OWLCLAW_DATABASE_URL` 连接
- Hatchet/Langfuse/Redis 按业务需要再接入

### 路径 C：增强生产（PG + 可选组件）

推荐组合：

- PostgreSQL(pgvector)
- Hatchet（持久调度）
- Langfuse（可观测）
- Redis（幂等/缓存）

## 环境变量参考

### 核心数据库

- `DATABASE_URL`
- `OWLCLAW_DATABASE_URL`
- `OWLCLAW_ADMIN_URL`（用于 db init）

### Hatchet

- `HATCHET_API_TOKEN`
- `HATCHET_SERVER_URL`
- `HATCHET_GRPC_TLS_STRATEGY`
- `HATCHET_GRPC_HOST_PORT`

### Langfuse

- `LANGFUSE_PUBLIC_KEY`
- `LANGFUSE_SECRET_KEY`
- `LANGFUSE_HOST`

### Redis/Kafka/RabbitMQ/SQS

详见根目录 `.env.example`，已按分区提供默认值与说明。

## 与 deploy/ 的关系

- 根目录 compose（`docker-compose.dev.yml` / `docker-compose.test.yml` / `docker-compose.minimal.yml`）是开发者首选入口。
- `deploy/` 下 compose 用于生产/特殊运维场景，详见 `deploy/README.md`。
