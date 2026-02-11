# Hatchet：不依赖 Docker 能做什么 / Docker 的作用

## 1. 不依赖 Docker 我们能达到什么效果

在**不启动 Docker、不运行 Hatchet Server** 的情况下，当前可以做到：

| 能力 | 说明 |
|------|------|
| **单元测试全通过** | 所有不依赖 Hatchet 的测试（app、db、cli、registry、skills、hatchet 配置/装饰器/错误路径等）均可本地通过。 |
| **Hatchet 客户端逻辑** | `HatchetConfig`、`HatchetClient`、`@client.task()` / `@client.durable_task()` 的注册与参数校验、`schedule_task` / `run_task_now` / `cancel_task` / `get_task_status` 的**校验与错误路径**（如未连接、未注册任务）均可测试。 |
| **Mock 运行** | 在**已 connect** 且拿到 SDK 的 workflow 对象后，可用 `standalone.aio_mock_run({})` 在**本进程内**执行任务逻辑，**不经过** Hatchet Server。适合单机验证任务代码、无需 Server。 |
| **数据库与 CLI** | `owlclaw db init/migrate/status`、本机 PostgreSQL 建库与迁移、Alembic 等，均不依赖 Docker。 |

**做不到的（需要 Hatchet Server / Docker）：**

- 真正的**持久化定时**（`ctx.aio_sleep_for` 跨进程、跨重启的持久化）
- **Cron 触发**、**延迟调度**、**任务队列**的服务器端行为
- 多进程 / 多机下的**任务分发与执行**
- 集成测试中「连上真实 Hatchet、跑真实任务」的那几条用例（无 Server 时会自动 **skip**）

总结：不依赖 Docker 时，可以完成**开发、单测、配置与客户端 API 校验、以及用 mock 跑任务逻辑**；**持久化、调度、队列、E2E** 需要 Hatchet Server（通常用 Docker 跑）。

---

## 2. Docker 的作用

Docker 在这里主要用来**跑 Hatchet 依赖的服务**，而不是跑业务代码本身：

| 作用 | 说明 |
|------|------|
| **提供 Hatchet Server（Hatchet Lite）** | 一个开箱即用的任务队列 + 调度服务（gRPC + 可选 Web UI），支持持久化执行、Cron、延迟任务。 |
| **可选：提供 PostgreSQL** | 用 `deploy/docker-compose.lite.yml` 时，会顺带起一个 Postgres 容器，并执行 `init-db.sql` 创建 `hatchet` / `owlclaw` 两库，省去本机装 Postgres 的步骤。 |
| **环境一致** | 团队/CI 用同一镜像，避免「本机能跑、别人不能跑」的问题。 |
| **拿到 HATCHET_API_TOKEN** | Hatchet Lite 启动后，可通过 Web UI（如 http://localhost:8888）登录并创建 tenant/token，或通过容器内 `hatchet-admin token create` 得到 token，供 `HATCHET_API_TOKEN` 使用。 |

不用 Docker 时，需要自己在本机安装并启动 PostgreSQL（以及可选 RabbitMQ），并自行部署 Hatchet 二进制或从源码跑 Hatchet Lite，复杂度更高；用 Docker 可以一条命令起 Postgres + Hatchet Lite。

---

## 3. Docker 已启动后：搭建 Hatchet

### 方案 A：一键启动（Postgres + Hatchet 都用 Docker）

在仓库根目录执行：

```bash
docker compose -f deploy/docker-compose.lite.yml up -d
```

- 会启动 **owlclaw-db**（Postgres）和 **hatchet-lite**。
- 若出现 `failed size validation` 等拉取 postgres 镜像失败，用方案 B。

### 方案 B：本机已有 Postgres（或 Postgres 镜像拉取失败时）

1. **建库**（二选一）  
   - 使用 CLI：`owlclaw db init --admin-url postgresql://postgres:你的密码@localhost:5432/postgres`  
   - 或执行脚本：`psql -U postgres -f deploy/init-db.sql`

2. **只启动 Hatchet Lite 容器**  
   ```bash
   docker compose -f deploy/docker-compose.lite.hatchet-only.yml up -d
   ```

3. **获取 API Token**  
   - 打开 **http://localhost:8888**，用默认账号登录：`admin@example.com` / `Admin123!!`  
   - 在 UI 里创建 tenant，在设置里创建或复制 **Client Token**  
   - 或进入容器执行：  
     `docker compose -f deploy/docker-compose.lite.hatchet-only.yml exec hatchet-lite /hatchet-admin token create --config /config`  
     （具体参数以 Hatchet 文档为准，如需 `--tenant-id` 可从 UI 查看）

4. **跑集成测试**  
   - 在仓库根目录配置 `.env`（复制 `.env.example`），填 `HATCHET_API_TOKEN` 和 `HATCHET_SERVER_URL=http://localhost:17077`（本 compose 为 17077）；pytest 会自动加载。
   - `poetry run pytest tests/integration/test_hatchet_integration.py -v`  
   - 其中 `test_hatchet_durable_task_aio_sleep_for_mock` 在 mock_run 下为 **SKIP**（需真实 Worker）；完成 7.2.3/7.2.4 后需用真实 Worker 跑通，见 `SPEC_TASKS_SCAN.md` 与 `integrations-hatchet/tasks.md`。

当前若本机**没有**运行中的 Postgres、且**没有**建好 `hatchet` 库，仅启动 `hatchet-only` 会因连不上库而退出；需先完成方案 B 的步骤 1 再执行步骤 2。
