# 设计文档：数据库核心基础设施

## 文档联动

- requirements: `.kiro/specs/database-core/requirements.md`
- design: `.kiro/specs/database-core/design.md`
- tasks: `.kiro/specs/database-core/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


## 概述

数据库核心基础设施为 OwlClaw 提供基于 SQLAlchemy 2.0+ 异步 API 的数据库访问层。该模块实现了以下核心功能：

- **声明式基类（Base）**：所有 ORM 模型的基类，强制包含 tenant_id 字段
- **异步引擎管理**：创建和管理 asyncpg 驱动的异步数据库引擎
- **会话工厂**：提供异步上下文管理器用于数据库会话
- **连接池配置**：可配置的连接池参数以优化资源使用
- **工具函数**：便捷的 get_engine() 和 get_session() 函数

该设计遵循 OwlClaw 数据库架构的五条铁律（参见 `docs/DATABASE_ARCHITECTURE.md`），特别是从第一天起就强制实施 tenant_id，为未来的多租户 SaaS 演进做好准备。

## 架构例外声明（实现阶段需固化）

本 spec 当前未引入业务层面的数据库铁律例外。实现阶段遵循以下约束：

1. 所有业务模型保持 `tenant_id VARCHAR(64)` 统一口径，不引入租户 ID 的多类型并存。
2. 时间字段默认使用 `TIMESTAMPTZ`（按数据库规范）；若出现聚合场景使用 `DATE`，必须在对应业务 spec 显式声明原因与约束。
3. `alembic_version` 属于 Alembic 系统表，不适用业务表约束（不要求 `tenant_id/UUID`）。

## 架构

### 模块结构

```
owlclaw/
└── db/
    ├── __init__.py          # 公共 API 导出
    ├── base.py              # Base 声明式基类
    ├── engine.py            # 引擎创建和管理
    ├── session.py           # 会话工厂和上下文管理器
    └── exceptions.py        # 自定义异常类
```

### 依赖关系

```mermaid
graph TD
    A[owlclaw.db] --> B[base.py]
    A --> C[engine.py]
    A --> D[session.py]
    A --> E[exceptions.py]
    
    C --> E
    D --> C
    D --> E
    
    B --> F[SQLAlchemy DeclarativeBase]
    C --> G[SQLAlchemy create_async_engine]
    D --> H[SQLAlchemy async_sessionmaker]
```

### 数据流

```mermaid
sequenceDiagram
    participant App as 应用代码
    participant GE as get_engine()
    participant GS as get_session()
    participant Engine as AsyncEngine
    participant Pool as 连接池
    participant DB as PostgreSQL
    
    App->>GE: 请求引擎
    GE->>Engine: 创建/复用引擎
    Engine->>Pool: 初始化连接池
    
    App->>GS: 请求会话
    GS->>Engine: 获取引擎
    GS->>App: 返回 AsyncSession 上下文管理器
    
    App->>App: async with session
    App->>DB: 执行查询
    DB->>App: 返回结果
    App->>App: 提交/回滚
    App->>Pool: 归还连接
```

## 组件和接口

### 1. Base 声明式基类 (base.py)

**职责**：
- 提供所有 ORM 模型的基类
- 强制包含 tenant_id 字段
- 暴露 metadata 供 Alembic 使用

**接口**：

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Index

class Base(DeclarativeBase):
    """
    所有 OwlClaw ORM 模型的基类。
    
    自动为所有继承的模型添加 tenant_id 字段和索引。
    """
    
    # 声明式映射的 tenant_id 字段
    tenant_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="default",
        index=True,
        doc="租户标识符，自托管默认为 'default'"
    )
    
    # 暴露 metadata 供 Alembic 使用
    # metadata: ClassVar[MetaData]  # 由 DeclarativeBase 自动提供
```

**设计决策**：
- 使用 SQLAlchemy 2.0 的 `Mapped` 类型注解，提供更好的类型检查
- tenant_id 默认值为 "default" 适用于自托管场景
- 使用 `index=True` 自动为每个表的 tenant_id 创建索引
- 继承自 `DeclarativeBase` 而不是旧式的 `declarative_base()`

### 2. 引擎管理 (engine.py)

**职责**：
- 创建和配置异步数据库引擎
- 管理引擎实例的生命周期
- 验证数据库连接配置

**接口**：

