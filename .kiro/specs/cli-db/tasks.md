# 实现计划：CLI 数据库运维工具

## 概述

本实现计划将 CLI 数据库运维工具分解为一系列增量开发任务。每个任务都是可独立完成的代码单元，并在完成后进行测试验证。实现将按照优先级进行：P0（MVP 必需）→ P1（开发必需）→ P2（运维增强）。

## 任务

- [ ] 1. 设置 CLI 基础设施和配置模块
  - 安装依赖：typer、rich、pyyaml
  - 创建 owlclaw/cli/ 目录结构
  - 实现配置读取模块（config.py）：支持环境变量、配置文件、命令行参数
  - 实现输出格式化模块（output.py）：使用 rich 库提供美观输出
  - 实现异常处理模块（exceptions.py）：定义 CLI 异常类
  - _需求：9.1, 9.2, 9.3, 9.4, 10.4, 10.5, 10.6_

- [ ]* 1.1 为配置读取编写属性测试
  - **属性 1：配置优先级一致性**
  - **验证需求：9.1, 9.2, 9.3**

- [ ] 2. 实现 CLI 主入口和 db 子命令组
  - 更新 owlclaw/cli/__init__.py：创建 Typer 应用
  - 创建 owlclaw/cli/db.py：定义 db 子命令组
  - 注册 db 子命令组到主应用
  - 测试 `owlclaw --help` 和 `owlclaw db --help` 输出
  - _需求：无（基础设施）_

- [ ] 3. 实现 init 命令（P0）
  - [ ] 3.1 实现 db_init.py 核心逻辑
    - 实现 init_command 函数：接受参数（admin-url、owlclaw-password、hatchet-password、skip-hatchet、dry-run）
    - 实现 SQL 语句构建：创建 database、role、extension
    - 实现密码生成：使用 secrets 模块生成随机密码
    - 实现 dry-run 模式：显示 SQL 但不执行
    - _需求：1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_
  
  - [ ] 3.2 实现 init 命令的数据库操作
    - 使用 asyncpg 连接到 admin database
    - 执行 database 和 role 创建
    - 切换到 owlclaw database 启用 pgvector 扩展
    - 处理 database 已存在的情况：显示警告并询问确认
    - _需求：1.1, 1.2, 1.3, 1.9_
  
  - [ ] 3.3 实现 init 命令的错误处理
    - 捕获连接错误：显示主机和端口
    - 捕获认证错误：显示用户名和数据库名
    - 捕获扩展安装错误：提示 pgvector 未安装
    - _需求：1.8_
  
  - [ ]* 3.4 为 init 命令编写单元测试
    - 测试成功场景：database、role、extension 创建
    - 测试 --skip-hatchet 参数
    - 测试 --dry-run 模式
    - 测试 database 已存在场景
    - 测试连接失败场景
    - _需求：1.1-1.10_

- [ ] 4. 实现 migrate 命令（P0）
  - [ ] 4.1 实现 db_migrate.py 核心逻辑
    - 实现 migrate_command 函数：接受参数（target、database-url、dry-run）
    - 加载 Alembic 配置：从 alembic.ini 读取
    - 获取待执行的迁移列表
    - 实现 dry-run 模式：显示迁移列表但不执行
    - _需求：2.1, 2.2, 2.3, 2.4_
  
  - [ ] 4.2 实现 migrate 命令的 Alembic 集成
    - 调用 Alembic API：command.upgrade()
    - 处理无待执行迁移场景：显示 "Already up to date"
    - 处理迁移失败：显示失败的 Revision 和错误详情
    - 显示成功应用的 Revision 列表
    - _需求：2.5, 2.6, 2.7_
  
  - [ ] 4.3 实现 migrate 命令的配置验证
    - 验证 Database_URL 配置
    - 验证 alembic.ini 文件存在
    - 验证 migrations 目录存在
    - _需求：2.8, 11.4, 11.5_
  
  - [ ]* 4.4 为 migrate 命令编写单元测试
    - 测试成功迁移场景
    - 测试 --target 参数
    - 测试 --dry-run 模式
    - 测试无待执行迁移场景
    - 测试迁移失败场景
    - 测试配置缺失场景
    - _需求：2.1-2.8_

