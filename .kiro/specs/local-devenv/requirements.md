# 需求文档：local-devenv（统一本地开发环境）

## 背景

OwlClaw 依赖多个外部服务（PostgreSQL + pgvector、Hatchet、Langfuse、Redis、Kafka），
当前本地启动方式分散在 `deploy/` 下的多个 compose 文件中，步骤繁琐，且与 CI 环境不一致。
对外提供服务时，用户面对一堆零散的 Docker 组件，体验极差。

## 目标

**一条命令启动完整本地开发环境，与 CI 完全镜像。**

## 用户故事

### US-1：新开发者零摩擦上手
作为新加入的开发者，我希望执行 `docker compose up -d` 后，所有依赖服务就绪，
然后 `poetry run pytest` 全部通过，无需任何额外配置。

### US-2：本地测试与 CI 完全一致
作为开发者，我希望本地跑的测试环境（PG 版本、pgvector 版本、镜像）与 CI `test.yml` 完全相同，
不再出现"本地过了 CI 挂"的情况。

### US-3：按需启动，不强制全量
作为只用核心功能的开发者，我希望有最小化启动选项（仅 PG + pgvector），
不强制启动 Hatchet 和 Langfuse。

### US-4：对外提供服务文档清晰
作为 OwlClaw 用户，我希望文档明确说明：
- 生产只需要 PostgreSQL（pgvector），其余都是可选集成
- 本地开发一条命令搞定
- 三种部署路径（本地开发 / 自托管生产 / 云托管）各有清晰指引

### US-5：环境变量统一管理
作为开发者，我希望有完整的 `.env.example`，知道每个变量的用途、默认值和是否必填。

## 验收标准

### AC-1：统一入口
- [ ] 根目录存在 `docker-compose.dev.yml`，一条命令启动：pgvector/pgvector:pg16 + Hatchet Lite + Langfuse
- [ ] 根目录存在 `docker-compose.test.yml`，与 CI `test.yml` 的 postgres service 完全镜像
- [ ] 根目录存在 `docker-compose.minimal.yml`，仅 pgvector/pgvector:pg16（最小依赖）

### AC-2：PG 镜像统一
- [ ] 所有 compose 文件（dev/test/minimal）统一使用 `pgvector/pgvector:pg16`
- [ ] `deploy/` 下旧的 `postgres:15-alpine` compose 文件更新或标注废弃

### AC-3：本地测试命令
- [ ] `docker compose -f docker-compose.test.yml up -d` 后，`poetry run pytest tests/unit/ tests/integration/` 全部通过
- [ ] 提供 `make test` 或 `scripts/test-local.sh` 封装上述流程

### AC-4：环境变量文档
- [ ] `.env.example` 完整覆盖所有服务的环境变量，标注必填/可选/默认值
- [ ] 每个 compose 文件顶部注释说明用途和启动命令

### AC-5：部署文档
- [ ] `docs/DEVELOPMENT.md`：本地开发环境搭建（一步到位）
- [ ] `docs/DEPLOYMENT.md`：三种部署路径（本地开发 / 自托管生产 / 云托管）
- [ ] 明确说明哪些依赖是必须的，哪些是可选的

### AC-6：Langfuse 本地集成
- [ ] `docker-compose.dev.yml` 包含 Langfuse 官方镜像（不内嵌源码）
- [ ] `.env.example` 包含本地 Langfuse 的 key 配置示例

## 非功能需求

- **零侵入**：`pip install owlclaw` 不依赖 Docker，Docker 只是开发便利工具
- **幂等**：`docker compose up -d` 可反复执行，不破坏已有数据
- **Windows 兼容**：compose 文件在 Windows Docker Desktop 下可用
- **镜像版本锁定**：所有镜像使用具体版本 tag，不用 `latest`

## 范围外

- Kubernetes 部署（已有 `deploy/k8s/`，不在本 spec 范围）
- CI 流水线修改（属于 test-infra spec）
- `.langfuse/` 目录清理（属于 repo-hygiene spec）
