# 设计文档：test-infra（测试基础设施统一）

## 1. 测试分层架构

```
tests/
├── conftest.py              # 全局 fixtures（db_session、mock_hatchet 等）
├── unit/                    # 纯单元测试 — 零外部依赖
│   ├── conftest.py          # unit 层 fixtures（mock 优先）
│   └── ...
├── integration/             # 集成测试 — 需要 PostgreSQL
│   ├── conftest.py          # integration 层 fixtures（真实 DB）
│   └── ...
└── e2e/                     # 端到端测试 — 需要全量服务
    ├── conftest.py          # e2e 层 fixtures
    └── ...
```

### 1.1 分层规则

| 层 | 外部依赖 | marker | 运行命令 |
|----|---------|--------|---------|
| unit | 无 | `@pytest.mark.unit`（可省略，默认） | `pytest tests/unit/` |
| integration | PostgreSQL + pgvector | `@pytest.mark.integration` | `pytest tests/integration/` |
| e2e | 全量（PG + Hatchet + Langfuse） | `@pytest.mark.e2e` | `pytest tests/e2e/` |

### 1.2 当前违规清单（需修复）

以下 `tests/unit/` 文件依赖外部服务，需迁移或修复：
- `tests/unit/test_cli_db.py` — 依赖 PostgreSQL（需 mock 或迁移到 integration）
- `tests/unit/capabilities/test_bindings_queue_executor.py` — 依赖 Kafka（需 mock）
- `tests/unit/triggers/test_queue_idempotency.py` — 依赖 Redis（需 mock）

## 2. 外部服务 Skip 机制

### 2.1 服务可用性检测

```python
# tests/conftest.py

import socket
import pytest

def _is_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False

def pytest_configure(config):
    config.addinivalue_line("markers", "requires_postgres: needs PostgreSQL")
    config.addinivalue_line("markers", "requires_hatchet: needs Hatchet server")
    config.addinivalue_line("markers", "requires_redis: needs Redis")
    config.addinivalue_line("markers", "requires_kafka: needs Kafka")

def pytest_collection_modifyitems(config, items):
    service_checks = {
        "requires_postgres": ("localhost", 5432, "PostgreSQL not available at localhost:5432"),
        "requires_hatchet":  ("localhost", 17077, "Hatchet not available at localhost:17077"),
        "requires_redis":    ("localhost", 6379,  "Redis not available at localhost:6379"),
        "requires_kafka":    ("localhost", 9092,  "Kafka not available at localhost:9092"),
    }
    for item in items:
        for marker_name, (host, port, reason) in service_checks.items():
            if item.get_closest_marker(marker_name):
                if not _is_port_open(host, port):
                    item.add_marker(pytest.mark.skip(reason=reason))
```

### 2.2 自动标注规则

`tests/integration/` 下的所有测试自动加 `@pytest.mark.requires_postgres`（通过 `conftest.py`），
无需每个测试文件手动标注。

## 3. 共享 Fixtures 设计

### 3.1 全局 conftest.py

```python
# tests/conftest.py

@pytest.fixture(scope="session")
def db_url() -> str:
    return os.environ.get(
        "OWLCLAW_DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/owlclaw_test"
    )

@pytest.fixture
async def async_db_session(db_url):
    """每个测试一个事务，测试后回滚。"""
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSession(engine) as session:
        async with session.begin():
            yield session
            await session.rollback()
    await engine.dispose()

@pytest.fixture
def mock_hatchet_client():
    """Mock Hatchet client for unit tests."""
    with patch("owlclaw.integrations.hatchet.HatchetClient") as mock:
        mock.return_value.task.return_value = lambda f: f
        yield mock
```

### 3.2 integration/conftest.py

```python
# tests/integration/conftest.py

pytestmark = pytest.mark.requires_postgres  # 整个目录自动标注

@pytest.fixture(scope="module")
async def db_engine(db_url):
    """模块级 engine，避免每个测试重建连接池。"""
    engine = create_async_engine(db_url, echo=False)
    yield engine
    await engine.dispose()
```

## 4. 覆盖率配置

### 4.1 pyproject.toml 分层配置

```toml
[tool.coverage.run]
source = ["owlclaw"]
omit = ["tests/*", "*/migrations/*", "*/__pycache__/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "@abstractmethod",
    "raise NotImplementedError",
]
```

### 4.2 CI 分层运行

```yaml
# test.yml 中分两步运行
- name: Run unit tests
  run: poetry run pytest tests/unit/ --cov=owlclaw --cov-fail-under=90 -q

- name: Run integration tests
  run: poetry run pytest tests/integration/ --cov=owlclaw --cov-append --cov-fail-under=80 -q
```

## 5. CI test.yml 与本地对齐

CI `test.yml` 的 postgres service 配置与 `docker-compose.test.yml` 保持完全一致：

```yaml
# 两处配置完全相同
image: pgvector/pgvector:pg16
environment:
  POSTGRES_PASSWORD: postgres
  POSTGRES_DB: owlclaw_test
```

pgvector 扩展初始化：两处都执行
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```
