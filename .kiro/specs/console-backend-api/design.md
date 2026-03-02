# Design: Console Backend API

> **目标**：实现 Console REST API 后端，通过查询契约层与底层模块解耦  
> **状态**：设计完成  
> **最后更新**：2026-03-02

---

## 1. 架构设计

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│  Console Frontend (React SPA)                                    │
│  TypeScript types auto-generated from OpenAPI Schema             │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP / WebSocket
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  owlclaw/web/api/                                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ overview  │ │ agents   │ │governance│ │ triggers │  ...      │
│  │ _router   │ │ _router  │ │ _router  │ │ _router  │           │
│  └─────┬────┘ └─────┬────┘ └─────┬────┘ └─────┬────┘           │
│        │             │            │             │                 │
│        └─────────────┴────────────┴─────────────┘                │
│                          │                                        │
│                  depends on Protocol only                         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│  owlclaw/web/contracts.py                                        │
│  ┌─────────────────┐ ┌─────────────────┐ ┌──────────────────┐  │
│  │OverviewProvider  │ │GovernanceProvider│ │TriggersProvider  │  │
│  │  (Protocol)      │ │  (Protocol)      │ │  (Protocol)      │  │
│  └─────────────────┘ └─────────────────┘ └──────────────────┘  │
│  ┌─────────────────┐ ┌─────────────────┐ ┌──────────────────┐  │
│  │AgentsProvider    │ │CapabilitiesProvi│ │LedgerProvider    │  │
│  │  (Protocol)      │ │  der (Protocol)  │ │  (Protocol)      │  │
│  └─────────────────┘ └─────────────────┘ └──────────────────┘  │
│  ┌─────────────────┐                                             │
│  │SettingsProvider  │                                             │
│  │  (Protocol)      │                                             │
│  └─────────────────┘                                             │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│  owlclaw/web/providers/                                          │
│  ┌─────────────────┐ ┌─────────────────┐ ┌──────────────────┐  │
│  │DefaultOverview   │ │DefaultGovernance│ │DefaultTriggers   │  │
│  │  Provider        │ │  Provider       │ │  Provider        │  │
│  └────────┬────────┘ └────────┬────────┘ └────────┬─────────┘  │
│           │                    │                    │             │
│           ▼                    ▼                    ▼             │
│  imports owlclaw.governance  owlclaw.governance  owlclaw.triggers│
│         owlclaw.config       owlclaw.capabilities                │
│         owlclaw.agent        owlclaw.governance.ledger           │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 核心组件

#### 组件 1：查询契约层 (`owlclaw/web/contracts.py`)

**职责**：定义 Console API 所需的全部数据访问接口，使用 Python `Protocol` 类型。

**接口定义**：

```python
from typing import Any, Protocol
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass
class HealthStatus:
    component: str
    healthy: bool
    latency_ms: float | None = None
    message: str | None = None


@dataclass
class OverviewMetrics:
    total_cost_today: Decimal
    total_executions_today: int
    success_rate_today: float
    active_agents: int
    health_checks: list[HealthStatus]


class OverviewProvider(Protocol):
    async def get_overview(self, tenant_id: str) -> OverviewMetrics: ...


class GovernanceProvider(Protocol):
    async def get_budget_trend(
        self, tenant_id: str, start_date: date, end_date: date, granularity: str
    ) -> list[dict[str, Any]]: ...

    async def get_circuit_breaker_states(self, tenant_id: str) -> list[dict[str, Any]]: ...

    async def get_visibility_matrix(
        self, tenant_id: str, agent_id: str | None
    ) -> dict[str, Any]: ...


class TriggersProvider(Protocol):
    async def list_triggers(self, tenant_id: str) -> list[dict[str, Any]]: ...

    async def get_trigger_history(
        self, trigger_id: str, tenant_id: str, limit: int, offset: int
    ) -> tuple[list[dict[str, Any]], int]: ...


class AgentsProvider(Protocol):
    async def list_agents(self, tenant_id: str) -> list[dict[str, Any]]: ...

    async def get_agent_detail(
        self, agent_id: str, tenant_id: str
    ) -> dict[str, Any] | None: ...


class CapabilitiesProvider(Protocol):
    async def list_capabilities(
        self, tenant_id: str, category: str | None
    ) -> list[dict[str, Any]]: ...

    async def get_capability_schema(
        self, capability_name: str
    ) -> dict[str, Any] | None: ...


class LedgerProvider(Protocol):
    async def query_records(
        self,
        tenant_id: str,
        agent_id: str | None,
        capability_name: str | None,
        status: str | None,
        start_date: date | None,
        end_date: date | None,
        limit: int,
        offset: int,
        order_by: str | None,
    ) -> tuple[list[dict[str, Any]], int]: ...

    async def get_record_detail(
        self, record_id: str, tenant_id: str
    ) -> dict[str, Any] | None: ...


class SettingsProvider(Protocol):
    async def get_settings(self, tenant_id: str) -> dict[str, Any]: ...

    async def get_system_info(self) -> dict[str, Any]: ...
```