```python
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from typing import Optional
import os

# 全局引擎缓存
_engines: dict[str, AsyncEngine] = {}

def create_engine(
    database_url: Optional[str] = None,
    *,
    pool_size: int = 20,
    max_overflow: int = 10,
    pool_timeout: float = 30.0,
    pool_recycle: int = 1800,
    pool_pre_ping: bool = True,
    echo: bool = False,
) -> AsyncEngine:
    """
    创建异步数据库引擎。
    
    Args:
        database_url: PostgreSQL 连接字符串，格式为
            postgresql+asyncpg://user:pass@host:port/dbname
            如果为 None，从环境变量 OWLCLAW_DATABASE_URL 读取
        pool_size: 连接池常驻连接数
        max_overflow: 超出 pool_size 时允许的额外连接数
        pool_timeout: 等待可用连接的超时时间（秒）
        pool_recycle: 连接回收时间（秒），防止数据库端超时
        pool_pre_ping: 使用前 ping 检测连接是否存活
        echo: 是否打印 SQL 语句（开发时使用）
    
    Returns:
        配置好的 AsyncEngine 实例
    
    Raises:
        ValueError: database_url 格式无效或未提供
        ConnectionError: 无法连接到数据库
        AuthenticationError: 认证失败
    """
    pass

def get_engine(database_url: Optional[str] = None) -> AsyncEngine:
    """
    获取或创建数据库引擎（单例模式）。
    
    对于相同的 database_url，返回缓存的引擎实例。
    
    Args:
        database_url: 可选的数据库连接字符串
    
    Returns:
        AsyncEngine 实例
    """
    pass

async def dispose_engine(database_url: Optional[str] = None) -> None:
    """
    释放引擎资源并关闭所有连接。
    
    Args:
        database_url: 要释放的引擎的连接字符串，
            如果为 None，释放所有引擎
    """
    pass
```

**实现细节**：
- 使用 `postgresql+asyncpg` 作为数据库方言
- 引擎实例按 database_url 缓存，避免重复创建
- 默认启用 `pool_pre_ping` 以检测失效连接
- 连接池参数遵循 `docs/DATABASE_ARCHITECTURE.md` 的推荐值

### 3. 会话管理 (session.py)

**职责**：
- 创建异步会话工厂
- 提供异步上下文管理器
- 自动处理事务提交和回滚

**接口**：

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """
    创建异步会话工厂。
    
    Args:
        engine: 异步数据库引擎
    
    Returns:
        async_sessionmaker 实例
    """
    pass

@asynccontextmanager
async def get_session(
    engine: Optional[AsyncEngine] = None
) -> AsyncIterator[AsyncSession]:
    """
    获取数据库会话的异步上下文管理器。
    
    自动处理事务：
    - 成功时提交
    - 异常时回滚
    - 退出时关闭会话
    
    Args:
        engine: 可选的数据库引擎，如果为 None 使用默认引擎
    
    Yields:
        AsyncSession 实例
    
    Example:
        async with get_session() as session:
            result = await session.execute(select(User))
            users = result.scalars().all()
    """
    pass
```

**实现细节**：
- 使用 `async_sessionmaker` 创建会话工厂
- 上下文管理器自动处理 commit/rollback/close
- 支持嵌套事务（通过 SQLAlchemy 的 savepoint）

### 4. 异常处理 (exceptions.py)

**职责**：
- 定义数据库相关的自定义异常
- 提供清晰的错误消息

**接口**：

```python
class DatabaseError(Exception):
    """数据库操作基础异常"""
    pass

class ConfigurationError(DatabaseError):
    """数据库配置错误"""
    pass

class ConnectionError(DatabaseError):
    """数据库连接错误"""
    def __init__(self, host: str, port: int, message: str):
        self.host = host
        self.port = port
        super().__init__(f"无法连接到 {host}:{port} - {message}")

class AuthenticationError(DatabaseError):
    """数据库认证错误（不暴露密码）"""
    def __init__(self, user: str, database: str):
        self.user = user
        self.database = database
        super().__init__(
            f"认证失败：用户 '{user}' 无法访问数据库 '{database}'"
        )

class PoolTimeoutError(DatabaseError):
    """连接池超时错误"""
    def __init__(self, pool_size: int, max_overflow: int, timeout: float):
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.timeout = timeout
        super().__init__(
            f"连接池超时：{timeout}秒内无法获取连接 "
            f"(pool_size={pool_size}, max_overflow={max_overflow})"
        )
