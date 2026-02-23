# 实现计划：数据库核心基础设施

## 文档联动

- requirements: `.kiro/specs/database-core/requirements.md`
- design: `.kiro/specs/database-core/design.md`
- tasks: `.kiro/specs/database-core/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


## 概述

本实现计划将数据库核心基础设施分解为一系列增量式的编码任务。每个任务都建立在前面任务的基础上，最终将所有组件集成在一起。实现将使用 Python 和 SQLAlchemy 2.0+ 异步 API。

## 任务

- [x] 1. 设置项目结构和依赖
  - 创建 `owlclaw/db/` 目录结构
  - 在 `pyproject.toml` 中添加依赖：sqlalchemy[asyncio]>=2.0, asyncpg, pgvector
  - 创建 `owlclaw/db/__init__.py` 文件
  - _需求：10.1_

- [x] 2. 实现自定义异常类
  - [x] 2.1 创建 `owlclaw/db/exceptions.py`
    - 实现 DatabaseError 基类
    - 实现 ConfigurationError、ConnectionError、AuthenticationError、PoolTimeoutError
    - 每个异常类包含适当的构造函数和错误消息格式
    - _需求：9.1, 9.2, 9.3, 9.4_
  
  - [ ]* 2.2 为异常类编写单元测试
    - 测试每个异常类的实例化
    - 测试错误消息格式
    - 测试不暴露敏感信息（如密码）
    - _需求：9.3_

- [x] 3. 实现 Base 声明式基类
  - [x] 3.1 创建 `owlclaw/db/base.py`
    - 定义 Base 类继承自 DeclarativeBase
    - 添加 tenant_id 字段（VARCHAR(64), NOT NULL, default='default', index=True）
    - 使用 SQLAlchemy 2.0 的 Mapped 和 mapped_column
    - 暴露 metadata 属性
    - _需求：1.1, 1.2, 1.3, 1.4, 1.5, 8.1_
  
  - [ ]* 3.2 编写 Base 类的基于属性的测试
    - **属性 1：Base 类的 tenant_id 字段完整性**
    - **验证需求：1.2, 1.3, 1.4**
  
  - [ ]* 3.3 编写 Base 类的基于属性的测试
    - **属性 5：Base.metadata 包含所有模型**
    - **验证需求：8.2**
  
  - [ ]* 3.4 编写 Base 类的单元测试
    - 测试 Base 是 DeclarativeBase 的子类
    - 测试 metadata 在连接前可访问
    - 测试创建示例模型并检查 tenant_id 字段
    - _需求：1.1, 8.3_

- [x] 4. 实现引擎管理
  - [x] 4.1 创建 `owlclaw/db/engine.py`
    - 实现 create_engine 函数
    - 支持从环境变量 OWLCLAW_DATABASE_URL 读取配置
    - 验证 Database_URL 格式
    - 配置连接池参数（pool_size, max_overflow, pool_timeout, pool_recycle）
    - 默认启用 pool_pre_ping
    - 支持 echo 参数
    - _需求：2.1, 2.2, 2.4, 2.5, 2.6, 2.7, 6.1, 6.2, 7.1_
  
  - [x] 4.2 实现 get_engine 函数
    - 使用全局字典缓存引擎实例
    - 支持可选的 database_url 参数
    - 参数优先级：显式参数 > 环境变量
    - _需求：4.1, 4.2, 4.3, 6.4_
  
  - [x] 4.3 实现 dispose_engine 函数
    - 释放引擎资源
    - 关闭所有连接
    - 清理缓存
    - _需求：4.1_
  
  - [ ]* 4.4 编写引擎管理的基于属性的测试
    - **属性 2：Database_URL 格式验证**
    - **验证需求：2.2, 9.1**
  
  - [ ]* 4.5 编写引擎管理的基于属性的测试
    - **属性 3：引擎实例复用**
    - **验证需求：4.3**
  
  - [ ]* 4.6 编写引擎管理的基于属性的测试
    - **属性 6：不支持的数据库方言错误**
    - **验证需求：9.5**
  
  - [ ]* 4.7 编写引擎管理的基于属性的测试
    - **属性 7：连接池参数传递**
    - **验证需求：2.5**
  
  - [x]* 4.8 编写引擎管理的单元测试
    - 测试环境变量读取
    - 测试参数优先级
    - 测试默认引擎使用 asyncpg 驱动
    - 测试连接池默认值
    - 测试未设置 DATABASE_URL 时抛出 ConfigurationError
    - _需求：2.1, 2.4, 5.1, 5.2, 5.3, 5.4, 6.1, 6.2, 6.4, 7.1_

- [x] 5. 检查点 - 确保所有测试通过
  - 确保所有测试通过，如有问题请询问用户。

- [x] 6. 实现会话管理
  - [x] 6.1 创建 `owlclaw/db/session.py`
    - 实现 create_session_factory 函数
    - 实现 get_session 异步上下文管理器
    - 自动处理事务提交、回滚和会话关闭
    - 支持可选的 engine 参数
    - _需求：3.1, 3.2, 3.3, 3.4, 3.5, 4.4, 4.5, 4.6_
  
  - [ ]* 6.2 编写会话管理的基于属性的测试
    - **属性 4：会话事务管理**
    - **验证需求：3.3, 3.4, 3.5**
  
  - [x]* 6.3 编写会话管理的单元测试
    - 测试 create_session_factory 返回 async_sessionmaker
    - 测试 get_session 支持异步上下文管理器协议
    - 测试不提供 engine 时使用默认引擎
    - 测试成功时自动提交
    - 测试异常时自动回滚
    - 测试退出时关闭会话
    - _需求：3.1, 3.2, 3.3, 3.4, 3.5, 4.6_

- [x] 7. 实现公共 API 导出
  - [x] 7.1 更新 `owlclaw/db/__init__.py`
    - 从各模块导入公共接口
    - 定义 __all__ 列表
    - 包含：Base, create_engine, get_engine, dispose_engine, create_session_factory, get_session
    - 包含所有异常类
    - _需求：10.2, 10.3, 10.4, 10.5_
  
  - [x]* 7.2 编写公共 API 的单元测试
    - 测试可以从 owlclaw.db 导入 Base
    - 测试可以从 owlclaw.db 导入 get_engine
    - 测试可以从 owlclaw.db 导入 get_session
    - 测试 __all__ 包含所有公共组件
    - _需求：10.2, 10.3, 10.4, 10.5_

- [ ] 8. 集成测试和文档
  - [x]* 8.1 编写集成测试
    - 测试实际连接到 PostgreSQL 数据库
    - 测试创建表和执行查询
    - 测试 pgvector 扩展兼容性
    - 测试连接池在并发下的行为
    - 使用 pytest-postgresql 或 Docker 容器
    - _需求：7.2, 7.3_
  
  - [x] 8.2 添加使用示例和文档字符串
    - 为所有公共函数和类添加详细的文档字符串
    - 在 README 或文档中添加使用示例
    - 包含配置示例（环境变量、连接池参数）
    - _需求：所有_

- [x] 9. 最终检查点 - 确保所有测试通过
  - 确保所有测试通过，如有问题请询问用户。

## 注意事项

- 标记为 `*` 的任务是可选的，可以跳过以加快 MVP 开发
- 每个任务都引用了具体的需求以便追溯
- 检查点确保增量验证
- 基于属性的测试验证通用正确性属性
- 单元测试验证特定示例和边缘情况
- 集成测试验证与实际数据库的交互
