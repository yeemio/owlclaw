# 需求文档：CLI 数据库运维工具

## 简介

CLI 数据库运维工具为 OwlClaw 提供统一的数据库运维命令行接口。通过 `owlclaw db` 子命令组，用户可以完成数据库初始化、schema 迁移、状态检查、备份恢复等运维操作。该工具封装了底层工具（Alembic、pg_dump、psql 等），提供一致的用户体验和清晰的错误提示。

## 术语表

- **CLI**：命令行接口（Command Line Interface）
- **Alembic**：SQLAlchemy 的数据库迁移工具
- **Migration**：数据库 schema 迁移脚本
- **Database_URL**：PostgreSQL 连接字符串，格式为 `postgresql://user:pass@host:port/dbname`
- **Admin_URL**：具有超级用户权限的 PostgreSQL 连接字符串，用于创建 database 和 role
- **Revision**：Alembic 迁移版本标识符
- **pg_dump**：PostgreSQL 官方备份工具
- **pg_restore**：PostgreSQL 官方恢复工具
- **Connection_Pool**：数据库连接池
- **RLS**：Row-Level Security，PostgreSQL 的行级安全策略
- **tenant_id**：租户标识符，用于多租户数据隔离
- **pgvector**：PostgreSQL 向量相似度搜索扩展
- **Dry_Run**：模拟执行模式，显示将要执行的操作但不实际执行

## 需求

### 需求 1：数据库初始化命令

**用户故事**：作为系统管理员，我希望通过一条命令在宿主 PostgreSQL 实例上初始化 OwlClaw 所需的 database、role 和 extension，以便快速完成部署准备。

#### 验收标准

1. WHEN 执行 `owlclaw db init` 时，THE CLI SHALL 创建 owlclaw database
2. WHEN 执行 `owlclaw db init` 时，THE CLI SHALL 创建 owlclaw role 并设置为 database owner
3. WHEN 执行 `owlclaw db init` 时，THE CLI SHALL 在 owlclaw database 中启用 pgvector 扩展
4. WHEN 提供 `--skip-hatchet` 参数时，THE CLI SHALL 跳过 hatchet database 的创建
5. WHEN 提供 `--owlclaw-password` 参数时，THE CLI SHALL 使用指定的密码创建 owlclaw role
6. WHEN 未提供 `--owlclaw-password` 参数时，THE CLI SHALL 生成随机密码并显示给用户
7. WHEN 提供 `--dry-run` 参数时，THE CLI SHALL 显示将要执行的 SQL 语句但不实际执行
8. WHEN Admin_URL 连接失败时，THE CLI SHALL 显示包含主机和端口的错误消息
9. WHEN owlclaw database 已存在时，THE CLI SHALL 显示警告并询问是否继续
10. WHEN 执行成功时，THE CLI SHALL 显示创建的 database、role 和 extension 信息

### 需求 2：Schema 迁移命令

**用户故事**：作为开发者，我希望通过命令执行数据库 schema 迁移，以便将数据库升级到最新版本。

#### 验收标准

1. WHEN 执行 `owlclaw db migrate` 时，THE CLI SHALL 调用 Alembic API 执行 upgrade head
2. WHEN 提供 `--target` 参数时，THE CLI SHALL 升级到指定的 Revision
3. WHEN 提供 `--dry-run` 参数时，THE CLI SHALL 显示将要执行的迁移但不实际执行
4. WHEN 提供 `--database-url` 参数时，THE CLI SHALL 使用指定的 Database_URL 而不是配置文件
5. WHEN 没有待执行的迁移时，THE CLI SHALL 显示 "Already up to date" 消息
6. WHEN 迁移执行失败时，THE CLI SHALL 显示失败的 Revision 和错误详情
7. WHEN 迁移执行成功时，THE CLI SHALL 显示已应用的 Revision 列表
8. WHEN Database_URL 未配置时，THE CLI SHALL 显示配置错误消息

### 需求 3：数据库状态检查命令

**用户故事**：作为系统管理员，我希望快速检查数据库连接和迁移状态，以便了解当前数据库的健康状况。

#### 验收标准

1. WHEN 执行 `owlclaw db status` 时，THE CLI SHALL 显示数据库连接信息（隐藏密码）
2. WHEN 执行 `owlclaw db status` 时，THE CLI SHALL 显示 PostgreSQL 服务器版本
3. WHEN 执行 `owlclaw db status` 时，THE CLI SHALL 显示已安装的扩展及其版本
4. WHEN 执行 `owlclaw db status` 时，THE CLI SHALL 显示当前的 Migration Revision
5. WHEN 执行 `owlclaw db status` 时，THE CLI SHALL 显示待执行的迁移数量
6. WHEN 执行 `owlclaw db status` 时，THE CLI SHALL 显示表数量和总行数
7. WHEN 执行 `owlclaw db status` 时，THE CLI SHALL 显示数据库磁盘使用量
8. WHEN 数据库连接失败时，THE CLI SHALL 显示连接错误并退出

