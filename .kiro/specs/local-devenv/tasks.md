# 任务清单：local-devenv（统一本地开发环境）

## 文档联动

- requirements: `.kiro/specs/local-devenv/requirements.md`
- design: `.kiro/specs/local-devenv/design.md`
- tasks: `.kiro/specs/local-devenv/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`

## Tasks

### Phase 1：核心 compose 文件（P0）

- [ ] **Task 1**: docker-compose.test.yml — 与 CI 完全镜像
  - [ ] 1.1 创建根目录 `docker-compose.test.yml`，使用 `pgvector/pgvector:pg16`
  - [ ] 1.2 配置 `owlclaw_test` 数据库，含 healthcheck
  - [ ] 1.3 添加 `CREATE EXTENSION IF NOT EXISTS vector;` 初始化步骤（与 CI test.yml 一致）
  - [ ] 1.4 验证：`docker compose -f docker-compose.test.yml up -d` + `poetry run pytest tests/unit/ -q` 通过
  - _Requirements: AC-1, AC-2_

- [ ] **Task 2**: docker-compose.minimal.yml — 最小依赖
  - [ ] 2.1 创建根目录 `docker-compose.minimal.yml`，使用 `pgvector/pgvector:pg16`
  - [ ] 2.2 挂载 `deploy/init-db.sql` 自动初始化 owlclaw 库
  - [ ] 2.3 配置具名 volume `owlclaw_minimal_data` 持久化数据
  - [ ] 2.4 验证：启动后 `owlclaw db status` 显示连接正常
  - _Requirements: AC-1, AC-3_

- [ ] **Task 3**: docker-compose.dev.yml — 全量开发环境
  - [ ] 3.1 创建根目录 `docker-compose.dev.yml`，包含 pgvector/pgvector:pg16
  - [ ] 3.2 集成 Hatchet Lite（锁定具体版本 tag，连接 owlclaw-db）
  - [ ] 3.3 集成 Langfuse（官方镜像，连接 owlclaw-db 的 langfuse 库）
  - [ ] 3.4 集成 Redis（`redis:7-alpine`，用于 Queue trigger 幂等存储）
  - [ ] 3.5 `deploy/init-db.sql` 扩展：增加 langfuse 数据库和用户创建
  - [ ] 3.6 所有服务配置 healthcheck
  - [ ] 3.7 顶部注释说明用途、启动命令、各服务端口
  - [ ] 3.8 验证：`docker compose -f docker-compose.dev.yml up -d` 所有服务 healthy
  - _Requirements: AC-1, AC-6_

### Phase 2：环境变量与脚本（P0）

- [ ] **Task 4**: .env.example 完整化
  - [ ] 4.1 按分区重写 `.env.example`：必填 / Hatchet / Langfuse / Redis / Kafka / 可选覆盖
  - [ ] 4.2 每个变量标注：必填/可选、默认值、说明
  - [ ] 4.3 添加本地 Langfuse key 配置示例（`http://localhost:3000`）
  - [ ] 4.4 添加 `DATABASE_URL` 和 `OWLCLAW_DATABASE_URL` 的本地默认值
  - _Requirements: AC-4, AC-5_

- [ ] **Task 5**: Makefile（开发快捷命令）
  - [ ] 5.1 创建根目录 `Makefile`，包含目标：
        `dev-up`, `dev-down`, `dev-reset`, `test-up`, `test-down`,
        `test`, `test-unit`, `test-int`, `lint`, `typecheck`
  - [ ] 5.2 每个目标添加 `## 注释`（`make help` 可读）
  - [ ] 5.3 Windows 兼容：检测 OS，提示使用 PowerShell 等价命令
  - [ ] 5.4 验证：`make help` 输出所有目标说明
  - _Requirements: AC-3_

- [ ] **Task 6**: scripts/test-local.sh + scripts/test-local.ps1
  - [ ] 6.1 创建 `scripts/test-local.sh`：启动 test compose → 等待 healthcheck → 运行 pytest → 停止
  - [ ] 6.2 创建 `scripts/test-local.ps1`：Windows 等价版本
  - [ ] 6.3 支持参数：`--unit-only`（跳过集成测试）、`--keep-up`（测试后不停止服务）
  - _Requirements: AC-3_

### Phase 3：文档（P1）

- [ ] **Task 7**: docs/DEVELOPMENT.md
  - [ ] 7.1 创建 `docs/DEVELOPMENT.md`，包含：
        前置条件、快速开始（3 步）、服务端口说明、常见问题
  - [ ] 7.2 快速开始验证：按文档步骤从零操作，`poetry run pytest` 通过
  - [ ] 7.3 Windows 特殊步骤单独说明（firewall、host.docker.internal）
  - _Requirements: AC-5_

- [ ] **Task 8**: docs/DEPLOYMENT.md
  - [ ] 8.1 创建 `docs/DEPLOYMENT.md`，包含：
        必须 vs 可选依赖表格、三种部署路径、环境变量完整参考
  - [ ] 8.2 明确说明：`pip install owlclaw` 零 Docker 依赖，Docker 只是便利工具
  - [ ] 8.3 生产路径：最小依赖（仅 PG）+ 可选组件（Hatchet/Langfuse/Redis）
  - _Requirements: AC-5_

### Phase 4：旧 compose 文件对齐（P1）

- [ ] **Task 9**: 更新 deploy/ 下旧 compose 文件
  - [ ] 9.1 `deploy/docker-compose.lite.yml`：将 `postgres:15-alpine` 替换为 `pgvector/pgvector:pg16`
  - [ ] 9.2 `deploy/docker-compose.prod.yml`：同上，并添加 pgvector 扩展初始化
  - [ ] 9.3 `deploy/docker-compose.cron.yml`：同上
  - [ ] 9.4 所有 compose 文件顶部注释统一格式（用途/命令/端口）
  - [ ] 9.5 `deploy/README.md` 更新：指向根目录 compose 文件作为首选入口
  - _Requirements: AC-2_

### Phase 5：验收（P0）

- [ ] **Task 10**: 端到端验收
  - [ ] 10.1 从干净状态（`docker compose down -v`）执行完整流程：
        `docker compose -f docker-compose.test.yml up -d` → `poetry run pytest tests/unit/ tests/integration/ -m "not e2e"` → 全部通过
  - [ ] 10.2 验证 `docker compose -f docker-compose.dev.yml up -d` 所有服务 healthy
  - [ ] 10.3 验证 `make test-unit` 不需要任何外部服务即可通过
  - [ ] 10.4 验证 `.env.example` 覆盖所有实际使用的环境变量（与代码中的 `os.environ` 对照）
  - _Requirements: AC-1, AC-2, AC-3_

## Backlog

- [ ] `owlclaw up` CLI 命令（封装 `docker compose up`，检测依赖状态）
- [ ] devcontainer 配置（`.devcontainer/devcontainer.json`）
- [ ] Kafka 本地 compose 集成（目前 Queue trigger 测试 skip Kafka 依赖）
- [ ] 镜像版本自动更新（Dependabot for Docker）

---

**维护者**: OwlClaw 核心团队
**最后更新**: 2026-02-25
