# 部署说明

**架构真源**：所有数据库与部署方式以 **`docs/DATABASE_ARCHITECTURE.md`** 为准。禁止在未对齐该文档的情况下新增数据库或变更隔离方式。

**原则**：复用**宿主已有 PostgreSQL**（本机 Postgres），在同一实例上创建 **hatchet** / **owlclaw** 两个独立 database，组件 database 级隔离。Hatchet Server 仅连 **hatchet** 库，OwlClaw 应用仅连 **owlclaw** 库。

---

## 标准路径：本机 Postgres + Hatchet Lite 容器

适用于：本机已安装并运行 PostgreSQL（与 `DATABASE_ARCHITECTURE.md` §2.1 Self-hosted 一致）。

### 步骤 1：在本机 Postgres 上建库

任选一种方式（效果一致，与架构 §5.2 对齐）：

**方式 A：OwlClaw CLI（推荐）**

```bash
# 仓库根目录执行；将 你的密码 换成本机 postgres 用户密码
owlclaw db init --admin-url postgresql://postgres:你的密码@localhost:5432/postgres
```

**方式 B：init 脚本（需 psql 在 PATH）**

```bash
psql -U postgres -h localhost -f deploy/init-db.sql
```

若方式 A 出现连接重置（如 Windows 下 WinError 64），可再次执行 `owlclaw db init`（幂等），或改用方式 B。建库规范见 `docs/DATABASE_ARCHITECTURE.md` §5。

以上任一方式会创建：

- **database hatchet**，用户 `hatchet` / 密码 `hatchet`（Hatchet Server 专用）
- **database owlclaw**，用户 `owlclaw` / 密码 `owlclaw`，并启用 **pgvector**

### 步骤 2：启动 Hatchet Lite（仅容器，连本机 hatchet 库）

```bash
# 仓库根目录
docker compose -f deploy/docker-compose.lite.hatchet-only.yml up -d
```

Hatchet Lite 通过 `host.docker.internal:5432` 连接本机 Postgres 的 **hatchet** 库。

- **hatchet 用户密码**：compose 使用 `hatchet:hatchet`。若你曾用 `owlclaw db init` 建库（随机密码），需先改回：  
  `psql -U postgres -h 127.0.0.1 -c "ALTER ROLE hatchet PASSWORD 'hatchet';"`
- **hatchet 库时区**：Hatchet 要求 UTC。若本机 Postgres 为其他时区，需执行：  
  `psql -U postgres -h 127.0.0.1 -c "ALTER DATABASE hatchet SET TIMEZONE='UTC';"`
- **本 compose 的 gRPC 端口**：主机为 **17077**（避免与镜像内 7077 冲突）。跑集成测试或示例时设置：  
  `export HATCHET_SERVER_URL=http://localhost:17077`（`HatchetConfig` 会优先使用该环境变量）。

若 Hatchet 容器连不上本机 Postgres（日志出现 `goose: failed to open DB: context deadline exceeded`），需让 Postgres 接受来自 Docker 的 TCP 连接，按下一小节配置后再执行步骤 2。

#### 让本机 Postgres 可被 Docker 访问（listen_addresses + pg_hba.conf）

以下为**推荐做法**：在本机 Postgres 上开放 TCP 监听并允许来自 Docker 的认证连接，然后重启 Postgres。配置一次即可，与 `owlclaw db init` / `init-db.sql` 无关。

1. **确认 Postgres 数据目录**  
   - Windows：通常在 `C:\Program Files\PostgreSQL\<版本>\data`  
   - Linux/macOS：`pg_config --sysconfdir` 或 `data_directory`（`SHOW data_directory;`）

2. **修改 `postgresql.conf`（数据目录下）**  
   - 将 `listen_addresses` 设为可被 Docker 访问的地址：  
     - 开发/单机：`listen_addresses = '*'` 或 `listen_addresses = '0.0.0.0'`  
     - 若仅允许本机+Docker 网段：`listen_addresses = 'localhost,172.17.0.1'`（Linux Docker 默认网桥网关）或保留 `localhost` 并在 pg_hba 中放行 Docker 网段  
   - 修改后需**重启 Postgres 服务**。

3. **修改 `pg_hba.conf`（同一数据目录）**  
   - 在文件末尾增加一行，允许来自 Docker 的 IPv4 连接并使用密码认证（md5 或 scram-sha-256，与服务器配置一致）：  
     - 开发/单机：`host    all    all    0.0.0.0/0    scram-sha-256`（或 `md5`，视 `postgresql.conf` 中 `password_encryption` 而定）  
     - 更小范围：`host    all    all    172.17.0.0/16    scram-sha-256`（仅 Docker 默认网桥）  
   - **重新加载**即可生效（无需重启）：`pg_ctl reload` 或 `SELECT pg_reload_conf();`，或重启 Postgres。