### 需求 4：迁移脚本生成命令

**用户故事**：作为开发者，我希望从 SQLAlchemy 模型自动生成迁移脚本，以便减少手写 SQL 的错误。

#### 验收标准

1. WHEN 执行 `owlclaw db revision -m "message"` 时，THE CLI SHALL 调用 Alembic autogenerate 生成迁移脚本
2. WHEN 提供 `--empty` 参数时，THE CLI SHALL 生成空的迁移脚本模板
3. WHEN 生成成功时，THE CLI SHALL 显示新迁移脚本的文件路径和 Revision ID
4. WHEN 模型定义没有变化时，THE CLI SHALL 显示 "No changes detected" 消息
5. WHEN 生成的迁移脚本包含 DROP TABLE 操作时，THE CLI SHALL 显示警告提示
6. WHEN Database_URL 未配置时，THE CLI SHALL 显示配置错误消息

### 需求 5：迁移回滚命令

**用户故事**：作为开发者，我希望能够回滚数据库迁移，以便在迁移出错时恢复到之前的状态。

#### 验收标准

1. WHEN 执行 `owlclaw db rollback` 时，THE CLI SHALL 回滚一个 Migration 版本
2. WHEN 提供 `--target` 参数时，THE CLI SHALL 回滚到指定的 Revision
3. WHEN 提供 `--steps N` 参数时，THE CLI SHALL 回滚 N 个版本
4. WHEN 提供 `--dry-run` 参数时，THE CLI SHALL 显示将要回滚的迁移但不实际执行
5. WHEN 已经是最早版本时，THE CLI SHALL 显示 "Already at base revision" 消息
6. WHEN 回滚执行失败时，THE CLI SHALL 显示失败的 Revision 和错误详情
7. WHEN 回滚执行成功时，THE CLI SHALL 显示已回滚的 Revision 列表

### 需求 6：数据库备份命令

**用户故事**：作为系统管理员，我希望能够备份 owlclaw database，以便在数据丢失时恢复。

#### 验收标准

1. WHEN 执行 `owlclaw db backup --output <path>` 时，THE CLI SHALL 使用 pg_dump 备份 owlclaw database
2. WHEN 提供 `--format custom` 参数时，THE CLI SHALL 使用 custom 格式备份（支持 pg_restore）
3. WHEN 提供 `--schema-only` 参数时，THE CLI SHALL 只备份 schema 不备份数据
4. WHEN 提供 `--data-only` 参数时，THE CLI SHALL 只备份数据不备份 schema
5. WHEN 输出文件已存在时，THE CLI SHALL 询问是否覆盖
6. WHEN 备份执行成功时，THE CLI SHALL 显示备份文件路径和大小
7. WHEN 备份执行失败时，THE CLI SHALL 显示错误详情并删除不完整的备份文件
8. WHEN pg_dump 不可用时，THE CLI SHALL 显示安装 PostgreSQL 客户端工具的提示

### 需求 7：数据库恢复命令

**用户故事**：作为系统管理员，我希望能够从备份恢复数据库，以便在灾难发生时快速恢复服务。

#### 验收标准

1. WHEN 执行 `owlclaw db restore --input <path>` 时，THE CLI SHALL 从备份文件恢复数据
2. WHEN 备份文件是 SQL 格式时，THE CLI SHALL 使用 psql 执行恢复
3. WHEN 备份文件是 custom 格式时，THE CLI SHALL 使用 pg_restore 执行恢复
4. WHEN 目标数据库不为空时，THE CLI SHALL 显示警告并要求确认
5. WHEN 提供 `--clean` 参数时，THE CLI SHALL 在恢复前清空目标数据库
6. WHEN 恢复执行成功时，THE CLI SHALL 显示恢复的表数量和行数
7. WHEN 恢复执行失败时，THE CLI SHALL 显示错误详情和回滚建议
8. WHEN 备份文件不存在时，THE CLI SHALL 显示文件不存在错误

### 需求 8：数据库健康检查命令

**用户故事**：作为系统管理员，我希望能够执行数据库健康检查，以便及时发现潜在问题。

#### 验收标准