```

### 5. 公共 API (__init__.py)

**职责**：
- 导出公共接口
- 提供清晰的模块 API

**接口**：

```python
from owlclaw.db.base import Base
from owlclaw.db.engine import create_engine, get_engine, dispose_engine
from owlclaw.db.session import create_session_factory, get_session
from owlclaw.db.exceptions import (
    DatabaseError,
    ConfigurationError,
    ConnectionError,
    AuthenticationError,
    PoolTimeoutError,
)

__all__ = [
    # Base 类
    "Base",
    # 引擎管理
    "create_engine",
    "get_engine",
    "dispose_engine",
    # 会话管理
    "create_session_factory",
    "get_session",
    # 异常
    "DatabaseError",
    "ConfigurationError",
    "ConnectionError",
    "AuthenticationError",
    "PoolTimeoutError",
]
```

## 数据模型

### Base 类的 tenant_id 字段

所有继承自 Base 的模型都会自动包含以下字段：

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|--------|------|------|--------|------|
| tenant_id | VARCHAR(64) | NOT NULL, INDEX | 'default' | 租户标识符 |

### 示例模型定义

```python
from owlclaw.db import Base
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from uuid import UUID, uuid4

class LedgerRecord(Base):
    """治理层执行记录"""
    __tablename__ = "ledger_records"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    # tenant_id 由 Base 自动提供
    agent_id: Mapped[str] = mapped_column(String(128), nullable=False)
    capability: Mapped[str] = mapped_column(String(256), nullable=False)
    decision: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
```

### 数据库连接配置

连接字符串格式：

```
postgresql+asyncpg://user:password@host:port/database
```

环境变量：

```bash
export OWLCLAW_DATABASE_URL="postgresql+asyncpg://owlclaw:password@localhost:5432/owlclaw"
```

连接池参数：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| pool_size | 20 | 连接池常驻连接数 |
| max_overflow | 10 | 超出 pool_size 时允许的额外连接数 |
| pool_timeout | 30 | 等待可用连接的超时时间（秒） |
| pool_recycle | 1800 | 连接回收时间（秒） |
| pool_pre_ping | True | 使用前 ping 检测连接是否存活 |


## 正确性属性

属性是一种特征或行为，应该在系统的所有有效执行中保持为真——本质上是关于系统应该做什么的形式化陈述。属性作为人类可读规范和机器可验证正确性保证之间的桥梁。

### 属性 1：Base 类的 tenant_id 字段完整性

*对于任何*继承自 Base 的模型类，该模型应该包含一个 VARCHAR(64) 类型的 tenant_id 字段，该字段为 NOT NULL，默认值为 'default'，并且有索引。

**验证需求：1.2, 1.3, 1.4**

### 属性 2：Database_URL 格式验证

*对于任何*提供给 create_engine 的字符串，如果该字符串不符合 `postgresql+asyncpg://user:pass@host:port/dbname` 格式，则应该抛出包含格式要求的 ValueError。

**验证需求：2.2, 9.1**

### 属性 3：引擎实例复用

*对于任何*相同的 Database_URL，多次调用 get_engine 应该返回同一个引擎实例（对象标识相同）。

**验证需求：4.3**

### 属性 4：会话事务管理

*对于任何*数据库会话，当在异步上下文管理器中使用时：
- 如果操作成功完成，应该自动提交事务
- 如果发生异常，应该自动回滚事务
- 退出上下文时，应该关闭会话

**验证需求：3.3, 3.4, 3.5**

### 属性 5：Base.metadata 包含所有模型

*对于任何*继承自 Base 的模型类，Base.metadata 应该包含该模型对应的表定义。

**验证需求：8.2**

### 属性 6：不支持的数据库方言错误

*对于任何*不是 `postgresql+asyncpg` 的数据库方言字符串，create_engine 应该抛出列出支持方言的 ValueError。

**验证需求：9.5**

### 属性 7：连接池参数传递

*对于任何*有效的连接池参数组合（pool_size、max_overflow、pool_timeout、pool_recycle），create_engine 应该创建具有这些配置的引擎。

**验证需求：2.5**

## 错误处理

### 错误类型层次

```
DatabaseError (基础异常)
├── ConfigurationError (配置错误)
├── ConnectionError (连接错误)
├── AuthenticationError (认证错误)
└── PoolTimeoutError (连接池超时)
```

### 错误场景和处理策略

