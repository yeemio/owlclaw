# owlclaw db 命令参考

数据库运维通过 `owlclaw db` 子命令完成，封装 Alembic、pg_dump、pg_restore 等工具。

## 环境变量

| 变量 | 说明 |
|------|------|
| `OWLCLAW_DATABASE_URL` | 应用数据库连接 URL（默认被多数 db 子命令使用） |
| `OWLCLAW_ADMIN_URL` | 超级用户 URL（仅 `init` 需要，用于创建 database/role） |

URL 格式：`postgresql://user:password@host:port/dbname` 或 `postgresql+asyncpg://...`。未设置时需通过 `--database-url` 传入。

## 命令概览

| 命令 | 说明 |
|------|------|
| `owlclaw db init` | 创建 owlclaw（及可选 hatchet）database、role、pgvector 扩展 |
| `owlclaw db migrate` | 执行 Alembic 迁移（升级到 head 或指定版本） |
| `owlclaw db status` | 查看连接、版本、扩展、表统计、迁移状态 |
| `owlclaw db revision` | 生成新迁移脚本（autogenerate 或空模板） |
| `owlclaw db rollback` | 回滚迁移（一步、多步或到指定版本） |
| `owlclaw db backup` | 使用 pg_dump 备份数据库 |
| `owlclaw db restore` | 从备份恢复（psql/pg_restore） |
| `owlclaw db check` | 健康检查（连接、迁移、pgvector、池、磁盘、慢查询） |

---

## owlclaw db init

在宿主 PostgreSQL 上创建 owlclaw database、role 及 pgvector 扩展；可选创建 hatchet database/role。

```bash
# 使用环境变量（需 OWLCLAW_ADMIN_URL）
owlclaw db init

# 指定 admin URL，随机生成 owlclaw 密码
owlclaw db init --admin-url postgresql://postgres@localhost:5432/postgres

# 仅创建 owlclaw，不创建 hatchet
owlclaw db init --skip-hatchet --dry-run
```

| 选项 | 说明 |
|------|------|
| `--admin-url` | 超级用户连接 URL |
| `--owlclaw-password` | 指定 owlclaw 角色密码（默认随机） |
| `--hatchet-password` | 指定 hatchet 角色密码（默认随机） |
| `--skip-hatchet` | 不创建 hatchet database/role |
| `--dry-run` | 仅打印将要执行的操作，不执行 |

---

## owlclaw db migrate

执行 Alembic 升级到指定版本（默认 `head`）。

```bash
owlclaw db migrate
owlclaw db migrate --target head
owlclaw db migrate --dry-run   # 仅显示当前版本与 heads，不执行
```

| 选项 | 说明 |
|------|------|
| `--target`, `-t` | 目标版本，默认 `head` |
| `--database-url` | 覆盖 OWLCLAW_DATABASE_URL |
| `--dry-run` | 不执行，仅显示待执行迁移 |

---

## owlclaw db status

显示数据库连接、服务器版本、扩展、表数、总行数、磁盘占用、当前迁移版本及待执行数量。

```bash
owlclaw db status
```

输出为 Rich 表格。需设置 `OWLCLAW_DATABASE_URL` 或 `--database-url`。

---

## owlclaw db revision

生成新的 Alembic 迁移文件。支持从模型自动生成或空模板。

```bash
# 根据模型变更自动生成（需能连上数据库）
owlclaw db revision -m "add_user_table"

# 仅生成空迁移
owlclaw db revision --empty -m "manual_change"
```

| 选项 | 说明 |
|------|------|
| `-m`, `--message` | 修订说明（autogenerate 时必填） |
| `--empty` | 生成空迁移，不扫描模型 |
| `--database-url` | 覆盖 OWLCLAW_DATABASE_URL |

生成后若检测到 DROP TABLE / DROP COLUMN 会输出警告。

---

## owlclaw db rollback

回滚迁移。可回滚一步、多步或到指定版本。

```bash
# 回滚一步
owlclaw db rollback -y

# 回滚到 base
owlclaw db rollback --target base -y

# 回滚 2 步
owlclaw db rollback --steps 2 -y

# 仅查看将要回滚的版本，不执行
owlclaw db rollback --dry-run
```

