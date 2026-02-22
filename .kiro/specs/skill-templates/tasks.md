# 实施计划：SKILL.md 模板库

## 概述

本实施计划将 SKILL.md 模板库系统的设计转换为可执行的开发任务。系统采用 Python 实现，提供 4 个核心组件（TemplateRegistry、TemplateRenderer、TemplateValidator、TemplateSearcher），15 个模板（5 个类别，每个类别 3 个模板），以及与 OwlClaw CLI 的集成。

实施将按照从核心功能到高级特性的顺序进行，每个阶段都包含相应的测试任务，确保增量验证和质量保证。

## 任务

- [x] 1. 设置项目结构和核心数据模型
  - [x] 创建项目目录结构（owlclaw/templates/skills/, owlclaw/templates/skills/templates/）
  - [x] 创建 5 个类别目录（monitoring/, analysis/, workflow/, integration/, report/）
  - [x] 定义核心数据类（TemplateMetadata, TemplateParameter, TemplateCategory, ValidationError, SearchResult）
  - [x] 定义自定义异常（TemplateNotFoundError, MissingParameterError, ParameterTypeError, ParameterValueError, TemplateRenderError）
  - [x] 配置 Python 类型注解和 mypy
  - [x] 设置测试框架（pytest）和属性测试库（hypothesis）
  - _需求：FR-1, FR-2_

- [x] 2. 实现 TemplateRegistry 组件
  - [x] 2.1 创建 TemplateRegistry 类和模板加载
    - 实现 __init__ 方法初始化注册表
    - 实现 _load_templates 方法递归扫描模板目录
    - 实现 _parse_template_metadata 方法从 Jinja2 注释提取元数据
    - 解析元数据字段（name, description, tags, parameters, examples）
    - 处理模板加载失败（跳过无效模板，记录错误）
    - _需求：FR-1.1, FR-1.2_
  
  - [ ]* 2.2 为模板注册编写属性测试
    - **属性 1：模板注册完整性**
    - **验证需求：FR-1.1**
    - 对于任意模板目录，所有有效的 .md.j2 文件都应该被注册
  
  - [ ]* 2.3 为模板元数据编写属性测试
    - **属性 2：模板元数据完整性**
    - **验证需求：FR-1.2**
    - 对于任意注册的模板，元数据应该包含所有必需字段
  
  - [ ]* 2.4 为模板分类编写属性测试
    - **属性 3：模板分类正确性**
    - **验证需求：FR-1.3**
    - 对于任意模板，类别应该与所在目录一致


  - [x] 2.5 实现模板检索方法
    - 实现 get_template(template_id) 方法获取特定模板
    - 实现 list_templates(category, tags) 方法列出和过滤模板
    - 实现 search_templates(query) 方法搜索模板
    - 处理模板不存在的情况（返回 None 或抛出异常）
    - _需求：FR-1.1, FR-4.1, FR-4.2_
  
  - [ ]* 2.6 为模板列表编写属性测试
    - **属性 22：模板列表完整性**
    - **验证需求：FR-1.5**
    - 对于任意类别，列出该类别的模板时应该包含所有有效模板
  
  - [ ]* 2.7 为模板参数定义编写属性测试
    - **属性 4：模板参数定义完整性**
    - **验证需求：FR-1.4**
    - 对于任意模板参数，应该包含名称、类型、描述和是否必需的信息