- [ ] 5. 实现 status 命令（P0）
  - [ ] 5.1 实现 db_status.py 核心逻辑
    - 实现 status_command 函数：接受参数（database-url）
    - 收集数据库状态信息：连接、版本、扩展、迁移、表统计、磁盘使用
    - 格式化输出：使用 rich 表格或格式化文本
    - _需求：3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_
  
  - [ ] 5.2 实现 status 命令的数据库查询
    - 查询 PostgreSQL 版本：SELECT version()
    - 查询已安装扩展：SELECT FROM pg_extension
    - 查询表统计：SELECT FROM pg_stat_user_tables
    - 查询磁盘使用：pg_database_size()
    - 查询当前迁移版本：从 alembic_version 表
    - _需求：3.2, 3.3, 3.4, 3.5, 3.6, 3.7_
  
  - [ ] 5.3 实现 status 命令的错误处理
    - 处理连接失败：显示错误并退出
    - 隐藏密码：使用 mask_password 函数
    - _需求：3.1, 3.8_
  
  - [ ]* 5.4 为 status 命令编写单元测试
    - 测试成功场景：显示所有状态信息
    - 测试连接失败场景
    - 测试密码隐藏
    - _需求：3.1-3.8_

- [ ] 6. Checkpoint - 确保 P0 命令测试通过
  - 运行所有 P0 命令的测试
  - 手动测试 init、migrate、status 命令
  - 确认所有测试通过，询问用户是否有问题

- [ ] 7. 实现 revision 命令（P1）
  - [ ] 7.1 实现 db_revision.py 核心逻辑
    - 实现 revision_command 函数：接受参数（message、empty、database-url）
    - 调用 Alembic API：command.revision() 或 autogenerate
    - 获取生成的迁移文件路径和 Revision ID
    - 显示成功消息
    - _需求：4.1, 4.2, 4.3_
  
  - [ ] 7.2 实现 revision 命令的危险操作检测
    - 检查生成的迁移脚本内容
    - 检测 DROP TABLE、DROP COLUMN 操作
    - 显示警告提示
    - _需求：4.5_
  
  - [ ] 7.3 实现 revision 命令的边缘情况处理
    - 处理无模型变化场景：显示 "No changes detected"
    - 处理配置缺失场景
    - _需求：4.4, 4.6_
  
  - [ ]* 7.4 为 revision 命令编写单元测试
    - 测试 autogenerate 场景
    - 测试 --empty 参数
    - 测试无变化场景
    - 测试危险操作检测
    - _需求：4.1-4.6_

- [ ] 8. 实现 rollback 命令（P1）
  - [ ] 8.1 实现 db_rollback.py 核心逻辑
    - 实现 rollback_command 函数：接受参数（target、steps、database-url、dry-run、yes）
    - 验证参数：target 和 steps 不能同时使用
    - 计算目标版本：根据 target 或 steps
    - 获取将要回滚的迁移列表
    - _需求：5.1, 5.2, 5.3_
  
  - [ ] 8.2 实现 rollback 命令的确认和执行
    - 显示将要回滚的迁移列表
    - 询问用户确认（除非 --yes）
    - 调用 Alembic API：command.downgrade()
    - 显示成功回滚的 Revision 列表
    - _需求：5.1, 5.7_
  
  - [ ] 8.3 实现 rollback 命令的边缘情况处理
    - 处理已是最早版本场景：显示 "Already at base revision"
    - 处理回滚失败：显示失败的 Revision 和错误详情
    - 实现 dry-run 模式
    - _需求：5.4, 5.5, 5.6_
  
  - [ ]* 8.4 为 rollback 命令编写单元测试
    - 测试回滚一个版本
    - 测试 --target 参数
    - 测试 --steps 参数
    - 测试 --dry-run 模式
    - 测试确认提示
    - 测试已是最早版本场景
    - _需求：5.1-5.7_

- [ ] 9. Checkpoint - 确保 P1 命令测试通过
  - 运行所有 P1 命令的测试
  - 手动测试 revision、rollback 命令
  - 确认所有测试通过，询问用户是否有问题

- [ ] 10. 实现 backup 命令（P2）
  - [ ] 10.1 实现 db_backup.py 核心逻辑
    - 实现 backup_command 函数：接受参数（output、format、schema-only、data-only、database-url）
    - 验证参数：schema-only 和 data-only 不能同时使用
    - 验证 format 参数：只支持 plain 和 custom
    - 检查 pg_dump 是否可用
    - _需求：6.1, 6.2, 6.3, 6.4, 6.8_
  
  - [ ] 10.2 实现 backup 命令的文件处理
    - 检查输出文件是否已存在：询问是否覆盖
    - 构建 pg_dump 命令
    - 执行 pg_dump：使用 subprocess
    - 处理备份失败：删除不完整的备份文件
    - _需求：6.5, 6.7_
  
  - [ ] 10.3 实现 backup 命令的成功输出
    - 显示备份文件路径
    - 显示文件大小
    - _需求：6.6_
  
  - [ ]* 10.4 为 backup 命令编写单元测试
    - 测试成功备份场景
    - 测试 --format custom 参数
    - 测试 --schema-only 参数
    - 测试文件已存在场景
    - 测试 pg_dump 不可用场景
    - _需求：6.1-6.8_

