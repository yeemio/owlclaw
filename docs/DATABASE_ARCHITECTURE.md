# OwlClaw 数据库架构

> **版本**: v1.0.0 (2026-02-10)
> **定位**: OwlClaw 数据库架构的**唯一真源**
> **关联**: `docs/ARCHITECTURE_ANALYSIS.md`（系统架构）、`deploy/`（部署脚本）

---

## 一、设计原则

### 1.1 五条铁律

| # | 原则 | 说明 |
|---|------|------|
| 1 | **复用宿主 PostgreSQL** | OwlClaw 不自行部署 PostgreSQL 实例，在宿主已有的 PostgreSQL 上创建 database。降低接入门槛，避免强制增加基础设施 |
| 2 | **组件间 database 级隔离** | OwlClaw 业务数据、Hatchet、Langfuse 各自使用独立的 database，互不干扰。权限、migration、备份均独立 |
| 3 | **tenant_id 从 Day 1 存在** | 所有 OwlClaw 表从第一天起包含 `tenant_id` 字段。Self-hosted 默认 `'default'`，为 Cloud 多租户预留，避免未来大规模 ALTER TABLE 返工 |
| 4 | **各组件独立管理 migration** | OwlClaw 用 Alembic，Hatchet 和 Langfuse 用各自内建 migration。OwlClaw 不介入第三方组件的 schema 管理 |
| 5 | **运维通过 CLI 统一入口** | 所有数据库运维操作通过 `owlclaw db` 子命令完成，封装底层工具（Alembic、pg_dump 等），提供一致的用户体验 |

### 1.2 为什么是 database 级隔离而不是 schema 级

Hatchet 官方文档明确要求：

> The database user requires permissions to write and modify schemas **on a clean database**. It is therefore recommended to create a **separate database instance** where Hatchet can run.

Hatchet 的 migration 需要对 database 有完整的 DDL 权限（创建/修改 schema、表、索引、扩展）。如果和 OwlClaw 业务数据放在同一个 database 里：

- Hatchet migration 可能意外影响 OwlClaw 的表
- OwlClaw 的 migration 可能与 Hatchet 的 migration 冲突
- 权限隔离困难（Hatchet 需要 database owner 级权限）

因此：**同一个 PostgreSQL 服务器进程，不同的 database**。

---

## 二、部署模式

OwlClaw 的数据库架构支持三种部署模式，对应产品的不同阶段。架构从 Day 1 就为最终形态设计，避免阶段间的破坏性迁移。

### 2.1 Self-hosted（MIT 开源，当前阶段）

**适用场景**：企业在自己的基础设施上部署 OwlClaw，接入已有的业务系统。

**核心特征**：
- 复用宿主已有的 PostgreSQL 实例，`owlclaw db init` 创建所需 database
- 单租户，`tenant_id` 默认 `'default'`
- 用户完全掌控数据

```
宿主已有的 PostgreSQL 实例
│
├── database: owlclaw                    ← OwlClaw 业务数据
│   ├── role: owlclaw                    ← OwlClaw 应用用户（database owner）
│   ├── schema: public
│   │   ├── alembic_version              ← Alembic 迁移版本追踪
│   │   ├── ledger_records               ← 治理层执行记录
│   │   ├── agent_memory                 ← Agent 长期记忆（含向量列）
│   │   ├── agent_identity               ← Agent 身份配置
│   │   └── ...                          ← 其他 OwlClaw 表
│   └── extension: pgvector             ← 向量搜索（Agent 记忆）
│
├── database: hatchet                    ← Hatchet 独占
│   ├── role: hatchet                    ← Hatchet 专用用户（database owner）
│   └── (Hatchet 内部表，由 Hatchet migration 管理)
│
├── database: langfuse (可选)            ← Langfuse 自托管时使用
│   ├── role: langfuse
│   └── (Langfuse 内部表，由 Langfuse migration 管理)
│
└── (宿主自己的 database)               ← OwlClaw 不碰
```

**部署拓扑**：