#### 组件 2：Provider 适配层 (`owlclaw/web/providers/`)

**职责**：将底层模块的具体实现适配为 Protocol 接口。这是唯一允许 import 底层模块的地方。

```
owlclaw/web/providers/
├── __init__.py
├── overview.py        # DefaultOverviewProvider
├── governance.py      # DefaultGovernanceProvider
├── agents.py          # DefaultAgentsProvider
├── capabilities.py    # DefaultCapabilitiesProvider
├── triggers.py        # DefaultTriggersProvider
├── ledger.py          # DefaultLedgerProvider
└── settings.py        # DefaultSettingsProvider
```

#### 组件 3：API 路由层 (`owlclaw/web/api/`)

**职责**：FastAPI 路由定义，只依赖 Protocol 接口。

```
owlclaw/web/api/
├── __init__.py        # create_api_app() factory
├── deps.py            # FastAPI Depends: get_overview_provider, etc.
├── middleware.py       # Token auth, CORS, error handler
├── schemas.py         # Pydantic response models
├── overview.py        # GET /api/v1/overview
├── agents.py          # GET /api/v1/agents, GET /api/v1/agents/{id}
├── governance.py      # GET /api/v1/governance/*
├── capabilities.py    # GET /api/v1/capabilities
├── triggers.py        # GET /api/v1/triggers
├── ledger.py          # GET /api/v1/ledger
├── settings.py        # GET /api/v1/settings
└── ws.py              # WebSocket /api/v1/ws
```

#### 组件 4：应用工厂 (`owlclaw/web/app.py`)

**职责**：组装 Provider 实例，创建 FastAPI 应用，挂载到 OwlClaw 主进程。

---

## 2. 实现细节

### 2.1 文件结构

```
owlclaw/web/
├── __init__.py
├── app.py             # create_console_app() — assembles providers + API
├── contracts.py       # Protocol interfaces (stable)
├── api/
│   ├── __init__.py    # create_api_app() — FastAPI sub-application
│   ├── deps.py        # Dependency injection
│   ├── middleware.py   # Auth + CORS + error handling
│   ├── schemas.py     # Pydantic response/request models
│   ├── overview.py
│   ├── agents.py
│   ├── governance.py
│   ├── capabilities.py
│   ├── triggers.py
│   ├── ledger.py
│   ├── settings.py
│   └── ws.py
└── providers/
    ├── __init__.py
    ├── overview.py
    ├── governance.py
    ├── agents.py
    ├── capabilities.py
    ├── triggers.py
    ├── ledger.py
    └── settings.py
```

### 2.2 依赖注入

FastAPI 的 `Depends` 机制用于注入 Provider 实例。`deps.py` 定义全局 Provider 注册表，由 `app.py` 在启动时填充。

```python
# owlclaw/web/api/deps.py
from owlclaw.web.contracts import (
    OverviewProvider,
    GovernanceProvider,
    TriggersProvider,
    AgentsProvider,
    CapabilitiesProvider,
    LedgerProvider,
    SettingsProvider,
)

_providers: dict[str, Any] = {}

def set_providers(**kwargs: Any) -> None:
    _providers.update(kwargs)

async def get_overview_provider() -> OverviewProvider:
    return _providers["overview"]

# ... similar for other providers
```

### 2.3 认证中间件

MVP 使用静态 Token 认证：

```python
# owlclaw/web/api/middleware.py
import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

class TokenAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        token = os.environ.get("OWLCLAW_CONSOLE_TOKEN")
        if not token:
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer ") or auth_header[7:] != token:
            return JSONResponse(
                {"error": {"code": "UNAUTHORIZED", "message": "Invalid or missing token"}},
                status_code=401,
            )
        return await call_next(request)
```

### 2.4 统一响应格式

```python
# owlclaw/web/api/schemas.py
from pydantic import BaseModel
from typing import Any, Generic, TypeVar

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    offset: int
    limit: int

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None

class ErrorResponse(BaseModel):
    error: ErrorDetail
```

### 2.5 Provider 适配示例

```python
# owlclaw/web/providers/ledger.py
from datetime import date
from typing import Any

from owlclaw.governance.ledger import ExecutionLedger, LedgerQueryFilters


class DefaultLedgerProvider:
    def __init__(self, ledger: ExecutionLedger) -> None:
        self._ledger = ledger

    async def query_records(
        self,
        tenant_id: str,
        agent_id: str | None = None,
        capability_name: str | None = None,
        status: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 50,
        offset: int = 0,
        order_by: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        filters = LedgerQueryFilters(
            agent_id=agent_id,
            capability_name=capability_name,
            status=status,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
            order_by=order_by,
        )
        records = await self._ledger.query_records(tenant_id, filters)
        total = await self._ledger.count_records(tenant_id, filters)
        return [self._serialize(r) for r in records], total

    def _serialize(self, record: Any) -> dict[str, Any]:
        return {
            "id": str(record.id),
            "agent_id": record.agent_id,
            "capability_name": record.capability_name,
            "status": record.status,
            "execution_time_ms": record.execution_time_ms,
            "estimated_cost": str(record.estimated_cost),
            "created_at": record.created_at.isoformat(),
        }
```