- [ ] 11. 实现 restore 命令（P2）
  - [ ] 11.1 实现 db_restore.py 核心逻辑
    - 实现 restore_command 函数：接受参数（input、clean、database-url、yes）
    - 检查备份文件是否存在
    - 检测备份文件格式：SQL 或 custom
    - 检查目标数据库是否为空
    - _需求：7.1, 7.2, 7.3, 7.4, 7.8_
  
  - [ ] 11.2 实现 restore 命令的确认和执行
    - 显示警告：将要恢复数据库
    - 询问用户确认（除非 --yes）
    - 执行恢复：使用 psql 或 pg_restore
    - 处理 --clean 参数
    - _需求：7.4, 7.5_
  
  - [ ] 11.3 实现 restore 命令的成功输出和错误处理
    - 显示恢复的表数量和行数
    - 处理恢复失败：显示错误详情和回滚建议
    - _需求：7.6, 7.7_
  
  - [ ]* 11.4 为 restore 命令编写单元测试
    - 测试从 SQL 文件恢复
    - 测试从 custom 格式恢复
    - 测试 --clean 参数
    - 测试数据库不为空场景
    - 测试备份文件不存在场景
    - _需求：7.1-7.8_

- [ ] 12. 实现 check 命令（P2）
  - [ ] 12.1 实现 db_check.py 核心逻辑
    - 实现 check_command 函数：接受参数（database-url）
    - 实现健康检查框架：运行多个检查项
    - 收集检查结果：状态（OK/WARN/ERROR）和消息
    - _需求：8.1-8.6_
  
  - [ ] 12.2 实现各项健康检查
    - 连接检查：测量响应时间
    - 迁移检查：检查是否为最新版本
    - pgvector 检查：检查扩展是否已安装
    - 连接池检查：检查使用率
    - 磁盘使用检查：检查是否超过阈值
    - 慢查询检查：检查最近一小时的慢查询
    - _需求：8.1, 8.2, 8.3, 8.4, 8.5, 8.6_
  
  - [ ] 12.3 实现 check 命令的输出
    - 格式化健康检查报告
    - 显示每个检查项的状态和消息
    - 计算总体状态：HEALTHY / HEALTHY (N warnings) / UNHEALTHY
    - 根据总体状态设置退出码
    - _需求：8.7, 8.8, 8.9_
  
  - [ ]* 12.4 为 check 命令编写单元测试
    - 测试所有检查项通过场景
    - 测试有警告场景
    - 测试有错误场景
    - 测试各个检查项的逻辑
    - _需求：8.1-8.9_

- [ ] 13. 实现通用功能和属性测试
  - [ ]* 13.1 为退出码编写属性测试
    - **属性 2：退出码正确性**
    - **验证需求：10.2, 10.3**
  
  - [ ]* 13.2 为参数验证编写属性测试
    - **属性 3：参数验证一致性**
    - **验证需求：12.1-12.7**
  
  - [ ] 13.3 实现通用的用户体验功能
    - 实现进度指示器：超过 2 秒显示
    - 实现 Ctrl+C 处理：优雅退出并清理资源
    - 实现 --verbose 参数：显示详细日志
    - _需求：10.1, 10.7, 10.10_

- [ ] 14. 集成测试和文档
  - [ ]* 14.1 编写集成测试
    - 测试完整的 init → migrate → status 流程
    - 测试完整的 backup → restore 流程
    - 测试完整的 revision → migrate → rollback 流程
  
  - [ ] 14.2 更新项目文档
    - 更新 README.md：添加 CLI 使用说明
    - 创建 CLI 命令参考文档
    - 添加常见问题和故障排除指南

- [ ] 15. Final Checkpoint - 确保所有测试通过
  - 运行所有单元测试
  - 运行所有属性测试
  - 运行所有集成测试
  - 手动测试所有命令
  - 确认所有测试通过，询问用户是否有问题

## 注意事项

- 标记 `*` 的任务为可选测试任务，可以跳过以加快 MVP 开发
- 每个任务引用了具体的需求编号，便于追溯
- 任务按优先级组织：P0（任务 1-6）→ P1（任务 7-9）→ P2（任务 10-12）
- Checkpoint 任务确保增量验证，及时发现问题
- 属性测试验证通用正确性属性，单元测试验证具体场景