```
┌─────────────────────────────────────────────────────────────────┐
│                        宿主基础设施                                │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ 宿主业务应用  │  │ OwlClaw      │  │ Hatchet      │           │
│  │ (Java/.NET/  │  │ Worker       │  │ Server (Go)  │           │
│  │  Python/...) │  │ (Python)     │  │              │           │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘           │
│         │                 │                  │                    │
│         │ 宿主 DB         │ owlclaw DB       │ hatchet DB        │
│         └────────┐        │        ┌─────────┘                    │
│                  ▼        ▼        ▼                              │
│         ┌─────────────────────────────────────┐                   │
│         │     宿主已有的 PostgreSQL 实例        │                   │
│         │  ┌────────┬─────────┬─────────┐     │                   │
│         │  │宿主 DB │ owlclaw │ hatchet │     │                   │
│         │  │        │   DB    │   DB    │     │                   │
│         │  └────────┴─────────┴─────────┘     │                   │
│         └─────────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 OwlClaw Cloud（未来 SaaS）

**适用场景**：OwlClaw 提供托管服务，多个客户（租户）共享基础设施。

**核心特征**：
- OwlClaw Cloud 管理 PostgreSQL 集群
- 共享 database + RLS（Row-Level Security）实现租户隔离
- Hatchet 天然支持 `tenant_id`，内建公平队列（fair queueing）
- 连接池统一管理，成本最优

```
OwlClaw Cloud 管理的 PostgreSQL 集群
│
├── database: owlclaw
│   ├── RLS 策略：所有表强制 tenant_id = current_setting('app.tenant_id')
│   ├── 连接池：PgBouncer / Supavisor，统一管理
│   └── schema: public
│       ├── alembic_version
│       ├── ledger_records        (tenant_id = 'tenant_abc', ...)
│       ├── agent_memory          (tenant_id = 'tenant_abc', ...)
│       ├── agent_identity        (tenant_id = 'tenant_abc', ...)
│       └── ...
│
├── database: hatchet
│   └── Hatchet 内建 tenant_id 天然支持多租户公平队列
│
└── database: langfuse
    └── Langfuse 内建多租户支持
```

**RLS 策略示意**：

```sql
-- Cloud 阶段引入，Self-hosted 不需要
ALTER TABLE ledger_records ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON ledger_records
    USING (tenant_id = current_setting('app.tenant_id'));

-- 每个请求开始时设置租户上下文
SET LOCAL app.tenant_id = 'tenant_abc';
```

**为什么 Cloud 用 RLS 而不是 Database-per-tenant**：

| 维度 | RLS（共享表） | Database-per-tenant |
|------|-------------|-------------------|
| 运维成本 | 低（一份 migration、一份备份） | 高（N 份 migration、N 份备份） |
| 连接池效率 | 高（一个池） | 低（N 个池或动态路由） |
| 租户数量上限 | 数万+ | 数百（受 PostgreSQL 连接限制） |
| 隔离强度 | 中（逻辑隔离） | 高（物理隔离） |
| 适用阶段 | Cloud 标准版 | Enterprise VIP |

### 2.3 Enterprise（商业许可）

**适用场景**：高合规要求的大客户，需要更强的数据隔离。

**可选能力**（在 `owlclaw-enterprise` 包中）：

- **Database-per-tenant**：为 VIP 租户创建独立 database，提供物理级隔离
- **BYOD（Bring Your Own Database）**：客户提供自己的 PostgreSQL 实例，OwlClaw Cloud 远程连接
- **独立实例**：为超大客户部署独立的 PostgreSQL 集群

### 2.4 三种模式的演进路径

```
Self-hosted (单租户)          OwlClaw Cloud (多租户)         Enterprise (VIP 隔离)
┌─────────────────┐          ┌─────────────────┐          ┌─────────────────┐
│ tenant_id =     │          │ tenant_id =     │          │ 独立 database   │
│ 'default'       │  ──────► │ 'tenant_xxx'    │  ──────► │ 或独立实例      │
│ 无 RLS          │          │ RLS 强制隔离    │          │ 物理隔离        │
│ 复用宿主 PG     │          │ 托管 PG 集群    │          │ BYOD 可选       │
└─────────────────┘          └─────────────────┘          └─────────────────┘

关键：tenant_id 从 Day 1 存在，模式切换只需要：
  - Self-hosted → Cloud：启用 RLS 策略 + 更新 tenant_id 值
  - Cloud → Enterprise：创建独立 database + 数据迁移
