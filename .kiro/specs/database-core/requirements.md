# 需求文档：数据库核心基础设施

## 文档联动

- requirements: `.kiro/specs/database-core/requirements.md`
- design: `.kiro/specs/database-core/design.md`
- tasks: `.kiro/specs/database-core/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


## 简介

数据库核心基础设施为 OwlClaw 提供基于 SQLAlchemy 的异步数据库操作能力，支持 PostgreSQL 数据库。该基础设施从第一天起就强制实施多租户隔离，管理连接池，并提供 session 和 engine 管理工具。设计支持 OwlClaw 从自托管单租户部署演进到云端多租户 SaaS，同时保持向后兼容性。

## 术语表

- **Base**：SQLAlchemy 声明式基类，所有 OwlClaw 模型都继承自该类
- **Engine**：SQLAlchemy 异步引擎，管理数据库连接
- **Session**：SQLAlchemy 异步会话，用于执行数据库操作
- **Connection_Pool**：连接池，由 SQLAlchemy 管理的可复用数据库连接池
- **tenant_id**：租户标识符，用于多租户数据隔离（自托管默认值为 'default'）
- **Database_URL**：PostgreSQL 连接字符串，格式为 `postgresql+asyncpg://user:pass@host:port/dbname`
- **pgvector**：PostgreSQL 向量相似度搜索扩展
- **Alembic**：SQLAlchemy 的数据库迁移工具
- **asyncpg**：Python 的异步 PostgreSQL 驱动

## 需求

### 需求 1：强制租户隔离的声明式基类

**用户故事**：作为开发者，我希望所有数据库模型都继承自一个强制包含 tenant_id 的 Base 类，以便从第一天起就保证多租户隔离，避免未来的 schema 迁移。

#### 验收标准

1. THE Base SHALL 是一个 SQLAlchemy DeclarativeBase 类
2. THE Base SHALL 提供类型为 VARCHAR(64) 的 tenant_id 列
3. THE Base SHALL 将 tenant_id 设置为 NOT NULL，默认值为 'default'
4. THE Base SHALL 为所有表的 tenant_id 创建索引
5. THE Base SHALL 暴露 metadata 以支持 Alembic 自动生成迁移脚本

### 需求 2：异步引擎管理

**用户故事**：作为开发者，我希望能够创建和管理异步数据库引擎，以便使用正确的配置连接到 PostgreSQL。

#### 验收标准

1. THE Engine_Factory SHALL 使用 asyncpg 驱动创建异步引擎
2. WHEN 提供 Database_URL 时，THE Engine_Factory SHALL 验证 URL 格式
3. WHEN Database_URL 包含无效凭据时，THE Engine_Factory SHALL 抛出描述性错误
4. THE Engine_Factory SHALL 支持从环境变量 OWLCLAW_DATABASE_URL 读取 Database_URL
5. THE Engine_Factory SHALL 接受连接池参数（pool_size、max_overflow、pool_timeout、pool_recycle）
6. THE Engine_Factory SHALL 默认启用 pool_pre_ping 以检测失效连接
7. THE Engine_Factory SHALL 支持 echo 参数用于开发时的 SQL 日志记录

### 需求 3：异步会话管理

**用户故事**：作为开发者，我希望通过异步上下文管理器获取数据库会话，以便连接能够自动清理。

#### 验收标准

1. THE Session_Factory SHALL 创建绑定到引擎的异步 sessionmaker 实例
2. THE Session_Factory SHALL 支持异步上下文管理器协议以实现自动清理
3. WHEN 会话在异步上下文中使用时，THE Session_Factory SHALL 在成功时提交事务
4. WHEN 会话上下文中发生异常时，THE Session_Factory SHALL 回滚事务
5. WHEN 会话上下文退出时，THE Session_Factory SHALL 关闭会话

### 需求 4：数据库工具函数

**用户故事**：作为开发者，我希望有便捷的工具函数来获取引擎和会话，以便无需手动管理生命周期即可访问数据库。

#### 验收标准

1. THE get_engine 函数 SHALL 返回已配置的异步引擎实例
2. THE get_engine 函数 SHALL 接受可选的 Database_URL 参数
3. THE get_engine 函数 SHALL 为相同的 Database_URL 复用现有引擎实例
4. THE get_session 函数 SHALL 返回会话的异步上下文管理器
5. THE get_session 函数 SHALL 接受可选的 engine 参数
6. WHEN 调用 get_session 时未提供 engine，THE get_session 函数 SHALL 使用默认引擎