| 选项 | 说明 |
|------|------|
| `-t`, `--target` | 目标版本（如 `base` 或 revision id） |
| `-s`, `--steps` | 回滚步数（与 `--target` 二选一） |
| `--database-url` | 覆盖 OWLCLAW_DATABASE_URL |
| `--dry-run` | 仅列出将回滚的版本 |
| `-y`, `--yes` | 跳过确认提示 |

---

## owlclaw db backup

使用 pg_dump 备份数据库。需本机已安装 PostgreSQL 客户端。

```bash
owlclaw db backup -o backup.sql
owlclaw db backup -o backup.dump -F custom
owlclaw db backup -o schema.sql --schema-only
```

| 选项 | 说明 |
|------|------|
| `-o`, `--output` | 输出文件路径（必填） |
| `-F`, `--format` | `plain`（SQL）或 `custom`（pg_restore 格式），默认 plain |
| `--schema-only` | 仅备份 schema |
| `--data-only` | 仅备份数据（与 `--schema-only` 互斥） |
| `--database-url` | 覆盖 OWLCLAW_DATABASE_URL |
| `-v`, `--verbose` | 显示详细进度 |

若输出文件已存在会询问是否覆盖。执行超过 2 秒会显示进度提示。

---

## owlclaw db restore

从备份文件恢复。自动识别 SQL 与 custom 格式。

```bash
owlclaw db restore -i backup.sql -y
owlclaw db restore -i backup.dump --clean -y
```

| 选项 | 说明 |
|------|------|
| `-i`, `--input` | 备份文件路径（必填） |
| `--clean` | 恢复前丢弃已有对象（仅 pg_restore 格式生效） |
| `--database-url` | 覆盖 OWLCLAW_DATABASE_URL |
| `-y`, `--yes` | 跳过确认提示 |
| `-v`, `--verbose` | 显示详细进度 |

目标库非空时会警告；恢复成功后会输出表数与总行数。

---

## owlclaw db check

运行健康检查：连接延迟、迁移是否最新、pgvector、连接池使用率、磁盘占用、慢查询（若启用 pg_stat_statements）。

```bash
owlclaw db check
owlclaw db check -v
```

| 选项 | 说明 |
|------|------|
| `--database-url` | 覆盖 OWLCLAW_DATABASE_URL |
| `-v`, `--verbose` | 显示每项检查的进度 |

输出总体状态：`HEALTHY`、`HEALTHY (N warnings)` 或 `UNHEALTHY`。存在 ERROR 时退出码为 1。

---

## 常见问题与故障排除

### 未设置 OWLCLAW_DATABASE_URL 时报错

多数 db 子命令需要数据库 URL。请设置环境变量或使用 `--database-url`：

```bash
export OWLCLAW_DATABASE_URL="postgresql://user:pass@localhost:5432/owlclaw"
owlclaw db status
```

### pg_dump / pg_restore / psql 未找到

backup、restore 依赖 PostgreSQL 客户端。请安装：

- **Ubuntu/Debian**: `apt install postgresql-client`
- **macOS**: `brew install postgresql`
- **Windows**: 从 [PostgreSQL 官网](https://www.postgresql.org/download/windows/) 安装并确保 `bin` 在 PATH 中

### 回滚或恢复时确认提示

使用 `-y` / `--yes` 可跳过交互确认（脚本或 CI 中常用）：

```bash
owlclaw db rollback -y
owlclaw db restore -i backup.sql -y
```

### Ctrl+C 中断

按 Ctrl+C 会以退出码 130 优雅退出；进行中的 DB 操作会随进程结束而终止，连接由引擎清理。

### 健康检查中 pgvector 或 Slow queries 为 N/A

- **pgvector**：若未安装扩展，检查项会显示 WARN。在目标 database 中执行 `CREATE EXTENSION vector;`（需先 `owlclaw db init` 或手动创建库）。
- **Slow queries**：依赖 `pg_stat_statements` 扩展。未启用时该项显示 "N/A (pg_stat_statements not enabled)"，不影响其他检查。

### 迁移相关

- 迁移脚本位于 `migrations/versions/`，由 `owlclaw db revision` 生成。
- 设计文档与规范见 [DATABASE_ARCHITECTURE.md](../DATABASE_ARCHITECTURE.md)。
