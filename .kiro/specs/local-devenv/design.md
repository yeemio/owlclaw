# 设计文档：local-devenv（统一本地开发环境）

## 1. 架构决策

### 1.1 compose 文件分层策略

```
根目录（开发者日常入口）
├── docker-compose.dev.yml      # 全量开发环境（PG + Hatchet + Langfuse）
├── docker-compose.test.yml     # 测试专用（与 CI 完全镜像，仅 PG + pgvector）
└── docker-compose.minimal.yml  # 最小依赖（仅 PG + pgvector）

deploy/（生产/特殊场景，保持现有结构）
├── docker-compose.lite.hatchet-only.yml  # 保留（本机 PG 场景）
├── docker-compose.prod.yml               # 保留（生产）
└── docker-compose.cron.yml               # 保留（一体化）
```

**设计原则**：根目录 compose 文件面向开发者，`deploy/` 面向运维/生产。

### 1.2 镜像选型

| 服务 | 镜像 | 版本锁定 | 理由 |
|------|------|---------|------|
| PostgreSQL + pgvector | `pgvector/pgvector:pg16` | `pg16` | 与 CI `test.yml` 一致；pg16 是当前 LTS |
| Hatchet | `ghcr.io/hatchet-dev/hatchet/hatchet-lite:v0.53.0` | 具体版本 | 避免 latest 不稳定 |
| Langfuse | `langfuse/langfuse:2` | 主版本 | 官方镜像，不内嵌源码 |
| Redis（可选） | `redis:7-alpine` | `7` | Queue trigger 幂等存储 |

### 1.3 网络与端口规划

| 服务 | 容器端口 | 宿主端口 | 用途 |
|------|---------|---------|------|
| postgres | 5432 | 5432 | owlclaw DB + hatchet DB |
| hatchet-lite gRPC | 7078 | 17077 | SDK 连接（避免内部端口冲突）|
| hatchet-lite HTTP | 8888 | 8888 | Web UI |
| langfuse | 3000 | 3000 | Tracing UI + API |
| redis | 6379 | 6379 | 幂等存储（仅 dev 全量）|

### 1.4 数据库初始化策略

复用现有 `deploy/init-db.sql`（创建 hatchet/owlclaw 两库 + pgvector 扩展），
通过 `docker-entrypoint-initdb.d/` 机制自动执行，无需手动步骤。

### 1.5 Langfuse 集成方式

使用 Langfuse 官方 Docker 镜像（单容器模式），不内嵌 `.langfuse/` 源码。
Langfuse 单容器模式需要 PostgreSQL（复用 owlclaw-db）和可选 ClickHouse（dev 环境跳过）。

```yaml
langfuse:
  image: langfuse/langfuse:2
  environment:
    DATABASE_URL: postgresql://langfuse:langfuse@owlclaw-db:5432/langfuse
    NEXTAUTH_SECRET: dev-secret-change-in-prod
    NEXTAUTH_URL: http://localhost:3000
    SALT: dev-salt
  ports:
    - "3000:3000"
  depends_on:
    - owlclaw-db
```

## 2. 文件结构

### 2.1 docker-compose.dev.yml（全量）

```yaml
# OwlClaw 全量开发环境
# 包含：PostgreSQL + pgvector、Hatchet Lite、Langfuse、Redis
# 用法：docker compose -f docker-compose.dev.yml up -d
# 停止：docker compose -f docker-compose.dev.yml down
# 清除数据：docker compose -f docker-compose.dev.yml down -v

services:
  owlclaw-db:
    image: pgvector/pgvector:pg16
    ...（含 init-db.sql + langfuse DB 创建）

  hatchet-lite:
    image: ghcr.io/hatchet-dev/hatchet/hatchet-lite:v0.53.0
    ...

  langfuse:
    image: langfuse/langfuse:2
    ...

  redis:
    image: redis:7-alpine
    ...
```

### 2.2 docker-compose.test.yml（测试专用）

```yaml
# OwlClaw 测试环境 — 与 CI test.yml 完全镜像
# 仅包含：PostgreSQL + pgvector（owlclaw_test 数据库）
# 用法：docker compose -f docker-compose.test.yml up -d
#       poetry run pytest tests/unit/ tests/integration/ -m "not e2e"

services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: owlclaw_test
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 3s
      retries: 5
```

### 2.3 docker-compose.minimal.yml（最小依赖）

```yaml
# OwlClaw 最小依赖 — 仅核心数据库
# 适用于：只用 Agent 核心功能，不需要 Hatchet/Langfuse
# 用法：docker compose -f docker-compose.minimal.yml up -d

services:
  owlclaw-db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: owlclaw
    ports:
      - "5432:5432"
    volumes:
      - ./deploy/init-db.sql:/docker-entrypoint-initdb.d/init-db.sql
      - owlclaw_minimal_data:/var/lib/postgresql/data
```

## 3. 脚本封装

### 3.1 Makefile 目标

```makefile
dev-up:       ## 启动全量开发环境
dev-down:     ## 停止开发环境
dev-reset:    ## 重置（删除数据卷）
test-up:      ## 启动测试环境
test-down:    ## 停止测试环境
test:         ## 启动测试环境 + 运行测试
test-unit:    ## 仅运行单元测试（不需要外部服务）
test-int:     ## 运行集成测试（需要 test-up）
```

### 3.2 scripts/dev.sh（Windows 兼容备选）

PowerShell 版本 `scripts/dev.ps1` 提供相同功能。

## 4. 环境变量设计

`.env.example` 分区设计：

```
# === 必填（本地开发） ===
DATABASE_URL=...
OWLCLAW_DATABASE_URL=...

# === Hatchet（可选，需 docker-compose.dev.yml）===
HATCHET_API_TOKEN=
HATCHET_SERVER_URL=http://localhost:17077

# === Langfuse（可选，需 docker-compose.dev.yml）===
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=http://localhost:3000

# === Redis（可选，Queue trigger）===
REDIS_URL=redis://localhost:6379/0

# === Kafka（可选，Queue trigger）===
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

## 5. 文档结构

```
docs/
├── DEVELOPMENT.md    # 新建：本地开发环境搭建（一步到位）
└── DEPLOYMENT.md     # 新建：三种部署路径
```

### DEVELOPMENT.md 结构

1. 前置条件（Docker Desktop、Poetry）
2. 快速开始（3 步：clone → `docker compose up` → `poetry run pytest`）
3. 服务说明（各端口用途）
4. 常见问题

### DEPLOYMENT.md 结构

1. 部署路径总览（必须 vs 可选依赖表格）
2. 本地开发（docker-compose.dev.yml）
3. 自托管生产（最小依赖 + 可选组件）
4. 云托管（Managed DB + 容器化 owlclaw）
5. 环境变量完整参考