```

---

## 三、数据模型

### 3.1 OwlClaw 核心表

以下是 `owlclaw` database 中的核心表。所有表都包含 `tenant_id` 字段。

| 表名 | 用途 | 关键字段 | 模块 |
|------|------|---------|------|
| `alembic_version` | Alembic 迁移版本追踪 | `version_num` | Alembic 内建 |
| `ledger_records` | 治理层执行记录 | `tenant_id`, `agent_id`, `capability`, `decision`, `cost`, `created_at` | `governance/ledger.py` |
| `agent_memory` | Agent 长期记忆 | `tenant_id`, `agent_id`, `content`, `embedding`(vector), `tags`, `created_at` | `agent/memory.py` |
| `agent_identity` | Agent 身份配置 | `tenant_id`, `agent_id`, `soul_config`, `updated_at` | `agent/identity.py` |
| `governance_rules` | 治理规则（可见性过滤、预算等） | `tenant_id`, `rule_type`, `config`, `enabled` | `governance/visibility.py` |
| `trigger_schedules` | 触发器调度记录 | `tenant_id`, `trigger_type`, `cron_expr`, `next_run_at` | `triggers/` |

### 3.2 tenant_id 设计

```sql
-- 所有 OwlClaw 表的 tenant_id 设计
-- Self-hosted 默认值 'default'，Cloud 阶段为真实租户 ID

CREATE TABLE ledger_records (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       VARCHAR(64) NOT NULL DEFAULT 'default',
    agent_id        VARCHAR(128) NOT NULL,
    capability      VARCHAR(256) NOT NULL,
    decision        JSONB NOT NULL,
    cost            DECIMAL(10, 6),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- 复合索引：tenant_id 作为前缀，支持 RLS 高效过滤
    CONSTRAINT idx_ledger_tenant_created
        UNIQUE (tenant_id, created_at, id)
);

-- 索引策略：所有查询都以 tenant_id 为前缀
CREATE INDEX idx_ledger_tenant_agent ON ledger_records (tenant_id, agent_id);
CREATE INDEX idx_ledger_tenant_capability ON ledger_records (tenant_id, capability);
```

### 3.3 pgvector 扩展

`pgvector` 用于 Agent 记忆的向量搜索（语义检索）：

```sql
-- 在 owlclaw database 中启用
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE agent_memory (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       VARCHAR(64) NOT NULL DEFAULT 'default',
    agent_id        VARCHAR(128) NOT NULL,
    content         TEXT NOT NULL,
    embedding       vector(1536),           -- OpenAI text-embedding-3-small 维度
    tags            TEXT[],
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ             -- 可选过期时间
);