- [x] 3. 实现 TemplateRenderer 组件
  - [x] 3.1 创建 TemplateRenderer 类和 Jinja2 集成
    - 初始化 Jinja2 Environment 和 FileSystemLoader
    - 配置环境（trim_blocks=True, lstrip_blocks=True）
    - 注册自定义过滤器（kebab_case, snake_case）
    - 实现 _get_template_path 方法获取模板文件路径
    - _需求：FR-2.1_
  
  - [x] 3.2 实现参数验证和转换
    - 实现 _validate_parameters 方法验证必需参数
    - 实现 _apply_defaults 方法应用默认值
    - 实现 _validate_and_convert_parameters 方法类型转换
    - 实现 _validate_parameter_choices 方法验证参数选项
    - 处理参数验证失败（抛出明确的错误）
    - _需求：FR-2.2, FR-2.3_
  
  - [ ]* 3.3 为必需参数验证编写属性测试
    - **属性 7：必需参数验证**
    - **验证需求：FR-2.3**
    - 对于任意模板，缺少必需参数应该失败并返回明确错误
  
  - [ ]* 3.4 为默认参数应用编写属性测试
    - **属性 8：默认参数应用**
    - **验证需求：FR-2.4**
    - 对于任意模板参数，有默认值且未提供值时应该使用默认值
  
  - [ ]* 3.5 为参数类型验证编写属性测试
    - **属性 23：参数类型验证**
    - **验证需求：FR-2.7**
    - 对于任意模板参数，类型不匹配应该失败或自动转换
  
  - [ ]* 3.6 为参数选项验证编写属性测试
    - **属性 24：参数选项验证**
    - **验证需求：FR-2.8**
    - 对于任意带 choices 的参数，值不在选项中应该失败


  - [x] 3.7 实现模板渲染方法
    - 实现 render(template_id, parameters) 方法
    - 加载 Jinja2 模板
    - 应用参数验证和默认值
    - 执行模板渲染
    - 捕获 Jinja2 异常并转换为 TemplateRenderError
    - _需求：FR-2.1, FR-2.2_
  
  - [ ]* 3.8 为模板渲染幂等性编写属性测试
    - **属性 5：模板渲染幂等性**
    - **验证需求：FR-2.1**
    - 对于任意模板和参数，多次渲染应该产生相同输出
  
  - [ ]* 3.9 为参数替换完整性编写属性测试
    - **属性 6：模板参数替换完整性**
    - **验证需求：FR-2.2**
    - 渲染后的输出不应该包含未替换的 Jinja2 占位符
  
  - [x] 3.10 实现自定义过滤器
    - 实现 _kebab_case 静态方法（转换为 kebab-case）
    - 实现 _snake_case 静态方法（转换为 snake_case）
    - 处理特殊字符和空格
    - 确保连字符/下划线不在开头或结尾
    - _需求：FR-2.5, FR-2.6_
  
  - [ ]* 3.11 为 kebab-case 转换编写属性测试
    - **属性 20：Kebab-case 转换正确性**
    - **验证需求：FR-2.5**
    - 对于任意字符串，应该转换为小写字母、数字和连字符
  
  - [ ]* 3.12 为 snake-case 转换编写属性测试
    - **属性 21：Snake-case 转换正确性**
    - **验证需求：FR-2.6**
    - 对于任意字符串，应该转换为小写字母、数字和下划线

- [x] 4. 检查点 - 确保基础组件测试通过
  - [x] 确保所有测试通过

