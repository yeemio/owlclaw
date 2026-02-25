# 任务清单：test-infra（测试基础设施统一）

## 文档联动

- requirements: `.kiro/specs/test-infra/requirements.md`
- design: `.kiro/specs/test-infra/design.md`
- tasks: `.kiro/specs/test-infra/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`

## Tasks

### Phase 1：外部服务 Skip 机制（P0）

- [x] **Task 1**: pytest skip 机制实现
  - [x] 1.1 在 `tests/conftest.py` 实现 `_is_port_open()` 服务可用性检测
  - [x] 1.2 实现 `pytest_collection_modifyitems`：检测 PG/Hatchet/Redis/Kafka，不可用时 skip
  - [x] 1.3 注册 markers：`requires_postgres`、`requires_hatchet`、`requires_redis`、`requires_kafka`
  - [x] 1.4 验证：无 PG 时 `pytest tests/integration/ -v` 显示 SKIP 而非 ERROR
  - _Requirements: AC-2_

- [x] **Task 2**: integration/ 目录自动标注
  - [x] 2.1 在 `tests/integration/conftest.py` 添加 `pytestmark = pytest.mark.requires_postgres`
  - [x] 2.2 移除各 integration 测试文件中手动的 `skipif` 逻辑（统一到 conftest）
  - [x] 2.3 验证：`pytest tests/integration/ --co -q` 显示所有测试带 `requires_postgres` marker
  - _Requirements: AC-2_

### Phase 2：单元测试纯净化（P0）

- [x] **Task 3**: 修复 unit 层外部依赖违规
  - [x] 3.1 `tests/unit/test_cli_db.py`：将 DB 连接调用替换为 mock，或迁移到 `tests/integration/`
  - [x] 3.2 `tests/unit/capabilities/test_bindings_queue_executor.py`：mock Kafka 连接
  - [x] 3.3 `tests/unit/triggers/test_queue_idempotency.py`：mock Redis 连接
  - [x] 3.4 验证：`poetry run pytest tests/unit/ -q`（无任何外部服务）全部通过，0 skip  
    - 当前状态（2026-02-25）：`1530 passed, 0 skipped`
  - _Requirements: AC-1_

- [ ] **Task 4**: 验证 unit 测试零外部依赖
  - [x] 4.1 在 CI lint job 中添加步骤：`pytest tests/unit/ -q --tb=short`（不启动任何 service）
  - [ ] 4.2 确认 unit 测试运行时间 < 60 秒  
    - 当前阻塞（2026-02-25）：本地实测 `tests/unit` 耗时约 `353s`（`1530 passed, 0 skipped`），需后续做用例分层/性能优化
  - _Requirements: AC-1_

### Phase 3：共享 Fixtures（P1）

- [x] **Task 5**: 全局 conftest.py 重构
  - [x] 5.1 添加 `db_url` fixture（从环境变量读取，默认 `localhost:5432/owlclaw_test`）
  - [x] 5.2 添加 `async_db_session` fixture（事务回滚模式）
  - [x] 5.3 添加 `mock_hatchet_client` fixture（patch `owlclaw.integrations.hatchet`）
  - [x] 5.4 保留现有 `app` fixture，确保向后兼容
  - _Requirements: AC-3_

- [x] **Task 6**: integration/conftest.py 模块级 fixtures
  - [x] 6.1 添加 `db_engine` fixture（scope="module"，避免每个测试重建连接池）
  - [x] 6.2 添加 `run_migrations` fixture（scope="session"，确保 schema 最新）
  - [x] 6.3 验证：集成测试之间数据不互相污染（事务回滚有效）  
    - 验证记录（2026-02-25）：在 `docker-compose.test.yml`（`OWLCLAW_PG_PORT=45432`）环境下执行 `poetry run pytest tests/integration/test_integration_fixtures.py -q`，结果 `2 passed`，确认隔离回滚生效
  - _Requirements: AC-3_

### Phase 4：覆盖率分层（P1）

- [x] **Task 7**: pyproject.toml 覆盖率配置
  - [x] 7.1 配置 `[tool.coverage.run]`：source、omit、branch=true
  - [x] 7.2 配置 `[tool.coverage.report]`：exclude_lines（TYPE_CHECKING、abstractmethod 等）
  - [x] 7.3 配置 `[tool.coverage.html]`：输出目录 `htmlcov/`
  - _Requirements: AC-5_

- [x] **Task 8**: CI test.yml 分层运行
  - [x] 8.1 将 CI test job 拆分为两步：unit（`--cov-fail-under=90`）+ integration（`--cov-fail-under=80`）
  - [x] 8.2 integration 步骤使用 `--cov-append` 累加覆盖率
  - [x] 8.3 验证：CI 输出分层覆盖率报告
  - _Requirements: AC-4, AC-5_

### Phase 5：CI 与本地镜像对齐（P0）

- [ ] **Task 9**: CI test.yml 与 docker-compose.test.yml 对齐
  - [x] 9.1 确认 CI `test.yml` postgres service 使用 `pgvector/pgvector:pg16`（已对齐）
  - [x] 9.2 确认 CI pgvector 初始化步骤与 `docker-compose.test.yml` 完全一致（CI 改为复用 `deploy/init-test-db.sql`）
  - [x] 9.3 将 CI 中 `POSTGRES_DB: owlclaw_test` 与本地 compose 对齐（已对齐）
  - [ ] 9.4 验证：本地 `make test-int` 与 CI 测试结果一致（同 pass/skip/fail）  
    - 当前阻塞（2026-02-25）：本机 Docker Engine 未运行，且无 `make` 命令，暂无法做本地对齐验收
  - _Requirements: AC-4_

### Phase 6：文档（P1）

- [x] **Task 10**: docs/TESTING.md
  - [x] 10.1 创建 `docs/TESTING.md`，包含：
        测试分层说明、各层运行命令、如何添加新测试、外部服务 skip 说明
  - [x] 10.2 添加测试矩阵表格（哪些测试需要哪些服务）
  - [x] 10.3 覆盖率目标说明（unit ≥ 90%，overall ≥ 80%）
  - _Requirements: AC-6_

### Phase 7：验收（P0）

- [ ] **Task 11**: 端到端验收
  - [ ] 11.1 无外部服务：`poetry run pytest tests/unit/ -q` → 全部通过，0 skip，< 60s
  - [ ] 11.2 有 PG：`poetry run pytest tests/unit/ tests/integration/ -q` → unit 全过，integration 按可用性 pass/skip
  - [ ] 11.3 CI 运行：所有 matrix（3.10/3.11/3.12）通过
  - [ ] 11.4 覆盖率：unit ≥ 90%，overall ≥ 80%
  - _Requirements: AC-1, AC-2, AC-3, AC-4, AC-5_

## Backlog

- [ ] pytest-xdist 并行测试（加速 CI）
- [ ] 测试数据工厂（factory_boy 或 polyfactory）
- [ ] Kafka 本地 mock（用 `aiokafka` mock 替代真实 Kafka）
- [ ] 测试报告 HTML 输出（`pytest-html`）

---

**维护者**: OwlClaw 核心团队
**最后更新**: 2026-02-25
