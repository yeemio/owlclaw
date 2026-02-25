# 需求文档：test-infra（测试基础设施统一）

## 背景

当前测试存在以下问题：
1. **本地与 CI 环境不一致**：本地 compose 用 `postgres:15-alpine`，CI 用 `pgvector/pgvector:pg16`
2. **测试分层不清晰**：`tests/unit/` 下混有需要 DB 的测试，`pytest -m unit` 无法独立运行
3. **外部服务依赖隐式**：需要 Hatchet/Kafka/Redis 的测试没有统一的 skip 机制，
   缺少外部服务时报错而非优雅跳过
4. **集成测试 fixtures 重复**：多个测试文件各自创建 DB 连接，没有共享 fixture
5. **覆盖率目标未分层**：单元测试应 ≥ 90%，集成测试另算，当前混在一起

## 目标

**测试分层清晰、本地/CI 完全一致、外部依赖优雅降级。**

## 用户故事

### US-1：无外部服务也能跑单元测试
作为开发者，我希望 `poetry run pytest tests/unit/ -m unit` 不需要任何 Docker 服务，
在任何机器上都能立即运行并通过。

### US-2：集成测试优雅跳过
作为开发者，我希望缺少 PostgreSQL 时，集成测试自动 skip 并给出清晰提示，
而不是报错 `connection refused`。

### US-3：本地一条命令跑完整测试
作为开发者，我希望 `make test` 自动启动所需服务、运行测试、输出覆盖率报告。

### US-4：CI 与本地完全镜像
作为开发者，我希望 CI `test.yml` 的 postgres service 配置与
本地 `docker-compose.test.yml` 完全相同（同镜像、同版本、同初始化步骤）。

### US-5：测试覆盖率分层报告
作为项目维护者，我希望 CI 输出分层覆盖率：
单元测试覆盖率 ≥ 90%，整体覆盖率 ≥ 80%。

## 验收标准

### AC-1：测试分层严格
- [ ] `tests/unit/` 下所有测试不依赖任何外部服务（DB/Hatchet/Kafka/Redis）
- [ ] `tests/integration/` 下所有测试标注 `@pytest.mark.integration`
- [ ] `tests/e2e/` 下所有测试标注 `@pytest.mark.e2e`
- [ ] `poetry run pytest tests/unit/ --co -q` 输出的测试全部可在无服务环境运行

### AC-2：外部服务 skip 机制
- [ ] 实现 `pytest_configure` + `pytest_collection_modifyitems`：
      检测 DB/Hatchet/Kafka/Redis 可用性，不可用时自动 skip 对应测试
- [ ] skip 信息清晰：`SKIP [reason: PostgreSQL not available at localhost:5432]`
- [ ] 单元测试不受 skip 机制影响（永远运行）

### AC-3：共享 fixtures
- [ ] `tests/conftest.py` 提供：`db_session`、`async_db_session`、`test_app` fixtures
- [ ] DB fixtures 使用事务回滚（每个测试后自动回滚，不污染数据）
- [ ] Hatchet mock fixture：`mock_hatchet_client`

### AC-4：CI 与本地镜像
- [ ] `.github/workflows/test.yml` 的 postgres service 与 `docker-compose.test.yml` 完全一致
- [ ] CI 中 pgvector 扩展初始化步骤与本地一致

### AC-5：覆盖率分层
- [ ] `pyproject.toml` 配置分层覆盖率：`--cov-fail-under=90`（unit）、`--cov-fail-under=80`（overall）
- [ ] CI 输出分层覆盖率报告（unit 和 integration 分开）

### AC-6：测试文档
- [ ] `docs/TESTING.md`：测试分层说明、如何运行各层测试、如何添加新测试

## 非功能需求

- 单元测试运行时间 < 60 秒（无外部服务）
- 集成测试运行时间 < 5 分钟（有 PG）
- 测试数据库与开发数据库完全隔离（不同数据库名）

## 范围外

- compose 文件创建（属于 local-devenv spec）
- `.langfuse/` 清理（属于 repo-hygiene spec）
- E2E 测试实现（已有，不在本 spec 范围）