| 场景 | 异常类型 | 错误消息内容 | 恢复策略 |
|------|---------|-------------|---------|
| 未设置 DATABASE_URL | ConfigurationError | "未配置数据库连接：请设置 OWLCLAW_DATABASE_URL 环境变量" | 用户配置环境变量 |
| URL 格式无效 | ValueError | "无效的数据库 URL 格式，期望：postgresql+asyncpg://..." | 用户修正 URL 格式 |
| 无法连接数据库 | ConnectionError | "无法连接到 host:port - 详细错误" | 检查网络和数据库状态 |
| 认证失败 | AuthenticationError | "认证失败：用户 'user' 无法访问数据库 'db'" | 检查用户名和密码 |
| 连接池超时 | PoolTimeoutError | "连接池超时：30秒内无法获取连接 (pool_size=20, max_overflow=10)" | 增加连接池大小或优化查询 |
| 不支持的方言 | ValueError | "不支持的数据库方言 'mysql'，支持的方言：['postgresql+asyncpg']" | 使用支持的数据库 |

### 错误处理原则

1. **不暴露敏感信息**：错误消息中不包含密码
2. **提供上下文**：包含足够的信息帮助诊断问题（主机、端口、用户名、数据库名）
3. **可操作性**：错误消息应该指导用户如何修复问题
4. **类型安全**：使用特定的异常类型，便于调用者捕获和处理

## 测试策略

### 双重测试方法

数据库核心基础设施需要同时使用单元测试和基于属性的测试：

- **单元测试**：验证特定示例、边缘情况和错误条件
- **基于属性的测试**：验证跨所有输入的通用属性

两者是互补的，共同提供全面的覆盖。

### 单元测试重点

单元测试应该专注于：

1. **特定示例**：
   - Base 类是 DeclarativeBase 的子类
   - 默认引擎使用 asyncpg 驱动
   - 可以从 owlclaw.db 导入公共 API
   - Base.metadata 在连接前可访问

2. **边缘情况**：
   - 无效凭据导致的连接失败
   - 连接池超时
   - pgvector 扩展未安装
   - 认证失败

3. **配置测试**：
   - 环境变量读取
   - 参数优先级（显式参数 > 环境变量）
   - 连接池默认值
   - pgvector 类型兼容性

### 基于属性的测试

基于属性的测试应该验证：

1. **属性 1-7**：如正确性属性部分所述
2. **测试配置**：每个属性测试至少运行 100 次迭代
3. **标签格式**：`Feature: database-core, Property N: [属性描述]`

### 测试库选择

- **Python**：使用 `hypothesis` 进行基于属性的测试
- **单元测试框架**：使用 `pytest`
- **异步测试**：使用 `pytest-asyncio`
- **数据库测试**：使用 `pytest-postgresql` 或 Docker 容器

### 测试隔离

- 每个测试使用独立的引擎实例
- 测试后清理全局引擎缓存
- 使用测试数据库，不影响开发数据库
- 模拟网络错误和数据库故障

### 集成测试

虽然本模块主要是基础设施代码，但仍需要一些集成测试：

- 实际连接到 PostgreSQL 数据库
- 测试 Alembic 迁移生成
- 测试 pgvector 扩展集成
- 测试连接池在高并发下的行为

这些集成测试应该标记为 `@pytest.mark.integration`，可以在 CI 中选择性运行。

## 实现注意事项

### 性能考虑

1. **引擎复用**：使用全局字典缓存引擎实例，避免重复创建
2. **连接池配置**：根据部署规模调整连接池参数
3. **预检查连接**：启用 pool_pre_ping 避免使用失效连接

### 安全考虑

1. **密码保护**：错误消息中不暴露密码
2. **SQL 注入**：使用参数化查询（SQLAlchemy 自动处理）
3. **连接加密**：支持 SSL 连接（通过 URL 参数配置）

### 可维护性

1. **类型注解**：所有公共 API 使用类型注解
2. **文档字符串**：所有公共函数和类包含详细的文档字符串
3. **错误消息**：清晰、可操作的错误消息
4. **日志记录**：关键操作记录日志（引擎创建、连接获取等）

### 向后兼容性

1. **API 稳定性**：公共 API 保持稳定，避免破坏性变更
2. **弃用策略**：使用 `warnings.warn` 标记弃用的功能
3. **版本管理**：遵循语义化版本控制

### 未来扩展

1. **读写分离**：支持配置只读副本
2. **多数据库**：支持连接多个数据库
3. **RLS 支持**：为 Cloud 版本添加 Row-Level Security 支持
4. **连接池监控**：暴露连接池统计信息的 API