-- 向量索引（HNSW 比 IVFFlat 更适合中小规模数据）
CREATE INDEX idx_memory_embedding ON agent_memory
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- 常规索引
CREATE INDEX idx_memory_tenant_agent ON agent_memory (tenant_id, agent_id);
CREATE INDEX idx_memory_tenant_tags ON agent_memory USING gin (tags);
```

---

## 四、Schema 迁移策略

### 4.1 迁移职责矩阵

| 组件 | database | 迁移由谁管 | 工具 | 触发方式 |
|------|----------|-----------|------|---------|
| **OwlClaw** | `owlclaw` | OwlClaw 自己 | **Alembic** | `owlclaw db migrate` |
| **Hatchet** | `hatchet` | Hatchet Server | Hatchet 内建 migration | Server 启动时自动执行 |
| **Langfuse** | `langfuse` | Langfuse Server | Langfuse 内建 migration | Server 启动时自动执行 |

OwlClaw 只管自己的 `owlclaw` database。Hatchet 和 Langfuse 的 migration 由它们自己的 Server 进程在启动时自动完成，OwlClaw 不介入。

### 4.2 为什么选 Alembic

1. **SQLAlchemy 官方配套** —— OwlClaw 已选 SQLAlchemy 作为 ORM，Alembic 是其原生迁移工具
2. **autogenerate** —— 从 SQLAlchemy model 定义自动生成迁移脚本，减少手写 SQL 的错误
3. **依赖极轻** —— Alembic 的额外依赖仅 Mako（模板引擎），对 SDK 的依赖负担几乎为零
4. **Python 生态标准** —— FastAPI、Flask、大量开源项目的标准选择
5. **版本追踪 + 回滚** —— 每次 schema 变更有记录，支持 upgrade/downgrade

### 4.3 Alembic 目录结构

```
owlclaw/
├── owlclaw/                 # SDK 代码
│   └── ...
├── migrations/              # Alembic 迁移目录
│   ├── env.py               # Alembic 环境配置（读取 OwlClaw 的 DB URL）
│   ├── script.py.mako       # 迁移脚本模板
│   └── versions/            # 迁移文件（自动生成 + 手动调整）
│       └── 001_initial.py   # 第一个迁移（创建 Ledger、Memory 等表）
├── alembic.ini              # Alembic 配置（指向 migrations/）
└── pyproject.toml           # alembic 依赖
```

### 4.4 引入时机

在实现第一个需要数据库表的模块时引入（预计是 `governance/ledger.py` 或 `agent/memory.py`）。第一张表创建时就应该有迁移记录。

---

## 五、运维工具：owlclaw db CLI

所有数据库运维操作通过 `owlclaw db` 子命令完成。CLI 是底层工具（Alembic、psql、pg_dump）的统一封装，提供一致的用户体验。

**范畴说明**（防止与 Alembic 混淆）：
- **建库（创建 database、role、extension）**：属于 **`owlclaw db init`**，不是 Alembic。init 在宿主已有 PostgreSQL 上创建 `owlclaw` / `hatchet` 库及对应用户，并在 owlclaw 库启用 pgvector（若已安装）。
- **Schema 迁移（表结构变更）**：属于 **Alembic**，通过 **`owlclaw db migrate`** 执行。仅针对已存在的 `owlclaw` 库内的表。

不得用独立脚本或 ad-hoc SQL 绕过 CLI 建库；一律使用 `owlclaw db init`（或与架构等价的 `deploy/init-db.sql` 由 DBA 在宿主机执行）。

### 5.1 命令总览

| 命令 | 用途 | 底层工具 | 优先级 |
|------|------|---------|--------|
| `owlclaw db init` | 初始化数据库（创建 database + role + extension） | psql / SQLAlchemy | P0 |
| `owlclaw db migrate` | 执行 schema 迁移（升级到最新） | Alembic `upgrade head` | P0 |
| `owlclaw db status` | 检查数据库状态（连接、迁移版本、表统计） | Alembic `current` + SQLAlchemy | P0 |
| `owlclaw db revision` | 生成新的迁移脚本 | Alembic `revision --autogenerate` | P1 |
| `owlclaw db rollback` | 回滚迁移（指定步数或版本） | Alembic `downgrade` | P1 |
| `owlclaw db backup` | 备份 owlclaw database | pg_dump | P2 |
| `owlclaw db restore` | 从备份恢复 | pg_restore | P2 |
| `owlclaw db check` | 健康检查（连接池、慢查询、磁盘） | SQLAlchemy + pg_stat | P2 |

### 5.2 命令详细设计

#### `owlclaw db init`

在宿主已有的 PostgreSQL 实例上创建 OwlClaw 所需的 database、role 和 extension。实现上优先使用 async 驱动，若遇连接重置（如 Windows 下 WinError 64）则自动用 psycopg2 同步后备重试，与 `init-db.sql` 行为一致。

```bash
# 基本用法（需要 PostgreSQL 超级用户权限）
owlclaw db init --admin-url postgresql://postgres:xxx@localhost:5432/postgres

# 指定自定义密码
owlclaw db init --admin-url postgresql://postgres:xxx@localhost:5432/postgres \
    --owlclaw-password mypassword \
    --hatchet-password hatchetpass

# 跳过 Hatchet database 创建（如果 Hatchet 已经有自己的 database）
owlclaw db init --admin-url ... --skip-hatchet

# 只检查，不执行（dry-run）
owlclaw db init --admin-url ... --dry-run
```

**执行的操作**：

```sql
-- 1. 创建 OwlClaw database 和 role
CREATE ROLE owlclaw WITH LOGIN PASSWORD '${password}';
CREATE DATABASE owlclaw OWNER owlclaw;

-- 2. 启用 pgvector 扩展
\c owlclaw
CREATE EXTENSION IF NOT EXISTS vector;

