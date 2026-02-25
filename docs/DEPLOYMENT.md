# 部署说明（Deployment）

本文档说明 OwlClaw 的部署路径与依赖边界。数据库/隔离原则以 [DATABASE_ARCHITECTURE.md](./DATABASE_ARCHITECTURE.md) 为准。

## 依赖矩阵（必须 vs 可选）

| 组件 | 必须 | 用途 |
|---|---|---|
| PostgreSQL（pgvector） | 是 | 核心数据存储（memory/ledger/state） |
| Hatchet | 否 | durable execution / 调度增强 |
| Langfuse | 否 | tracing 与可观测 |
| Redis | 否 | queue idempotency / 缓存 |

## 三种部署路径

1. 最小路径（推荐起步）
- 仅 PostgreSQL（含 pgvector）
- 适合：先跑核心能力与单机验证

2. 开发路径
- PostgreSQL + Hatchet + Langfuse（可选 Redis）
- 适合：联调、触发器、可观测验证

3. 生产路径
- PostgreSQL 为核心，Hatchet/Langfuse/Redis 按需启用
- 所有凭证通过环境变量管理，不在仓库明文存储

## 环境变量参考（核心）

| 变量 | 说明 | 示例 |
|---|---|---|
| `OWLCLAW_DATABASE_URL` | OwlClaw DB 连接 | `postgresql+asyncpg://owlclaw:owlclaw@localhost:5432/owlclaw` |
| `HATCHET_SERVER_URL` | Hatchet gRPC 地址 | `http://localhost:17077` |
| `HATCHET_API_TOKEN` | Hatchet API token | `<token>` |
| `LANGFUSE_HOST` | Langfuse 地址 | `http://localhost:3000` |
| `LANGFUSE_PUBLIC_KEY` | Langfuse 公钥 | `<pk>` |
| `LANGFUSE_SECRET_KEY` | Langfuse 私钥 | `<sk>` |

## 关键说明

`pip install owlclaw` 本身不强依赖 Docker。  
Docker 仅用于本地开发/测试便利化（快速拉起 PG/Hatchet/Langfuse）。