4. **防火墙**  
   - **Windows**：以**管理员**身份运行一次，放行 TCP 5432 入站：  
     ```powershell
     # 在仓库根目录执行（需管理员 PowerShell）
     .\deploy\windows-firewall-5432.ps1
     ```  
     或手动：`netsh advfirewall firewall add rule name="PostgreSQL 5432" dir=in action=allow protocol=TCP localport=5432`  
   - Linux：`sudo ufw allow 5432/tcp`（或等价 iptables 规则）后 `ufw reload`。

5. **自检**  
   - 本机：`psql -U postgres -h 127.0.0.1 -p 5432 -d hatchet -c "SELECT 1;"`  
   - 容器内（若 Docker 已装）：`docker run --rm postgres:15 psql -U hatchet -h host.docker.internal -p 5432 -d hatchet -c "SELECT 1;"`（密码按你建库时设置的，如 `hatchet`）。

以上完成后，再执行 **步骤 2** 启动 Hatchet 容器。

### 步骤 3：获取 API Token

- 打开 **http://localhost:8888**，登录 `admin@example.com` / `Admin123!!`
- 在 UI 中创建 tenant，在设置中复制 **Client Token**
- 写入本地 **`.env`**（仓库根目录，已 gitignore）：复制 `.env.example` 为 `.env`，填上 `HATCHET_API_TOKEN` 和 `HATCHET_SERVER_URL=http://localhost:17077`。跑集成测试时会自动加载 `.env`。

### 步骤 4：验证

```bash
# 集成测试（需已设置 HATCHET_API_TOKEN）
poetry run pytest tests/integration/test_hatchet_integration.py -v
```

---

## 可选：Docker 同时跑 Postgres 时

若希望 Postgres 也由 Docker 提供（非本机已有实例），可使用：

```bash
docker compose -f deploy/docker-compose.lite.yml up -d
```

- 会启动 **owlclaw-db**（Postgres 容器 + 自动执行 `init-db.sql`）和 **hatchet-lite**
- 若拉取 postgres 镜像失败（如 `failed size validation`），请使用上文**标准路径**（本机 Postgres + hatchet-only）

---

## Compose 文件说明

| 文件 | 用途 | 依赖 |
|------|------|------|
| `docker-compose.lite.hatchet-only.yml` | **推荐（当前）**。仅 Hatchet Lite，连本机已建好的 hatchet 库 | 本机 Postgres + 已执行步骤 1 |
| `docker-compose.lite.yml` | 备用。Postgres + Hatchet Lite 均由 Docker 提供 | 无（需能拉取 postgres 镜像） |
| `docker-compose.prod.yml` | 生产（旧入口，待与根目录 compose 统一） | 见文件内说明 |
| `docker-compose.cron.yml` | Cron 一体化（旧入口，待与根目录 compose 统一） | Docker 构建环境 |

> 说明：根目录 `docker-compose.dev.yml` / `docker-compose.test.yml` / `docker-compose.minimal.yml`
> 由 `local-devenv` spec 统一收敛后作为首选入口；本目录 compose 将保留为兼容入口。

---

## 小结（标准路径）

| 步骤 | 命令 |
|------|------|
| 1. 本机 Postgres 已运行 | — |
| 2. 建库 | `owlclaw db init --admin-url postgresql://postgres:xxx@localhost:5432/postgres` 或 `psql -U postgres -h localhost -f deploy/init-db.sql` |
| 3. 起 Hatchet | `docker compose -f deploy/docker-compose.lite.hatchet-only.yml up -d` |
| 4. 拿 Token | 打开 http://localhost:8888，登录后复制 Client Token，设 `HATCHET_API_TOKEN` |

所有数据库相关约定（database 名、role、pgvector、迁移职责）以 **`docs/DATABASE_ARCHITECTURE.md`** 为准。

---

## 故障排查

- **`owlclaw db init` 报 WinError 64 / connection closed**  
  会自动用 psycopg2 同步后备重试；若仍失败，请用方式 B：`psql -U postgres -h localhost -f deploy/init-db.sql`（需 psql 在 PATH）。

- **Hatchet 容器启动后马上退出，日志有 `goose: failed to open DB: context deadline exceeded`**  
  容器连不上本机 Postgres。请按上文 **「让本机 Postgres 可被 Docker 访问」** 配置 `listen_addresses`、`pg_hba.conf` 与防火墙；若本机不便开放 5432，可改用 `docker-compose.lite.yml`（Postgres 与 Hatchet 均在 Docker 内、同网段）。