-- 3. 创建 Hatchet database 和 role（可选）
CREATE ROLE hatchet WITH LOGIN PASSWORD '${password}';
CREATE DATABASE hatchet OWNER hatchet;
```

#### `owlclaw db migrate`

执行 OwlClaw 的 schema 迁移。

```bash
# 升级到最新版本
owlclaw db migrate

# 升级到指定版本
owlclaw db migrate --target abc123

# 显示将要执行的迁移（不实际执行）
owlclaw db migrate --dry-run

# 使用指定的数据库 URL（覆盖配置文件）
owlclaw db migrate --database-url postgresql://owlclaw:xxx@localhost:5432/owlclaw
```

#### `owlclaw db status`

检查数据库连接和迁移状态。

```bash
$ owlclaw db status

OwlClaw Database Status
=======================
Connection:     postgresql://owlclaw:***@localhost:5432/owlclaw
Server:         PostgreSQL 15.6
Extensions:     pgvector 0.7.0
Migration:      abc123 (2026-02-10: add ledger table)
Pending:        0 migrations
Tables:         6
Total rows:     12,345
Disk usage:     48 MB
```

#### `owlclaw db revision`

生成新的迁移脚本（开发者使用）。

```bash
# 从 model 自动生成迁移
owlclaw db revision -m "add governance_rules table"

# 生成空迁移（手动编写）
owlclaw db revision -m "custom data migration" --empty
```

#### `owlclaw db rollback`

回滚迁移。

```bash
# 回滚一个版本
owlclaw db rollback

# 回滚到指定版本
owlclaw db rollback --target abc123

# 回滚 N 步
owlclaw db rollback --steps 3
```

#### `owlclaw db backup`

备份 owlclaw database。

```bash
# 备份到文件
owlclaw db backup --output ./backups/owlclaw_20260210.sql

# 自定义格式（支持 pg_restore）
owlclaw db backup --output ./backups/owlclaw_20260210.dump --format custom

# 只备份 schema（不含数据）
owlclaw db backup --output ./backups/schema.sql --schema-only
```

#### `owlclaw db restore`

从备份恢复。

```bash
# 从 SQL 文件恢复
owlclaw db restore --input ./backups/owlclaw_20260210.sql

# 从 custom 格式恢复
owlclaw db restore --input ./backups/owlclaw_20260210.dump
```

#### `owlclaw db check`

数据库健康检查。

```bash
$ owlclaw db check

OwlClaw Database Health Check
==============================
[OK]  Connection:        responsive (2ms)
[OK]  Migration:         up to date (abc123)
[OK]  pgvector:          installed (0.7.0)
[OK]  Connection pool:   5/20 active
[OK]  Disk usage:        48 MB (< 80% threshold)
[WARN] Slow queries:     2 queries > 1s in last hour
[OK]  Replication lag:   N/A (no replicas)

Overall: HEALTHY (1 warning)
```

### 5.3 CLI 实现位置

```
owlclaw/
├── owlclaw/
│   └── cli/
│       ├── __init__.py
│       ├── main.py          # CLI 主入口（click / typer）
│       └── db.py            # owlclaw db 子命令组
```

---

## 六、连接管理

### 6.1 连接字符串规范

OwlClaw 支持两种方式配置数据库连接：

**方式一：环境变量（推荐用于容器化部署）**

```bash
export OWLCLAW_DATABASE_URL=postgresql://owlclaw:password@localhost:5432/owlclaw
```

**方式二：配置文件（推荐用于开发）**

```yaml
# owlclaw.yaml
database:
  url: postgresql://owlclaw:${OWLCLAW_DB_PASSWORD}@localhost:5432/owlclaw
  pool_size: 20
  max_overflow: 10
  pool_timeout: 30
  pool_recycle: 1800
  echo: false           # 开发时可设为 true 打印 SQL