### 需求 5：连接池配置

**用户故事**：作为系统管理员，我希望能够配置连接池参数，以便针对我的部署规模优化数据库资源使用。

#### 验收标准

1. THE Connection_Pool SHALL 支持 pool_size 参数，默认值为 20
2. THE Connection_Pool SHALL 支持 max_overflow 参数，默认值为 10
3. THE Connection_Pool SHALL 支持 pool_timeout 参数，默认值为 30 秒
4. THE Connection_Pool SHALL 支持 pool_recycle 参数，默认值为 1800 秒
5. WHEN pool_size 加 max_overflow 超限时，THE Connection_Pool SHALL 在 pool_timeout 秒后抛出超时错误
6. WHEN 连接超过 pool_recycle 时间时，THE Connection_Pool SHALL 关闭并替换该连接

### 需求 6：环境变量支持

**用户故事**：作为 DevOps 工程师，我希望通过环境变量配置数据库连接，以便在容器化环境中部署 OwlClaw 而无需修改代码。

#### 验收标准

1. WHEN 设置了 OWLCLAW_DATABASE_URL 时，THE Engine_Factory SHALL 使用它作为连接字符串
2. WHEN 未设置 OWLCLAW_DATABASE_URL 时，THE Engine_Factory SHALL 抛出配置错误
3. THE Engine_Factory SHALL 支持在 Database_URL 中从环境变量插值密码
4. WHEN 显式向 get_engine 提供 Database_URL 时，THE Engine_Factory SHALL 使用它而不是 OWLCLAW_DATABASE_URL

### 需求 7：PostgreSQL 和 pgvector 支持

**用户故事**：作为开发者，我希望数据库基础设施能够与 PostgreSQL 和 pgvector 扩展配合工作，以便为 agent 记忆存储和查询向量嵌入。

#### 验收标准

1. THE Engine_Factory SHALL 使用 postgresql+asyncpg 作为数据库方言
2. THE Engine_Factory SHALL 支持连接到 PostgreSQL 13 或更高版本
3. THE Base SHALL 兼容 pgvector 扩展类型
4. WHEN pgvector 扩展未安装时，THE Engine_Factory SHALL 提供清晰的错误消息

### 需求 8：Alembic 集成准备

**用户故事**：作为开发者，我希望 Base 类暴露 metadata，以便 Alembic 能够从模型定义自动生成迁移脚本。

#### 验收标准

1. THE Base SHALL 暴露类型为 MetaData 的 metadata 属性
2. THE Base.metadata SHALL 包含所有继承自 Base 的模型的表定义
3. THE Base.metadata SHALL 在建立任何数据库连接之前可访问
4. THE Base.metadata SHALL 支持 Alembic 的 autogenerate 功能

### 需求 9：错误处理

**用户故事**：作为开发者，我希望数据库配置问题能有清晰的错误消息，以便快速诊断和修复问题。

#### 验收标准

1. WHEN Database_URL 格式无效时，THE Engine_Factory SHALL 抛出包含格式要求的 ValueError
2. WHEN 数据库连接失败时，THE Engine_Factory SHALL 抛出包含主机和端口详情的 ConnectionError
3. WHEN 认证失败时，THE Engine_Factory SHALL 抛出不暴露密码的 AuthenticationError
4. WHEN pool_timeout 超时时，THE Connection_Pool SHALL 抛出包含当前连接池统计信息的 TimeoutError
5. WHEN 使用不支持的数据库方言时，THE Engine_Factory SHALL 抛出列出支持方言的 ValueError

### 需求 10：模块组织

**用户故事**：作为开发者，我希望数据库基础设施以清晰的模块结构组织，以便轻松导入和使用数据库工具。

#### 验收标准

1. THE 数据库基础设施 SHALL 位于 owlclaw/db/ 模块中
2. THE Base 类 SHALL 可从 owlclaw.db 导入
3. THE get_engine 函数 SHALL 可从 owlclaw.db 导入
4. THE get_session 函数 SHALL 可从 owlclaw.db 导入
5. THE 模块 SHALL 暴露列出公共 API 组件的 __all__