---

## 3. 数据流

### 3.1 API 请求处理流程

```
Client → HTTP Request
    │
    ▼
TokenAuthMiddleware → 401 if invalid
    │
    ▼
FastAPI Router (e.g., /api/v1/ledger)
    │
    ▼
Route Handler
    │  depends on LedgerProvider (Protocol)
    ▼
deps.py → returns DefaultLedgerProvider instance
    │
    ▼
DefaultLedgerProvider.query_records()
    │  imports and calls owlclaw.governance.ledger.ExecutionLedger
    ▼
Database query → results
    │
    ▼
Pydantic serialization → JSON response
```

### 3.2 WebSocket 实时推送流程

```
Client → WebSocket /api/v1/ws
    │
    ▼
Auth check (token in query param or first message)
    │
    ▼
Subscribe to event channels (overview/triggers/ledger)
    │
    ▼
Background task polls providers at intervals:
  - OverviewProvider.get_overview() every 30s
  - TriggersProvider event stream
  - LedgerProvider new records
    │
    ▼
Push JSON messages to connected clients
```

消息契约固定为三类：`overview`、`triggers`、`ledger`，用于前端缓存增量更新。

---

## 4. 错误处理

### 4.1 Provider 异常

**场景**：底层模块不可用（DB 断连、Hatchet 不可达）

**处理**：Provider 捕获底层异常，返回降级数据（标记 `healthy: false`），不抛到 API 层。

### 4.2 认证失败

**场景**：无 Token 或 Token 不匹配

**处理**：中间件返回 401，统一错误格式。

### 4.3 参数校验

**场景**：无效的筛选参数

**处理**：由全局异常处理器拦截 `RequestValidationError`，返回 422 且使用统一 `ErrorResponse` 结构（`code=VALIDATION_ERROR`，`details.errors` 包含字段错误明细）。

---

## 5. 配置

### 5.1 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `OWLCLAW_CONSOLE_TOKEN` | Console API 认证 Token | 空（禁用认证） |
| `OWLCLAW_CONSOLE_CORS_ORIGINS` | CORS 允许的源 | `*`（开发模式） |

### 5.2 owlclaw.yaml 配置

```yaml
console:
  enabled: true
  auth:
    token: ${OWLCLAW_CONSOLE_TOKEN}
  cors:
    origins: ["*"]
  cache:
    overview_ttl_seconds: 30
```

---

## 6. 测试策略

### 6.1 单元测试

- 每个 API 路由使用 mock Provider 测试
- Provider 适配层使用 mock 底层模块测试
- 认证中间件独立测试

### 6.2 集成测试

- 完整 API 请求链路（FastAPI TestClient + 真实 Provider + 内存数据）
- WebSocket 连接和消息推送测试

### 6.3 架构隔离测试

- AST 扫描 `owlclaw/web/api/` 目录，验证无 `from owlclaw.agent`、`from owlclaw.governance` 等直接导入
- 此测试作为 CI 门禁

---

## 7. 迁移计划

### 7.1 Phase 1：框架搭建（2-3 天）

- [x] 创建 `owlclaw/web/` 包结构
- [x] 实现 contracts.py（全部 Protocol）
- [x] 实现 API 框架（路由挂载 + 认证 + 错误处理 + 分页）
- [x] 实现 deps.py 依赖注入

### 7.2 Phase 2：核心 API（3-4 天）

- [x] 实现 Overview Provider + API
- [x] 实现 Governance Provider + API
- [x] 实现 Ledger Provider + API
- [x] 实现 Capabilities Provider + API

### 7.3 Phase 3：扩展 API（2-3 天）

- [x] 实现 Agents Provider + API
- [x] 实现 Triggers Provider + API
- [x] 实现 Settings Provider + API
- [x] 实现 WebSocket 实时推送

### 7.4 Phase 4：测试与验收（1-2 天）

- [x] 单元测试全覆盖
- [x] 集成测试
- [x] 架构隔离扫描
- [x] 性能基准测试

---

## 8. 风险与缓解

### 8.1 底层模块缺少 count 方法

**影响**：分页需要 total count，但 `ExecutionLedger.query_records()` 可能不返回总数

**缓解**：Provider 层补充 count 查询；若底层无 count 方法，Provider 使用 `SELECT COUNT(*)` 独立查询

### 8.2 WebSocket 内存压力

**影响**：大量客户端连接可能导致内存问题

**缓解**：MVP 限制最大连接数（默认 10）；使用 asyncio 事件而非轮询

---

**维护者**：yeemio  
**最后更新**：2026-03-02