```

**优先级**：环境变量 > 配置文件 > 默认值

### 6.2 SQLAlchemy 连接池配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `pool_size` | 20 | 连接池常驻连接数 |
| `max_overflow` | 10 | 超出 pool_size 时允许的额外连接数 |
| `pool_timeout` | 30 | 等待可用连接的超时时间（秒） |
| `pool_recycle` | 1800 | 连接回收时间（秒），防止数据库端超时断开 |
| `pool_pre_ping` | true | 使用前 ping 检测连接是否存活 |

### 6.3 Hatchet 连接配置

Hatchet Server 独立连接 `hatchet` database，OwlClaw 不管理 Hatchet 的数据库连接：

```yaml
# owlclaw.yaml
hatchet:
  server_url: http://localhost:7077
  api_token: ${HATCHET_API_TOKEN}
  namespace: owlclaw

  # 以下配置传递给 Hatchet Server（通过环境变量或 Hatchet 配置）
  # DATABASE_URL: postgresql://hatchet:${HATCHET_DB_PASSWORD}@localhost:5432/hatchet
```

---

## 七、性能指南

### 7.1 索引策略

**原则**：所有查询都以 `tenant_id` 为前缀，确保 RLS 引入后性能不退化。

```sql
-- 推荐：复合索引以 tenant_id 为前缀
CREATE INDEX idx_ledger_tenant_agent ON ledger_records (tenant_id, agent_id);
CREATE INDEX idx_ledger_tenant_created ON ledger_records (tenant_id, created_at DESC);

-- 避免：不含 tenant_id 的索引（RLS 下效率低）
-- CREATE INDEX idx_ledger_agent ON ledger_records (agent_id);  -- 不推荐
```

### 7.2 连接池调优

| 部署规模 | pool_size | max_overflow | 说明 |
|---------|-----------|-------------|------|
| 开发 | 5 | 5 | 单开发者 |
| 小型生产 | 20 | 10 | 单实例，< 100 Agent |
| 中型生产 | 50 | 20 | 多实例，100-1000 Agent |
| 大型 / Cloud | 使用 PgBouncer | - | 外部连接池管理 |

### 7.3 pgvector 向量索引

| 索引类型 | 适用场景 | 构建速度 | 查询速度 | 内存占用 |
|---------|---------|---------|---------|---------|
| **HNSW** | 中小规模（< 100 万向量） | 慢 | 快 | 高 |
| **IVFFlat** | 大规模（> 100 万向量） | 快 | 中 | 低 |

**推荐**：Self-hosted 和 Cloud 初期使用 HNSW；数据量超过 100 万条记忆时切换到 IVFFlat。

```sql
-- HNSW（推荐默认）
CREATE INDEX idx_memory_embedding ON agent_memory
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- IVFFlat（大规模时切换）
-- CREATE INDEX idx_memory_embedding ON agent_memory
--     USING ivfflat (embedding vector_cosine_ops)
--     WITH (lists = 100);
```

---

## 八、灾备与高可用

### 8.1 备份策略

| 场景 | 工具 | 频率 | 保留期 |
|------|------|------|--------|
| 开发 | `owlclaw db backup` | 按需 | 不限 |
| 生产（小型） | `owlclaw db backup` + cron | 每日 | 7 天 |
| 生产（中型） | pg_basebackup + WAL 归档 | 持续 | 30 天 |
| Cloud | 云托管自动备份（RDS / Cloud SQL） | 持续 | 按 SLA |

**备份范围**：`owlclaw db backup` 只备份 `owlclaw` database。Hatchet 和 Langfuse 的备份由各自的运维流程负责。

### 8.2 高可用方案

**Self-hosted（推荐）**：

```
                    ┌──────────────────┐
                    │   OwlClaw App    │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │   PostgreSQL     │
                    │   Primary        │
                    │   (读写)         │
                    └────────┬─────────┘
                             │ WAL 流复制
                    ┌────────▼─────────┐
                    │   PostgreSQL     │
                    │   Standby        │
                    │   (只读/故障切换) │
                    └──────────────────┘
