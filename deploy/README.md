# 部署说明

**数据库架构**：复用宿主 PostgreSQL，组件间 database 级隔离。创建两个 database：**hatchet**（Hatchet 独占）、**owlclaw**（OwlClaw 业务）。详见 `docs/DATABASE_ARCHITECTURE.md`。Compose 需从**仓库根目录**执行。

---

## 推荐：Docker 正常时一键启动

```bash
# 在仓库根目录
docker compose -f deploy/docker-compose.lite.yml up -d
```

会启动 `owlclaw-db`（Postgres + 自动执行 `init-db.sql` 建 hatchet/owlclaw 两库）和 `hatchet-lite`。若本机 Docker 拉取 postgres 镜像时报错（如 `failed size validation`），用下面「本机 Postgres + 仅 Hatchet」方案。

---

## Docker 跑不起来时：本机 Postgres + 仅 Hatchet

当 postgres 镜像一直拉取/提交失败时，用本机已有的 PostgreSQL，只让 Docker 跑 Hatchet Lite。

### 步骤 1：本机安装并启动 PostgreSQL 15

- **Windows**：安装 [PostgreSQL](https://www.postgresql.org/download/windows/)，确保服务运行、`psql` 在 PATH 中。
- **WSL**：`sudo apt update && sudo apt install -y postgresql-15`，然后 `sudo service postgresql start`。

### 步骤 2：用项目里的 init 脚本建库（hatchet + owlclaw）

在**仓库根目录**执行（需能以超级用户连到本机 Postgres）：

```bash
# 默认连 localhost:5432，用户 postgres；有密码时可用 PGPASSWORD=xxx
psql -U postgres -f deploy/init-db.sql
```

会创建 database `hatchet`（用户 hatchet/密码 hatchet）和 `owlclaw`（用户 owlclaw/密码 owlclaw），并在 owlclaw 库启用 pgvector。

### 步骤 3：只启动 Hatchet Lite 容器（不拉 postgres 镜像）

```bash
docker compose -f deploy/docker-compose.lite.hatchet-only.yml up -d
```

Hatchet Lite 会通过 `host.docker.internal:5432` 连到本机 Postgres 的 **hatchet** 库。验证：`curl -s http://localhost:7077/health` 或访问 Hatchet 文档中的健康检查地址。

### 小结

| 步骤 | 命令 |
|------|------|
| 1. 本机 Postgres 已运行 | — |
| 2. 建库 | `psql -U postgres -f deploy/init-db.sql` |
| 3. 起 Hatchet | `docker compose -f deploy/docker-compose.lite.hatchet-only.yml up -d` |

---

## Compose 文件说明

| 文件 | 用途 |
|------|------|
| `docker-compose.lite.yml` | 开发：owlclaw-db + Hatchet Lite（需能拉取 postgres 镜像） |
| `docker-compose.lite.hatchet-only.yml` | 仅 Hatchet Lite，连本机已建好的 hatchet 库 |
| `docker-compose.prod.yml` | 生产：owlclaw-db + Hatchet Engine |

## 若仍想修复 Docker 拉取 postgres 失败

- Docker Desktop → Troubleshoot → **Clean / Purge data**，或 **Reset to factory defaults**（会清空本地镜像与容器）。
- 将 Docker 数据目录加入 Windows 安全中心的排除项。
