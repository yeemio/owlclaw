# Requirements Document: cli-migrate

## 文档联动

- requirements: `.kiro/specs/cli-migrate/requirements.md`
- design: `.kiro/specs/cli-migrate/design.md`
- tasks: `.kiro/specs/cli-migrate/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


## Introduction

cli-migrate 是 OwlClaw 的 AI 辅助迁移工具，旨在帮助已有业务系统（Brownfield）快速接入 OwlClaw 的 AI 自主能力。该工具通过扫描已有项目代码，识别可接入的业务函数和 API，自动生成 OwlClaw 接入代码（@handler 注册）和对应的 SKILL.md 文档（遵循 Agent Skills 规范），从而实现零改造或最小改造接入。

根据 OwlClaw 的核心定位，cli-migrate 是实现"让已有业务系统获得 AI 自主能力"愿景的关键工具，降低业务开发者的接入门槛，使其无需深入学习 AI 框架即可让业务系统"活"起来。

## Glossary

- **CLI_Migrate**: 命令行迁移工具，用于扫描和生成 OwlClaw 接入代码
- **Scanner**: 代码扫描器，使用 AST 分析已有项目代码
- **Handler**: OwlClaw 的能力注册装饰器（@handler），用于注册业务函数
- **SKILL.md**: 遵循 Agent Skills 规范的业务知识文档
- **Brownfield_Project**: 已有的成熟业务系统
- **Migration_Report**: 迁移分析报告，包含可接入函数列表和建议
- **Dry_Run_Mode**: 预览模式，生成代码但不写入文件系统
- **Target_Language**: 待迁移项目的编程语言（Python/Java/.NET 等）

## Requirements

### Requirement 1: 项目扫描与分析

**User Story:** 作为业务开发者，我希望工具能自动扫描我的项目代码，识别可接入 OwlClaw 的业务函数，这样我可以快速了解迁移范围和工作量。

#### Acceptance Criteria

1. WHEN 用户执行 `owlclaw migrate scan <project_path>` 命令，THE Scanner SHALL 使用 AST 解析目标项目的源代码文件
2. THE Scanner SHALL 识别符合以下条件的函数：公开函数、有明确输入输出、无副作用或副作用可控
3. THE Scanner SHALL 提取函数签名、参数类型、返回类型、文档字符串和注释
4. WHEN 扫描完成，THE CLI_Migrate SHALL 生成 Migration_Report，包含可接入函数列表、函数复杂度评分、建议接入优先级
5. THE Migration_Report SHALL 以 JSON 和 Markdown 两种格式输出
6. WHERE 项目包含多种 Target_Language，THE Scanner SHALL 支持多语言混合扫描

### Requirement 2: Python 项目迁移支持

**User Story:** 作为 Python 业务开发者，我希望工具能为我的 Python 函数生成 @handler 注册代码，这样我可以快速将已有函数接入 OwlClaw。

#### Acceptance Criteria

1. THE CLI_Migrate SHALL 支持 Python 3.8+ 项目的扫描和代码生成
2. WHEN 用户选择一个 Python 函数进行迁移，THE CLI_Migrate SHALL 生成包含 @app.handler 装饰器的注册代码
3. THE CLI_Migrate SHALL 根据函数签名自动推断参数类型和返回类型（使用 type hints）
4. IF 函数缺少 type hints，THEN THE CLI_Migrate SHALL 在生成的代码中添加 `MANUAL_REVIEW` 注释提示用户补充类型
5. THE CLI_Migrate SHALL 生成对应的 SKILL.md 文档骨架，包含函数描述、参数说明、使用场景
6. THE CLI_Migrate SHALL 保留原函数的文档字符串并转换为 SKILL.md 的相应章节

### Requirement 3: REST API 迁移支持

**User Story:** 作为 API 开发者，我希望工具能扫描我的 OpenAPI 规范文件，生成调用这些 API 的 OwlClaw capability，这样我可以让 Agent 使用已有的 REST API。

#### Acceptance Criteria

1. WHEN 用户提供 OpenAPI 3.0+ 规范文件（YAML/JSON），THE CLI_Migrate SHALL 解析 API 端点定义
2. THE CLI_Migrate SHALL 为每个 API 端点生成一个 @handler 函数，封装 HTTP 调用逻辑
3. THE CLI_Migrate SHALL 根据 OpenAPI 的 schema 定义生成参数验证代码
4. THE CLI_Migrate SHALL 在生成的 SKILL.md 中包含 API 的描述、参数、响应格式、错误码说明
5. WHERE API 需要认证，THE CLI_Migrate SHALL 生成配置占位符并在 SKILL.md 中说明认证要求
6. THE CLI_Migrate SHALL 支持批量生成（一次处理整个 OpenAPI 规范）

### Requirement 4: 数据库操作迁移支持

**User Story:** 作为数据库开发者，我希望工具能识别我的 CRUD 操作函数，生成对应的 OwlClaw handler，这样 Agent 可以安全地访问数据库。

#### Acceptance Criteria

1. THE CLI_Migrate SHALL 识别使用 ORM（SQLAlchemy/Django ORM）的数据库操作函数
2. WHEN 识别到 CRUD 操作，THE CLI_Migrate SHALL 生成包含事务管理的 @handler 代码
3. THE CLI_Migrate SHALL 在生成的 SKILL.md 中明确标注数据库操作的副作用和风险
4. THE CLI_Migrate SHALL 为写操作（INSERT/UPDATE/DELETE）生成额外的确认提示逻辑
5. WHERE 函数涉及敏感数据，THE CLI_Migrate SHALL 在 SKILL.md 中添加数据脱敏建议
6. THE CLI_Migrate SHALL 生成数据库连接配置的示例代码

### Requirement 5: 定时任务迁移支持

**User Story:** 作为运维开发者，我希望工具能识别我的 cron job 和定时任务，转换为 OwlClaw 的触发器配置，这样我可以用 OwlClaw 管理定时任务。

#### Acceptance Criteria

1. THE CLI_Migrate SHALL 识别 crontab 文件、APScheduler 配置、Celery beat 任务
2. WHEN 识别到定时任务，THE CLI_Migrate SHALL 生成对应的 OwlClaw trigger 配置（cron 表达式）
3. THE CLI_Migrate SHALL 将定时任务的执行逻辑封装为 @handler 函数
4. THE CLI_Migrate SHALL 在 SKILL.md 中说明任务的执行频率、业务目的、依赖条件
5. WHERE 任务有复杂的依赖关系，THE CLI_Migrate SHALL 在 Migration_Report 中标注需要手动处理的部分
6. THE CLI_Migrate SHALL 生成任务监控和错误处理的建议代码

### Requirement 6: SKILL.md 自动生成

**User Story:** 作为业务开发者，我希望工具能自动生成 SKILL.md 文档骨架，这样我只需填充业务规则而不需要从零编写。

#### Acceptance Criteria

1. THE CLI_Migrate SHALL 为每个迁移的函数生成符合 Agent Skills 规范的 SKILL.md
2. THE SKILL.md SHALL 包含 YAML frontmatter（name、description、metadata）
3. THE SKILL.md SHALL 包含"可用工具"章节，列出函数签名和参数说明
4. THE SKILL.md SHALL 包含"业务规则"章节的占位符，提示用户填写业务逻辑
5. THE SKILL.md SHALL 包含"决策指引"章节的占位符，提示用户填写 Agent 决策建议
6. WHERE 函数有文档字符串，THE CLI_Migrate SHALL 自动填充 SKILL.md 的相应章节
7. THE CLI_Migrate SHALL 根据函数类型（监控/分析/工作流）选择合适的 SKILL.md 模板

### Requirement 7: Dry-Run 预览模式

**User Story:** 作为谨慎的开发者，我希望在实际生成代码前能预览迁移结果，这样我可以评估影响范围并决定是否继续。

#### Acceptance Criteria

1. WHEN 用户执行 `owlclaw migrate generate --dry-run`，THE CLI_Migrate SHALL 生成所有代码和文档但不写入文件系统
2. THE CLI_Migrate SHALL 在终端输出将要创建的文件列表和路径
3. THE CLI_Migrate SHALL 显示每个文件的内容预览（前 20 行）
4. THE CLI_Migrate SHALL 输出统计信息：将创建的文件数、代码行数、预估工作量
5. THE CLI_Migrate SHALL 提供交互式确认，询问用户是否继续实际生成
6. WHERE 检测到潜在冲突（文件已存在），THE CLI_Migrate SHALL 在 dry-run 中高亮显示

### Requirement 8: 迁移报告与建议

**User Story:** 作为项目负责人，我希望工具能生成详细的迁移报告，包含风险评估和优化建议，这样我可以制定迁移计划。

#### Acceptance Criteria

1. THE Migration_Report SHALL 包含项目概览：总函数数、可迁移函数数、不可迁移函数数及原因
2. THE Migration_Report SHALL 为每个函数提供复杂度评分（简单/中等/复杂）
3. THE Migration_Report SHALL 标注高风险函数（涉及敏感数据、外部依赖、复杂逻辑）
4. THE Migration_Report SHALL 提供迁移优先级建议（基于函数调用频率、业务价值）
5. THE Migration_Report SHALL 包含预估的迁移工作量（人天）
6. THE Migration_Report SHALL 提供最佳实践建议（如何优化函数以更好地适配 OwlClaw）
7. THE Migration_Report SHALL 以 Markdown 格式输出，支持导出为 PDF

### Requirement 9: 多语言支持路线图

**User Story:** 作为多语言项目的开发者，我希望了解工具的语言支持计划，这样我可以规划不同语言模块的迁移顺序。

#### Acceptance Criteria

1. THE CLI_Migrate SHALL 在 MVP 阶段完整支持 Python 3.8+ 项目
2. THE CLI_Migrate SHALL 在文档中明确标注 Java 和 .NET 支持为 Phase 2 功能
3. WHERE 用户尝试扫描不支持的语言，THE CLI_Migrate SHALL 返回友好的错误消息并建议替代方案
4. THE CLI_Migrate SHALL 提供语言支持状态查询命令 `owlclaw migrate languages`
5. THE CLI_Migrate SHALL 的架构设计 SHALL 支持插件式语言扩展（为未来语言支持预留接口）

### Requirement 10: 代码生成质量保证

**User Story:** 作为质量工程师，我希望生成的代码符合编码规范且可直接运行，这样我可以减少手动修复工作。

#### Acceptance Criteria

1. THE CLI_Migrate SHALL 生成的 Python 代码 SHALL 符合 PEP 8 规范
2. THE CLI_Migrate SHALL 生成的代码 SHALL 通过 mypy 类型检查（如果原函数有 type hints）
3. THE CLI_Migrate SHALL 生成的代码 SHALL 包含必要的 import 语句和依赖声明
4. THE CLI_Migrate SHALL 生成的代码 SHALL 包含错误处理逻辑（try-except 块）
5. THE CLI_Migrate SHALL 生成的代码 SHALL 包含日志记录语句（使用 Python logging 模块）
6. THE CLI_Migrate SHALL 提供代码格式化选项（black/autopep8）
7. WHERE 生成的代码有 `MANUAL_REVIEW` 注释，THE CLI_Migrate SHALL 在 Migration_Report 中汇总所有待人工复核项

### Requirement 11: 配置与定制化

**User Story:** 作为团队负责人，我希望能配置迁移工具的行为，这样我可以适配团队的编码规范和项目结构。

#### Acceptance Criteria

1. THE CLI_Migrate SHALL 支持配置文件（.owlclaw-migrate.yaml）
2. THE CLI_Migrate SHALL 允许配置输出目录、命名规范、代码风格
3. THE CLI_Migrate SHALL 允许配置扫描规则（包含/排除特定目录或文件）
4. THE CLI_Migrate SHALL 允许配置 SKILL.md 模板路径（使用自定义模板）
5. THE CLI_Migrate SHALL 允许配置函数过滤规则（基于命名模式、复杂度、注解）
6. WHERE 配置文件不存在，THE CLI_Migrate SHALL 使用合理的默认值
7. THE CLI_Migrate SHALL 提供配置验证命令 `owlclaw migrate config validate`

### Requirement 12: 交互式迁移向导

**User Story:** 作为新手开发者，我希望有交互式向导引导我完成迁移，这样我可以逐步学习而不会被复杂选项淹没。

#### Acceptance Criteria

1. WHEN 用户执行 `owlclaw migrate init`，THE CLI_Migrate SHALL 启动交互式向导
2. THE CLI_Migrate SHALL 询问项目路径、语言、输出目录等基本信息
3. THE CLI_Migrate SHALL 在扫描后展示可迁移函数列表，允许用户交互式选择
4. THE CLI_Migrate SHALL 为每个选中的函数询问额外信息（业务描述、优先级）
5. THE CLI_Migrate SHALL 在生成前显示摘要并请求确认
6. THE CLI_Migrate SHALL 支持保存向导配置为配置文件，供后续使用
7. WHERE 用户中断向导，THE CLI_Migrate SHALL 保存进度并允许恢复

## Special Requirements Guidance

### Parser and Serializer Requirements

cli-migrate 涉及多种代码解析和生成场景，需要特别关注解析器的正确性：

#### Requirement 13: Python AST 解析器

**User Story:** 作为工具开发者，我需要可靠的 Python AST 解析器，这样我可以准确提取函数信息。

#### Acceptance Criteria

1. WHEN 提供有效的 Python 源文件，THE Parser SHALL 解析为 AST 并提取函数定义
2. WHEN 提供无效的 Python 源文件，THE Parser SHALL 返回描述性错误消息
3. THE Pretty_Printer SHALL 将生成的 Python 代码格式化为符合 PEP 8 的格式
4. FOR ALL 有效的 Python 函数定义，解析 → 生成代码 → 解析 SHALL 产生等价的 AST（round-trip property）

#### Requirement 14: OpenAPI 规范解析器

**User Story:** 作为工具开发者，我需要可靠的 OpenAPI 解析器，这样我可以准确提取 API 定义。

#### Acceptance Criteria

1. WHEN 提供有效的 OpenAPI 3.0+ 规范文件，THE Parser SHALL 解析为内部数据结构
2. WHEN 提供无效的 OpenAPI 规范文件，THE Parser SHALL 返回描述性错误消息并指出错误位置
3. THE Pretty_Printer SHALL 将生成的 API 调用代码格式化为可读格式
4. FOR ALL 有效的 OpenAPI 规范，解析 → 生成 handler 代码 → 验证 SHALL 确保生成的代码能正确调用 API（round-trip property）

#### Requirement 15: SKILL.md 生成器

**User Story:** 作为工具开发者，我需要可靠的 SKILL.md 生成器，这样我可以确保生成的文档符合 Agent Skills 规范。

#### Acceptance Criteria

1. WHEN 提供函数元数据，THE Generator SHALL 生成符合 Agent Skills 规范的 SKILL.md
2. THE Generator SHALL 验证生成的 SKILL.md 的 YAML frontmatter 格式正确
3. THE Pretty_Printer SHALL 将 SKILL.md 格式化为可读的 Markdown
4. FOR ALL 生成的 SKILL.md，解析 frontmatter → 验证 → 重新生成 SHALL 产生等价的文档（round-trip property）

### Requirement 16: Declarative Binding 输出模式

**User Story:** 作为 IT 运维人员，我希望 cli-migrate 能直接生成包含 Declarative Binding 的 SKILL.md，这样业务系统可以零代码接入 OwlClaw Agent。

#### Acceptance Criteria

1. THE CLI_Migrate SHALL support `--output-mode` flag with values: `handler` (default), `binding`, `both`
2. WHEN `--output-mode binding`, THE CLI_Migrate SHALL generate SKILL.md files with embedded binding declarations instead of @handler Python code
3. FOR OpenAPI endpoints, THE generated SKILL.md SHALL contain HTTP Binding (type=http, method, url template with `${ENV_VAR}`, headers, response_mapping)
4. FOR ORM operations, THE generated SKILL.md SHALL contain SQL Binding (type=sql, parameterized query, read_only=true by default)
5. FOR cron tasks, THE generated SKILL.md SHALL contain HTTP Binding pointing to the task's execution endpoint (if applicable)
6. THE generated SKILL.md SHALL include `prerequisites.env` listing all required environment variables extracted from security schemes and connection strings
7. THE generated SKILL.md body SHALL contain a placeholder section prompting the business user to fill in business rules and decision guidance in natural language
8. WHEN `--output-mode both`, THE CLI_Migrate SHALL generate both @handler code AND binding SKILL.md for each resource
9. ALL generated binding SKILL.md SHALL pass `owlclaw skill validate` without errors
10. THE generated binding SHALL use `${ENV_VAR}` references for all credentials — no plaintext secrets

### Requirement 17: BindingGenerator 组件

**User Story:** 作为工具开发者，我需要一个专门的 BindingGenerator 组件来将扫描结果转换为 binding SKILL.md，这样生成逻辑与现有的 HandlerGenerator 和 SKILLGenerator 保持一致的架构。

#### Acceptance Criteria

1. THE BindingGenerator SHALL be a new class in the Generator Module, alongside HandlerGenerator and SKILLGenerator
2. THE BindingGenerator SHALL implement `generate_from_openapi(endpoint: APIEndpoint) -> BindingGenerationResult`
3. THE BindingGenerator SHALL implement `generate_from_orm(operation: ORMOperation) -> BindingGenerationResult`
4. THE BindingGenerationResult SHALL include: skill_path, skill_content, binding_type, tools_count, prerequisites, warnings
5. THE BindingGenerator SHALL reuse the existing Jinja2 template engine for SKILL.md generation
6. FOR ALL generated SQL bindings, THE BindingGenerator SHALL enforce parameterized queries (`:param` placeholders)

---

**维护者**: OwlClaw 核心团队  
**最后更新**: 2026-02-24  
**优先级**: P1  
**预估工作量**: 5-7 天（含 binding 输出模式）