```

- Hatchet 支持读副本：`READ_REPLICA_ENABLED=true`，分析查询走副本
- OwlClaw 的 SQLAlchemy 可配置读写分离（通过 `create_engine` 的 `execution_options`）

**Cloud**：

- 使用云托管 PostgreSQL（AWS RDS Multi-AZ / Google Cloud SQL HA / Azure Flexible Server）
- 自动故障切换，无需手动管理
- PgBouncer / Supavisor 做连接池

### 8.3 云托管方案

| 云平台 | 服务 | 特点 |
|--------|------|------|
| AWS | RDS for PostgreSQL | Multi-AZ、自动备份、pgvector 支持 |
| Google Cloud | Cloud SQL for PostgreSQL | HA、自动备份、pgvector 支持 |
| Azure | Database for PostgreSQL Flexible Server | Zone-redundant HA、pgvector 支持 |
| Supabase | Supabase Postgres | 内建 pgvector、连接池、Dashboard |
| Neon | Neon Serverless Postgres | 按需扩缩、分支、pgvector 支持 |

所有云托管方案都支持在同一实例中创建多个 database（owlclaw / hatchet / langfuse），与 Self-hosted 架构完全一致。

---

## 九、从 Self-hosted 到 Cloud 的迁移路径

### 9.1 迁移步骤

```
Step 1: 数据导出
  owlclaw db backup --output owlclaw_export.dump --format custom

Step 2: 在 Cloud 环境创建目标 database
  owlclaw db init --admin-url postgresql://admin:xxx@cloud-host:5432/postgres

Step 3: 数据导入
  owlclaw db restore --input owlclaw_export.dump \
      --database-url postgresql://owlclaw:xxx@cloud-host:5432/owlclaw

Step 4: 更新 tenant_id（从 'default' 到真实租户 ID）
  UPDATE ledger_records SET tenant_id = 'tenant_xxx' WHERE tenant_id = 'default';
  UPDATE agent_memory SET tenant_id = 'tenant_xxx' WHERE tenant_id = 'default';
  -- ... 所有表

Step 5: 启用 RLS 策略
  -- 执行 Cloud 阶段的 RLS migration

Step 6: 切换连接
  -- 更新 owlclaw.yaml 或环境变量，指向 Cloud 数据库
```

### 9.2 关键注意事项

- **tenant_id 更新是原子操作**：在事务中批量更新，确保一致性
- **RLS 策略引入是 Alembic migration**：作为正常的 schema 迁移管理
- **Hatchet 数据不需要迁移**：Hatchet 的工作流数据是临时的（任务执行完即归档），切换到 Cloud 时重新创建 Hatchet database 即可
- **向量索引需要重建**：pg_dump 导出后，HNSW/IVFFlat 索引需要在目标库重建

---

## 附录 A：init-db.sql 参考

`deploy/init-db.sql` 是 Docker 环境下的初始化脚本，`owlclaw db init` CLI 命令的功能等价物：

```sql
-- OwlClaw 数据库初始化脚本
-- 详见 docs/DATABASE_ARCHITECTURE.md

-- 1. Hatchet 独占数据库
CREATE DATABASE hatchet;
CREATE ROLE hatchet WITH LOGIN PASSWORD 'hatchet';
ALTER DATABASE hatchet OWNER TO hatchet;

-- 2. OwlClaw 业务数据库
CREATE DATABASE owlclaw;
CREATE ROLE owlclaw WITH LOGIN PASSWORD 'owlclaw';
ALTER DATABASE owlclaw OWNER TO owlclaw;

-- 3. OwlClaw 库启用 pgvector（Agent 记忆向量搜索）
\c owlclaw
CREATE EXTENSION IF NOT EXISTS vector;
```

> **注意**：生产环境请使用 `owlclaw db init` 命令并指定强密码，不要使用此脚本的默认密码。

---

## 附录 B：行业参考

OwlClaw 的数据库架构设计参考了以下开源项目的实践：

| 项目 | 路径 | 数据库策略 |
|------|------|-----------|
| **Langfuse** | MIT → Langfuse Cloud | Self-hosted: 用户自己的 PostgreSQL；Cloud: RLS 多租户 |
| **Temporal** | MIT → Temporal Cloud | Self-hosted: 单 PostgreSQL + namespace 隔离；Cloud: 托管集群 |
| **Hatchet** | MIT → Hatchet Cloud | Self-hosted: 独占 clean database；Cloud: 内建 tenant_id 多租户 |
| **Supabase** | MIT → Supabase Cloud | 每个项目一个 PostgreSQL 实例 |

---

> **文档版本**: v1.0.0
> **创建时间**: 2026-02-10
> **维护者**: yeemio
> **下次审核**: 2026-03-01