1. WHEN 执行 `owlclaw db check` 时，THE CLI SHALL 检查数据库连接响应时间
2. WHEN 执行 `owlclaw db check` 时，THE CLI SHALL 检查 Migration 是否为最新版本
3. WHEN 执行 `owlclaw db check` 时，THE CLI SHALL 检查 pgvector 扩展是否已安装
4. WHEN 执行 `owlclaw db check` 时，THE CLI SHALL 检查 Connection_Pool 使用率
5. WHEN 执行 `owlclaw db check` 时，THE CLI SHALL 检查磁盘使用率是否超过阈值
6. WHEN 执行 `owlclaw db check` 时，THE CLI SHALL 检查最近一小时内的慢查询数量
7. WHEN 所有检查项通过时，THE CLI SHALL 显示 "Overall: HEALTHY" 状态
8. WHEN 有检查项失败时，THE CLI SHALL 显示 "Overall: UNHEALTHY" 状态和失败项详情
9. WHEN 有检查项警告时，THE CLI SHALL 显示 "Overall: HEALTHY (N warnings)" 状态

### 需求 9：配置读取

**用户故事**：作为用户，我希望 CLI 能够从环境变量和配置文件读取数据库连接信息，以便在不同环境中灵活部署。

#### 验收标准

1. WHEN 设置了 OWLCLAW_DATABASE_URL 环境变量时，THE CLI SHALL 使用它作为 Database_URL
2. WHEN 未设置 OWLCLAW_DATABASE_URL 时，THE CLI SHALL 从配置文件读取 database.url
3. WHEN 命令行提供 `--database-url` 参数时，THE CLI SHALL 使用它而不是环境变量或配置文件
4. WHEN 所有配置源都未提供 Database_URL 时，THE CLI SHALL 显示配置错误消息
5. WHERE 命令需要 Admin_URL 时，WHEN 提供 `--admin-url` 参数时，THE CLI SHALL 使用指定的 Admin_URL
6. WHERE 命令需要 Admin_URL 时，WHEN 未提供 `--admin-url` 参数时，THE CLI SHALL 显示参数缺失错误

### 需求 10：错误处理和用户体验

**用户故事**：作为用户，我希望 CLI 能够提供清晰的错误消息和进度提示，以便快速诊断和解决问题。

#### 验收标准

1. WHEN 命令执行时间超过 2 秒时，THE CLI SHALL 显示进度指示器
2. WHEN 命令执行成功时，THE CLI SHALL 以退出码 0 退出
3. WHEN 命令执行失败时，THE CLI SHALL 以非零退出码退出
4. WHEN 发生错误时，THE CLI SHALL 显示错误类型和详细消息
5. WHEN 发生连接错误时，THE CLI SHALL 显示主机、端口和连接失败原因
6. WHEN 发生认证错误时，THE CLI SHALL 显示用户名和数据库名（不显示密码）
7. WHEN 用户按 Ctrl+C 中断命令时，THE CLI SHALL 清理临时资源并优雅退出
8. WHEN 命令需要确认时，THE CLI SHALL 显示提示并等待用户输入 yes/no
9. WHEN 提供 `--yes` 参数时，THE CLI SHALL 跳过所有确认提示自动执行
10. WHEN 提供 `--verbose` 参数时，THE CLI SHALL 显示详细的执行日志

### 需求 11：Alembic API 封装

**用户故事**：作为开发者，我希望 CLI 直接调用 Alembic API 而不是执行 alembic 命令行，以便提供更好的错误处理和用户体验。

#### 验收标准

1. THE CLI SHALL 使用 alembic.config.Config 类加载 Alembic 配置
2. THE CLI SHALL 使用 alembic.command 模块执行迁移操作
3. THE CLI SHALL 捕获 Alembic 异常并转换为用户友好的错误消息
4. THE CLI SHALL 在执行 Alembic 操作前验证 migrations 目录存在
5. THE CLI SHALL 在执行 Alembic 操作前验证 alembic.ini 文件存在
6. WHEN Alembic 配置文件不存在时，THE CLI SHALL 显示初始化 Alembic 的指导消息

### 需求 12：命令行参数验证

**用户故事**：作为用户，我希望 CLI 能够验证命令行参数的有效性，以便在执行前发现参数错误。

#### 验收标准

1. WHEN Database_URL 格式无效时，THE CLI SHALL 显示格式错误和正确格式示例
2. WHEN Admin_URL 格式无效时，THE CLI SHALL 显示格式错误和正确格式示例
3. WHEN 提供的文件路径不存在时，THE CLI SHALL 显示文件不存在错误
4. WHEN 提供的目录路径不存在时，THE CLI SHALL 询问是否创建目录
5. WHEN `--steps` 参数不是正整数时，THE CLI SHALL 显示参数类型错误
6. WHEN `--format` 参数不是支持的格式时，THE CLI SHALL 显示支持的格式列表
7. WHEN 互斥参数同时提供时，THE CLI SHALL 显示参数冲突错误