- [x] 5. 实现 TemplateValidator 组件
  - [x] 5.1 创建 TemplateValidator 类和模板验证
    - 实现 validate_template(template_path) 方法验证模板文件
    - 验证元数据注释块存在（{# ... #} 格式）
    - 验证 Jinja2 语法有效性（使用 Environment.parse）
    - 返回 ValidationError 列表
    - _需求：FR-3.1, FR-3.2_
  
  - [ ]* 5.2 为模板 Jinja2 语法编写属性测试
    - **属性 17：模板文件 Jinja2 语法有效性**
    - **验证需求：FR-5.1**
    - 对于任意模板文件，应该是有效的 Jinja2 模板
  
  - [ ]* 5.3 为模板元数据注释块编写属性测试
    - **属性 18：模板文件元数据注释块存在性**
    - **验证需求：FR-5.2**
    - 对于任意模板文件，应该包含元数据注释块


  - [x] 5.4 实现 SKILL.md 文件验证
    - 实现 validate_skill_file(skill_path) 方法验证生成的文件
    - 实现 _parse_skill_file 方法分离 frontmatter 和 body
    - 实现 _validate_frontmatter 方法验证 frontmatter
    - 实现 _validate_body 方法验证 Markdown body
    - 实现 _validate_trigger_syntax 方法验证 trigger 语法
    - _需求：FR-3.1, FR-3.2, FR-3.3_
  
  - [ ]* 5.5 为 frontmatter 有效性编写属性测试
    - **属性 9：生成文件 frontmatter 有效性**
    - **验证需求：FR-3.1**
    - 对于任意渲染后的文件，frontmatter 应该是有效的 YAML
  
  - [ ]* 5.6 为 name 格式编写属性测试
    - **属性 10：生成文件 name 格式正确性**
    - **验证需求：FR-3.2**
    - 对于任意渲染后的文件，name 字段应该符合 kebab-case 格式
  
  - [ ]* 5.7 为 trigger 语法编写属性测试
    - **属性 11：生成文件 trigger 语法正确性**
    - **验证需求：FR-3.3**
    - 对于任意包含 trigger 的文件，应该符合支持的语法
  
  - [ ]* 5.8 为 body 非空性编写属性测试
    - **属性 12：生成文件 body 非空性**
    - **验证需求：FR-3.4**
    - 对于任意渲染后的文件，body 应该不为空且包含标题
  
  - [x] 5.9 实现验证错误处理
    - 实现 validate_and_report 方法生成友好的错误报告
    - 按严重程度分类错误（error/warning）
    - 提供修复建议
    - _需求：FR-3.1, FR-3.2, FR-3.3_
  
  - [ ]* 5.10 为验证错误信息编写属性测试
    - **属性 19：验证错误信息明确性**
    - **验证需求：FR-5.3**
    - 对于任意验证失败，应该返回明确的错误信息

- [x] 6. 实现 TemplateSearcher 组件
  - [x] 6.1 创建 TemplateSearcher 类和搜索功能
    - 实现 __init__ 方法接收 TemplateRegistry
    - 实现 search(query, category, limit) 方法搜索模板
    - 实现 _calculate_relevance 方法计算相关性分数
    - 实现相关性算法（名称匹配、描述匹配、标签匹配、类别匹配）
    - 按相关性分数排序结果
    - _需求：FR-4.1, FR-4.2_
  
  - [ ]* 6.2 为搜索结果相关性编写属性测试
    - **属性 13：搜索结果相关性**
    - **验证需求：FR-4.1**
    - 对于任意搜索查询，结果应该按相关性分数降序排列
  
  - [ ]* 6.3 为搜索结果唯一性编写属性测试
    - **属性 14：搜索结果唯一性**
    - **验证需求：FR-4.2**
    - 对于任意搜索查询，结果列表不应该包含重复模板


  - [x] 6.4 实现过滤功能
    - 实现类别过滤（通过 TemplateRegistry.list_templates）
    - 实现标签过滤（通过 TemplateRegistry.list_templates）
    - 支持组合过滤（类别 + 标签 + 关键词）
    - _需求：FR-4.2, FR-4.3_
  
  - [ ]* 6.5 为类别过滤编写属性测试
    - **属性 15：类别过滤正确性**
    - **验证需求：FR-4.3**
    - 对于任意类别过滤，返回的模板类别都应该匹配
  
  - [ ]* 6.6 为标签过滤编写属性测试
    - **属性 16：标签过滤正确性**
    - **验证需求：FR-4.4**
    - 对于任意标签过滤，返回的模板都应该包含匹配标签
  
  - [ ]* 6.7 为搜索覆盖性编写属性测试
    - **属性 25：模板搜索覆盖性**
    - **验证需求：FR-4.5**
    - 对于任意模板，如果查询包含其关键词，应该出现在结果中
  
  - [x] 6.8 实现推荐功能（可选）
    - 实现 recommend(context, limit) 方法推荐模板
    - 基于上下文信息（use_case, existing_skills, tech_stack）
    - 实现简单的推荐算法
    - _需求：FR-4.1_

- [x] 7. 检查点 - 确保核心组件测试通过
  - [x] 确保所有测试通过

- [x] 8. 创建模板文件 - Monitoring 类别
  - [x] 8.1 创建 health-check.md.j2 模板
    - 定义元数据注释块（name, description, tags, parameters, examples）
    - 定义参数（skill_name, skill_description, check_interval, alert_threshold, endpoints）
    - 实现 frontmatter 部分（name, description, metadata, owlclaw）
    - 实现 Markdown body 部分（目标、检查项、告警策略、使用的工具、决策流程、注意事项）
    - 使用 Jinja2 语法（变量、条件、循环）
    - _需求：FR-1.1, FR-1.2, FR-1.3, FR-1.4_
  
  - [x] 8.2 创建 metric-monitor.md.j2 模板
    - 定义监控指标的模板
    - 参数：skill_name, skill_description, metrics, thresholds, check_interval
    - 实现指标监控逻辑
    - _需求：FR-1.1, FR-1.2, FR-1.3, FR-1.4_
  
  - [x] 8.3 创建 alert-handler.md.j2 模板
    - 定义告警处理的模板
    - 参数：skill_name, skill_description, alert_sources, notification_channels
    - 实现告警处理逻辑
    - _需求：FR-1.1, FR-1.2, FR-1.3, FR-1.4_


- [x] 9. 创建模板文件 - Analysis 类别
  - [x] 9.1 创建 data-analyzer.md.j2 模板
    - 定义数据分析的模板
    - 参数：skill_name, skill_description, data_sources, analysis_type, output_format
    - 实现数据分析逻辑
    - _需求：FR-1.1, FR-1.2, FR-1.3, FR-1.4_
  
  - [x] 9.2 创建 trend-detector.md.j2 模板
    - 定义趋势检测的模板
    - 参数：skill_name, skill_description, metrics, time_window, sensitivity
    - 实现趋势检测逻辑
    - _需求：FR-1.1, FR-1.2, FR-1.3, FR-1.4_
  
  - [x] 9.3 创建 anomaly-detector.md.j2 模板
    - 定义异常检测的模板
    - 参数：skill_name, skill_description, data_source, detection_method, threshold
    - 实现异常检测逻辑
    - _需求：FR-1.1, FR-1.2, FR-1.3, FR-1.4_

- [x] 10. 创建模板文件 - Workflow 类别
  - [x] 10.1 创建 approval-flow.md.j2 模板
    - 定义审批流程的模板
    - 参数：skill_name, skill_description, approval_stages, approvers, timeout
    - 实现审批流程逻辑
    - _需求：FR-1.1, FR-1.2, FR-1.3, FR-1.4_
  
  - [x] 10.2 创建 task-scheduler.md.j2 模板
    - 定义任务调度的模板
    - 参数：skill_name, skill_description, schedule_type, tasks, dependencies
    - 实现任务调度逻辑
    - _需求：FR-1.1, FR-1.2, FR-1.3, FR-1.4_
  
  - [x] 10.3 创建 event-handler.md.j2 模板
    - 定义事件处理的模板
    - 参数：skill_name, skill_description, event_types, handlers, filters
    - 实现事件处理逻辑
    - _需求：FR-1.1, FR-1.2, FR-1.3, FR-1.4_

- [x] 11. 创建模板文件 - Integration 类别
  - [x] 11.1 创建 api-client.md.j2 模板
    - 定义 API 客户端的模板
    - 参数：skill_name, skill_description, api_base_url, endpoints, auth_type
    - 实现 API 调用逻辑
    - _需求：FR-1.1, FR-1.2, FR-1.3, FR-1.4_
  
  - [x] 11.2 创建 webhook-handler.md.j2 模板
    - 定义 Webhook 处理的模板
    - 参数：skill_name, skill_description, webhook_path, payload_format, validation
    - 实现 Webhook 处理逻辑
    - _需求：FR-1.1, FR-1.2, FR-1.3, FR-1.4_
  
  - [x] 11.3 创建 data-sync.md.j2 模板
    - 定义数据同步的模板
    - 参数：skill_name, skill_description, source, destination, sync_mode, schedule
    - 实现数据同步逻辑
    - _需求：FR-1.1, FR-1.2, FR-1.3, FR-1.4_


- [x] 12. 创建模板文件 - Report 类别
  - [x] 12.1 创建 daily-report.md.j2 模板
    - 定义日报生成的模板
    - 参数：skill_name, skill_description, data_sources, report_sections, recipients
    - 实现日报生成逻辑
    - _需求：FR-1.1, FR-1.2, FR-1.3, FR-1.4_
  
  - [x] 12.2 创建 summary-generator.md.j2 模板
    - 定义摘要生成的模板
    - 参数：skill_name, skill_description, content_source, summary_length, format
    - 实现摘要生成逻辑
    - _需求：FR-1.1, FR-1.2, FR-1.3, FR-1.4_
  
  - [x] 12.3 创建 notification-sender.md.j2 模板
    - 定义通知发送的模板
    - 参数：skill_name, skill_description, notification_type, channels, template
    - 实现通知发送逻辑
    - _需求：FR-1.1, FR-1.2, FR-1.3, FR-1.4_

- [x] 13. 检查点 - 确保所有模板文件有效
  - [x] 使用 TemplateValidator 验证所有 15 个模板文件
  - 确保所有模板包含有效的元数据注释块
  - 确保所有模板是有效的 Jinja2 模板
  - 如有问题请询问用户

- [x] 14. 实现 CLI 集成 - owlclaw skill init 命令
  - [x] 14.1 创建 CLI 命令入口
    - 在 owlclaw/cli/commands/ 创建 skill.py 文件
    - 实现 skill 命令组（使用 Click）
    - 实现 init 子命令
    - 添加命令行参数（--category, --template, --name, --output）
    - _需求：FR-3, FR-4_
  
  - [x] 14.2 实现交互式向导
    - 实现类别选择（使用 Click.prompt 或 questionary）
    - 实现模板选择（展示模板列表）
    - 实现参数收集（根据模板参数定义）
    - 实现参数验证（类型、必需、choices）
    - 提供友好的提示和帮助信息
    - _需求：NFR-4_
  
  - [x] 14.3 实现模板渲染和文件生成
    - 调用 TemplateRegistry 获取模板
    - 调用 TemplateRenderer 渲染模板
    - 写入到 capabilities/ 目录
    - 自动调用 TemplateValidator 验证生成的文件
    - 显示成功消息和下一步提示
    - _需求：FR-2, FR-3_
  
  - [x] 14.4 实现非交互模式
    - 支持通过命令行参数提供所有参数
    - 支持从 JSON/YAML 文件加载参数
    - 用于自动化和 CI/CD 集成
    - _需求：NFR-4_


- [x] 15. 实现 CLI 集成 - owlclaw skill validate 命令
  - [x] 15.1 创建 validate 子命令
    - 实现 validate 子命令
    - 添加命令行参数（--file, --directory）
    - 支持验证单个文件或整个目录
    - _需求：FR-3_
  
  - [x] 15.2 实现验证逻辑
    - 调用 TemplateValidator.validate_skill_file
    - 显示验证结果（成功/失败）
    - 显示错误和警告列表
    - 提供修复建议
    - 设置正确的退出码（0 成功，1 失败）
    - _需求：FR-3.1, FR-3.2, FR-3.3_
  
  - [x] 15.3 实现批量验证
    - 支持验证 capabilities/ 目录下所有 SKILL.md 文件
    - 显示验证摘要（总数、成功、失败）
    - 支持 --strict 模式（警告也视为失败）
    - _需求：FR-3_

- [x] 16. 实现 CLI 集成 - owlclaw skill templates 命令（模板列表）
  - [x] 16.1 创建 templates 子命令
    - 实现 list 子命令
    - 添加命令行参数（--category, --tags, --search）
    - 支持过滤和搜索
    - _需求：FR-4_
  
  - [x] 16.2 实现模板列表显示
    - 调用 TemplateRegistry.list_templates 或 TemplateSearcher.search
    - 以表格形式显示模板列表（ID、名称、类别、描述）
    - 支持 --verbose 模式显示详细信息（参数、示例）
    - 支持 --json 模式输出 JSON 格式
    - _需求：FR-4.1, FR-4.2, FR-4.3_
  
  - [x] 16.3 实现模板详情显示（--show）
    - 添加 --show <template-id> 参数显示模板详情
    - 显示完整的元数据、参数定义、使用示例
    - 显示模板文件路径
    - _需求：FR-4_

- [x] 17. 检查点 - 确保 CLI 功能测试通过
  - 测试 owlclaw skill init 命令（交互式和非交互式）
  - 测试 owlclaw skill validate 命令
  - 测试 owlclaw skill list 命令
  - 确保所有命令正常工作，如有问题请询问用户

- [x] 18. 实现错误处理和日志
  - [x] 18.1 实现统一的错误处理
    - 在所有组件中捕获异常
    - 转换为友好的错误消息
    - 记录详细的错误日志
    - 提供修复建议
    - _需求：NFR-1, NFR-2_
  
  - [x] 18.2 实现日志记录
    - 配置 Python logging
    - 记录关键操作（模板加载、渲染、验证）
    - 记录错误和警告
    - 支持不同的日志级别（DEBUG, INFO, WARNING, ERROR）
    - _需求：NFR-1_


- [x] 19. 实现性能优化
  - [x] 19.1 优化模板加载
    - 实现模板缓存（避免重复解析）
    - 实现延迟加载（按需加载模板内容）
    - 优化元数据解析性能
    - _需求：NFR-3_
  
  - [x] 19.2 优化模板渲染
    - 缓存 Jinja2 Environment
    - 缓存编译后的模板
    - 优化参数验证性能
    - _需求：NFR-3_
  
  - [ ]* 19.3 编写性能测试
    - 测试加载所有模板的时间（目标 < 1 秒）
    - 测试渲染单个模板的时间（目标 < 100ms）
    - 测试搜索模板的时间（目标 < 200ms）
    - 测试验证文件的时间（目标 < 500ms）
    - _需求：NFR-3_

- [x] 20. 编写单元测试
  - [x] 20.1 为 TemplateRegistry 编写单元测试
    - 测试从目录加载模板
    - 测试通过 ID 获取模板
    - 测试列出和过滤模板
    - 测试搜索模板
    - 测试模板不存在的情况
    - _需求：FR-1_
  
  - [x] 20.2 为 TemplateRenderer 编写单元测试
    - 测试使用参数渲染模板
    - 测试缺少必需参数
    - 测试参数类型转换
    - 测试参数选项验证
    - 测试默认值应用
    - 测试自定义过滤器（kebab_case, snake_case）
    - 测试模板渲染错误
    - _需求：FR-2_
  
  - [x] 20.3 为 TemplateValidator 编写单元测试
    - 测试验证有效的模板文件
    - 测试验证无效的模板文件
    - 测试验证有效的 SKILL.md 文件
    - 测试验证无效的 SKILL.md 文件
    - 测试 frontmatter 验证
    - 测试 trigger 语法验证
    - 测试 body 验证
    - _需求：FR-3_
  
  - [x] 20.4 为 TemplateSearcher 编写单元测试
    - 测试关键词搜索
    - 测试类别过滤
    - 测试标签过滤
    - 测试组合过滤
    - 测试相关性排序
    - 测试结果唯一性
    - _需求：FR-4_


- [x] 21. 编写集成测试
  - [x] 21.1 编写端到端测试 - 完整流程
    - 创建完整的模板创建流程测试
    - 从模板注册到渲染到验证
    - 验证生成的 SKILL.md 文件正确
    - 验证文件可以被 Skills 加载器加载
    - _需求：所有功能需求_
  
  - [x] 21.2 编写 CLI 集成测试
    - 测试 owlclaw skill init 命令完整流程
    - 测试 owlclaw skill validate 命令
    - 测试 owlclaw skill list 命令
    - 测试命令行参数和选项
    - _需求：FR-3, FR-4_
  
  - [x] 21.3 编写错误场景测试
    - 测试模板文件不存在
    - 测试模板语法错误
    - 测试参数验证失败
    - 测试渲染错误
    - 测试验证失败
    - 验证系统继续正常运行
    - _需求：NFR-1_

- [x] 22. 创建配置文件和示例
  - [x] 22.1 创建配置文件模板
    - 创建 config/templates.example.yaml 示例配置
    - 包含模板目录配置
    - 包含验证规则配置
    - 添加详细的配置说明注释
    - _需求：NFR-2_
  
  - [x] 22.2 创建使用示例
    - 创建 examples/skill-templates/ 目录
    - 示例 1：使用 CLI 创建监控 Skill
    - 示例 2：使用 CLI 创建分析 Skill
    - 示例 3：使用 API 创建自定义模板
    - 示例 4：验证和修复 SKILL.md 文件
    - 示例 5：搜索和浏览模板
    - _需求：NFR-4_

- [x] 23. 编写文档
  - [x] 23.1 编写 API 文档
    - 为所有公开类和方法添加文档字符串
    - 使用 Google 风格或 NumPy 风格
    - 包含参数说明、返回值说明和示例
    - 生成 API 文档（使用 Sphinx 或 MkDocs）
    - _需求：NFR-2, NFR-4_
  
  - [x] 23.2 编写用户指南
    - 创建 docs/templates/user-guide.md 用户指南
    - 包含快速开始指南（< 5 分钟）
    - 包含 CLI 命令说明
    - 包含模板使用指南
    - 包含最佳实践
    - 包含故障排查
    - _需求：NFR-4_
  
  - [x] 23.3 编写模板开发指南
    - 创建 docs/templates/template-development.md 开发指南
    - 包含模板文件格式说明
    - 包含元数据定义规范
    - 包含 Jinja2 语法指南
    - 包含模板测试指南
    - 包含模板审查清单
    - _需求：NFR-2_


  - [x] 23.4 编写架构文档
    - 更新 docs/ARCHITECTURE.md 添加模板库说明
    - 包含设计决策说明
    - 包含组件架构图
    - 包含数据流图
    - 包含扩展点说明
    - _需求：NFR-2_
  
  - [x] 23.5 编写 CLI 使用文档
    - 创建 docs/cli/skill-commands.md CLI 文档
    - 包含所有命令的详细说明
    - 包含命令行参数和选项
    - 包含使用示例
    - 包含常见问题解答
    - _需求：NFR-4_

- [x] 24. 实现可维护性改进
  - [x] 24.1 实现模板版本管理
    - 在模板元数据中添加 version 字段
    - 实现版本兼容性检查
    - 提供模板升级指南
    - _需求：NFR-2_
  
  - [x] 24.2 实现模板测试工具
    - 创建 scripts/test_template.py 脚本
    - 支持测试单个模板
    - 支持测试所有模板
    - 验证模板可以正确渲染
    - 验证生成的文件通过验证
    - _需求：NFR-2_
  
  - [x] 24.3 实现模板审查工具
    - 创建 scripts/review_template.py 脚本
    - 检查模板元数据完整性
    - 检查模板参数定义
    - 检查模板文档质量
    - 生成审查报告
    - _需求：NFR-2_

- [x] 25. 最终检查点 - 确保所有测试通过并准备部署
  - 运行所有单元测试
  - 运行所有属性测试（每个至少 100 次迭代）
  - 运行所有集成测试
  - 检查测试覆盖率（目标 ≥ 80%）
  - 运行类型检查（mypy）
  - 运行代码格式检查（ruff 或 black）
  - 验证所有 15 个模板文件有效
  - 验证所有 CLI 命令正常工作
  - 验证文档完整性
  - 如有问题请询问用户

## 注意事项

- 标记为 `*` 的任务是可选的测试任务，可以跳过以加快 MVP 开发
- 每个任务都引用了具体的需求以确保可追溯性
- 检查点确保增量验证
- 属性测试验证通用正确性属性（每个至少 100 次迭代）
- 单元测试验证特定示例和边界情况
- 集成测试验证组件间的交互
- 所有代码使用 Python 3.10+ 和类型注解
- 遵循 PEP 8 代码风格
- 使用 pytest 作为测试框架
- 使用 hypothesis 作为属性测试框架
- 模板文件使用 Jinja2 语法
- 元数据使用 YAML 格式


## 依赖关系

```
1. 项目结构和数据模型
   ↓
2. TemplateRegistry ←─────┐
   ↓                      │
3. TemplateRenderer       │
   ↓                      │
4. 检查点 1               │
   ↓                      │
5. TemplateValidator      │
   ↓                      │
6. TemplateSearcher (依赖 2)
   ↓
7. 检查点 2
   ↓
8-12. 创建 15 个模板文件
   ↓
13. 检查点 3 - 验证模板
   ↓
14-16. CLI 集成
   ↓
17. 检查点 4 - CLI 测试
   ↓
18-19. 错误处理和性能优化
   ↓
20-21. 单元测试和集成测试
   ↓
22-24. 配置、文档和工具
   ↓
25. 最终检查点
```

## 预估工作量

- **Phase 1：核心组件**（任务 1-7）：1-2 天
  - TemplateRegistry, TemplateRenderer, TemplateValidator, TemplateSearcher
- **Phase 2：模板创建**（任务 8-13）：1-2 天
  - 15 个模板文件（5 个类别 × 3 个模板）
- **Phase 3：CLI 集成**（任务 14-17）：1 天
  - owlclaw skill init, validate, list 命令
- **Phase 4：测试和优化**（任务 18-21）：1-2 天
  - 错误处理、性能优化、单元测试、集成测试
- **Phase 5：文档和工具**（任务 22-25）：1 天
  - 配置文件、示例、文档、工具脚本

**总计**：5-7 天

## 验收标准

### 功能验收

- [ ] 可以从模板目录加载所有模板
- [ ] 可以通过 ID、类别、标签搜索模板
- [ ] 可以使用参数渲染模板生成 SKILL.md 文件
- [ ] 可以验证模板文件和生成的 SKILL.md 文件
- [ ] 提供 15 个模板（5 个类别，每个类别 3 个模板）
- [ ] owlclaw skill init 命令正常工作（交互式和非交互式）
- [ ] owlclaw skill validate 命令正常工作
- [ ] owlclaw skill list 命令正常工作
- [ ] 生成的 SKILL.md 文件符合 Agent Skills 规范
- [ ] 生成的 SKILL.md 文件可以被 Skills 加载器加载

### 性能验收

- [ ] 加载所有模板 < 1 秒
- [ ] 渲染单个模板 < 100ms
- [ ] 搜索模板 < 200ms
- [ ] 验证文件 < 500ms

### 质量验收

- [ ] 单元测试覆盖率 ≥ 80%
- [ ] 所有属性测试通过（每个至少 100 次迭代）
- [ ] 类型检查通过（mypy）
- [ ] 代码检查通过（ruff 或 black）
- [ ] 所有模板文件通过验证
- [ ] 文档完整（API 文档、用户指南、开发指南）


### 文档验收

- [ ] API 文档完整（所有公开接口有文档字符串）
- [ ] 用户指南完整（快速开始、CLI 命令、最佳实践、故障排查）
- [ ] 模板开发指南完整（格式说明、规范、测试指南、审查清单）
- [ ] 架构文档完整（设计决策、组件架构、数据流、扩展点）
- [ ] CLI 使用文档完整（命令说明、参数选项、示例、FAQ）
- [ ] 示例代码完整（至少 5 个典型场景）

### 可演示

- [ ] 可以演示从零创建一个监控类 Skill（< 5 分钟）
- [ ] 可以演示搜索和浏览模板
- [ ] 可以演示验证生成的文件
- [ ] 可以演示使用不同类别的模板
- [ ] 可以演示 CLI 的交互式和非交互式模式

## 属性测试清单

以下是所有 25 个正确性属性及其对应的测试任务：

1. **属性 1：模板注册完整性** - 任务 2.2
2. **属性 2：模板元数据完整性** - 任务 2.3
3. **属性 3：模板分类正确性** - 任务 2.4
4. **属性 4：模板参数定义完整性** - 任务 2.7
5. **属性 5：模板渲染幂等性** - 任务 3.8
6. **属性 6：模板参数替换完整性** - 任务 3.9
7. **属性 7：必需参数验证** - 任务 3.3
8. **属性 8：默认参数应用** - 任务 3.4
9. **属性 9：生成文件 frontmatter 有效性** - 任务 5.5
10. **属性 10：生成文件 name 格式正确性** - 任务 5.6
11. **属性 11：生成文件 trigger 语法正确性** - 任务 5.7
12. **属性 12：生成文件 body 非空性** - 任务 5.8
13. **属性 13：搜索结果相关性** - 任务 6.2
14. **属性 14：搜索结果唯一性** - 任务 6.3
15. **属性 15：类别过滤正确性** - 任务 6.5
16. **属性 16：标签过滤正确性** - 任务 6.6
17. **属性 17：模板文件 Jinja2 语法有效性** - 任务 5.2
18. **属性 18：模板文件元数据注释块存在性** - 任务 5.3
19. **属性 19：验证错误信息明确性** - 任务 5.10
20. **属性 20：Kebab-case 转换正确性** - 任务 3.11
21. **属性 21：Snake-case 转换正确性** - 任务 3.12
22. **属性 22：模板列表完整性** - 任务 2.6
23. **属性 23：参数类型验证** - 任务 3.5
24. **属性 24：参数选项验证** - 任务 3.6
25. **属性 25：模板搜索覆盖性** - 任务 6.7

## 模板清单

以下是需要创建的 15 个模板文件：

### Monitoring 类别（任务 8）
1. health-check.md.j2 - 健康检查监控
2. metric-monitor.md.j2 - 指标监控
3. alert-handler.md.j2 - 告警处理

### Analysis 类别（任务 9）
4. data-analyzer.md.j2 - 数据分析
5. trend-detector.md.j2 - 趋势检测
6. anomaly-detector.md.j2 - 异常检测

### Workflow 类别（任务 10）
7. approval-flow.md.j2 - 审批流程
8. task-scheduler.md.j2 - 任务调度
9. event-handler.md.j2 - 事件处理

### Integration 类别（任务 11）
10. api-client.md.j2 - API 客户端
11. webhook-handler.md.j2 - Webhook 处理
12. data-sync.md.j2 - 数据同步

### Report 类别（任务 12）
13. daily-report.md.j2 - 日报生成
14. summary-generator.md.j2 - 摘要生成
15. notification-sender.md.j2 - 通知发送

---

**维护者**：平台研发  
**最后更新**：2026-02-22
