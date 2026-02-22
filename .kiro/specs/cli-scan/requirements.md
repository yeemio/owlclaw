# Requirements Document: cli-scan

## Introduction

cli-scan 是 OwlClaw 的 AST 代码扫描器，用于分析项目源代码的结构、能力点和元数据。作为 cli-migrate 的基础组件，cli-scan 负责解析源代码文件，构建抽象语法树（AST），提取函数签名、类型信息、文档字符串、依赖关系和复杂度指标，并输出结构化的扫描结果。

根据 OwlClaw 的核心定位"让已有业务系统获得 AI 自主能力"，cli-scan 是实现代码分析和自动化接入的关键基础设施。它降低了代码理解的门槛，使 cli-migrate 能够智能地识别可接入的业务函数，从而实现零改造或最小改造接入。

cli-scan 设计为独立可用的代码分析工具，同时也是 cli-migrate 的依赖组件。MVP 阶段优先支持 Python 3.8+，后续扩展至 Java 和 .NET。

## Glossary

- **CLI_Scan**: 命令行 AST 扫描器，用于分析项目代码结构
- **AST**: 抽象语法树（Abstract Syntax Tree），代码的结构化表示
- **Scanner**: 代码扫描引擎，负责遍历文件和解析代码
- **Parser**: 语言解析器，将源代码转换为 AST
- **Function_Signature**: 函数签名，包含函数名、参数、返回类型
- **Type_Hint**: Python 类型注解，用于静态类型检查
- **Docstring**: 文档字符串，描述函数、类或模块的用途
- **Complexity_Score**: 复杂度评分，包括圈复杂度和认知复杂度
- **Dependency_Graph**: 依赖关系图，表示函数间的调用关系
- **Scan_Result**: 扫描结果，包含代码结构和元数据的结构化数据
- **Incremental_Scan**: 增量扫描，只扫描变更的文件
- **Target_Language**: 待扫描项目的编程语言（Python/Java/.NET 等）

## Requirements

### Requirement 1: Python 项目扫描

**User Story:** 作为开发者，我希望扫描器能解析 Python 项目的源代码，提取函数和类的定义，这样我可以了解项目的代码结构。

#### Acceptance Criteria

1. WHEN 用户执行 `owlclaw scan <project_path>` 命令，THE Scanner SHALL 遍历项目目录下的所有 .py 文件
2. THE Parser SHALL 使用 Python ast 模块解析每个 .py 文件为 AST
3. THE Scanner SHALL 提取模块级函数、类定义、类方法的 Function_Signature
4. THE Scanner SHALL 支持 Python 3.8 至 Python 3.13 的语法特性
5. IF 文件包含语法错误，THEN THE Scanner SHALL 记录错误信息并继续扫描其他文件
6. THE Scanner SHALL 排除虚拟环境目录（venv、.venv、env）和第三方库目录（site-packages）

### Requirement 2: 函数签名提取

**User Story:** 作为代码分析工具的用户，我希望扫描器能提取完整的函数签名信息，这样我可以了解函数的接口定义。

#### Acceptance Criteria

1. THE Scanner SHALL 提取函数名、参数名、参数默认值
2. WHERE 函数包含 Type_Hint，THE Scanner SHALL 提取参数类型和返回类型
3. THE Scanner SHALL 识别位置参数、关键字参数、可变参数（*args、**kwargs）
4. THE Scanner SHALL 提取装饰器信息（decorator 名称和参数）
5. THE Scanner SHALL 识别异步函数（async def）和生成器函数（yield）
6. THE Scan_Result SHALL 以 JSON 格式表示函数签名，包含所有提取的元数据

### Requirement 3: 文档字符串提取

**User Story:** 作为文档生成工具的用户，我希望扫描器能提取文档字符串，这样我可以自动生成 API 文档。

#### Acceptance Criteria

1. THE Scanner SHALL 提取函数、类、模块的 Docstring
2. THE Scanner SHALL 识别 Google 风格、NumPy 风格、reStructuredText 风格的 Docstring
3. THE Scanner SHALL 解析 Docstring 中的参数说明、返回值说明、异常说明
4. WHERE Docstring 包含示例代码，THE Scanner SHALL 提取示例代码块
5. THE Scanner SHALL 保留 Docstring 的原始格式和缩进
6. THE Scan_Result SHALL 将 Docstring 作为独立字段存储

### Requirement 4: 类型推断

**User Story:** 作为类型检查工具的用户，我希望扫描器能推断缺少类型注解的变量类型，这样我可以进行静态类型分析。

#### Acceptance Criteria

1. WHERE 函数参数缺少 Type_Hint，THE Scanner SHALL 尝试从默认值推断类型
2. THE Scanner SHALL 从函数体中的赋值语句推断局部变量类型
3. THE Scanner SHALL 从 return 语句推断返回类型
4. THE Scanner SHALL 识别常见的类型模式（List、Dict、Optional、Union）
5. IF 类型无法推断，THEN THE Scanner SHALL 在 Scan_Result 中标记为 "unknown"
6. THE Scanner SHALL 提供置信度评分（high/medium/low）表示推断的可靠性

### Requirement 5: 依赖关系分析

**User Story:** 作为架构分析工具的用户，我希望扫描器能识别函数间的调用关系，这样我可以生成依赖关系图。

#### Acceptance Criteria

1. THE Scanner SHALL 识别函数内部的函数调用语句
2. THE Scanner SHALL 构建 Dependency_Graph，表示函数间的调用关系
3. THE Scanner SHALL 识别外部模块的导入语句（import、from...import）
4. THE Scanner SHALL 区分标准库、第三方库、项目内部模块的依赖
5. THE Scanner SHALL 识别循环依赖并在 Scan_Result 中标注
6. THE Dependency_Graph SHALL 以邻接表或邻接矩阵格式存储

### Requirement 6: 复杂度计算

**User Story:** 作为代码质量工程师，我希望扫描器能计算函数的复杂度指标，这样我可以识别需要重构的代码。

#### Acceptance Criteria

1. THE Scanner SHALL 计算每个函数的圈复杂度（Cyclomatic Complexity）
2. THE Scanner SHALL 计算每个函数的认知复杂度（Cognitive Complexity）
3. THE Scanner SHALL 统计函数的代码行数（LOC）和有效代码行数（SLOC）
4. THE Scanner SHALL 统计函数的参数数量和嵌套深度
5. THE Complexity_Score SHALL 包含复杂度等级（simple/medium/complex）
6. THE Scan_Result SHALL 为每个函数包含完整的 Complexity_Score

### Requirement 7: 增量扫描

**User Story:** 作为 CI/CD 流程的用户，我希望扫描器支持增量扫描，这样我可以快速分析代码变更。

#### Acceptance Criteria

1. WHEN 用户执行 `owlclaw scan --incremental` 命令，THE Scanner SHALL 只扫描自上次扫描后变更的文件
2. THE Scanner SHALL 使用 git diff 识别变更的文件列表
3. THE Scanner SHALL 缓存上次扫描的 Scan_Result
4. THE Scanner SHALL 合并增量扫描结果与缓存结果
5. WHERE 文件被删除，THE Scanner SHALL 从 Scan_Result 中移除对应的条目
6. THE Scanner SHALL 在 Scan_Result 中标注每个条目的扫描时间戳

### Requirement 8: 并行扫描

**User Story:** 作为大型项目的开发者，我希望扫描器支持并行处理，这样我可以在合理时间内完成扫描。

#### Acceptance Criteria

1. THE Scanner SHALL 使用多进程并行扫描多个文件
2. THE Scanner SHALL 根据 CPU 核心数自动确定并行度
3. WHEN 用户指定 `--workers N` 参数，THE Scanner SHALL 使用 N 个工作进程
4. THE Scanner SHALL 在并行扫描时保证结果的确定性（相同输入产生相同输出）
5. THE Scanner SHALL 在扫描 1000 个文件时完成时间少于 10 秒
6. THE Scanner SHALL 在并行扫描时正确处理异常和错误

### Requirement 9: 扫描结果输出

**User Story:** 作为工具集成者，我希望扫描器能输出结构化的扫描结果，这样我可以在其他工具中使用这些数据。

#### Acceptance Criteria

1. THE Scanner SHALL 支持 JSON 格式输出扫描结果
2. THE Scanner SHALL 支持 YAML 格式输出扫描结果
3. WHEN 用户指定 `--output <file>` 参数，THE Scanner SHALL 将结果写入指定文件
4. WHERE 未指定输出文件，THE Scanner SHALL 将结果输出到标准输出
5. THE Scan_Result SHALL 包含扫描元数据（扫描时间、项目路径、扫描文件数）
6. THE Scan_Result SHALL 使用一致的 schema，便于工具解析

### Requirement 10: 配置与过滤

**User Story:** 作为项目负责人，我希望能配置扫描器的行为，这样我可以适配项目的特定需求。

#### Acceptance Criteria

1. THE Scanner SHALL 支持配置文件（.owlclaw-scan.yaml）
2. THE Scanner SHALL 允许配置包含和排除的目录模式（glob pattern）
3. THE Scanner SHALL 允许配置包含和排除的文件模式（glob pattern）
4. THE Scanner SHALL 允许配置最小复杂度阈值（只输出复杂度高于阈值的函数）
5. THE Scanner SHALL 允许配置是否提取 Docstring、是否计算复杂度、是否分析依赖
6. WHERE 配置文件不存在，THE Scanner SHALL 使用合理的默认值
7. THE Scanner SHALL 提供配置验证命令 `owlclaw scan config validate`

### Requirement 11: 错误处理与日志

**User Story:** 作为运维工程师，我希望扫描器能提供清晰的错误信息和日志，这样我可以快速定位问题。

#### Acceptance Criteria

1. WHEN 扫描过程中发生错误，THE Scanner SHALL 记录详细的错误信息（文件路径、行号、错误类型）
2. THE Scanner SHALL 使用 Python logging 模块记录日志
3. THE Scanner SHALL 支持日志级别配置（DEBUG/INFO/WARNING/ERROR）
4. WHEN 用户指定 `--verbose` 参数，THE Scanner SHALL 输出详细的扫描进度信息
5. THE Scanner SHALL 在扫描完成后输出统计信息（成功文件数、失败文件数、总耗时）
6. WHERE 文件无法读取，THE Scanner SHALL 记录警告并继续扫描其他文件

### Requirement 12: 命令行接口

**User Story:** 作为命令行工具的用户，我希望扫描器提供友好的命令行接口，这样我可以方便地使用各种功能。

#### Acceptance Criteria

1. THE CLI_Scan SHALL 提供 `owlclaw scan <path>` 命令扫描指定路径
2. THE CLI_Scan SHALL 提供 `--format` 参数选择输出格式（json/yaml）
3. THE CLI_Scan SHALL 提供 `--output` 参数指定输出文件
4. THE CLI_Scan SHALL 提供 `--incremental` 参数启用增量扫描
5. THE CLI_Scan SHALL 提供 `--workers` 参数指定并行度
6. THE CLI_Scan SHALL 提供 `--config` 参数指定配置文件路径
7. THE CLI_Scan SHALL 提供 `--help` 参数显示帮助信息
8. THE CLI_Scan SHALL 提供 `--version` 参数显示版本信息

## Special Requirements Guidance

### Parser and Serializer Requirements

cli-scan 的核心功能是解析源代码和序列化扫描结果，需要特别关注解析器和序列化器的正确性。

#### Requirement 13: Python AST 解析器

**User Story:** 作为工具开发者，我需要可靠的 Python AST 解析器，这样我可以准确提取代码结构。

#### Acceptance Criteria

1. WHEN 提供有效的 Python 源文件，THE Parser SHALL 解析为 AST 并提取所有函数和类定义
2. WHEN 提供无效的 Python 源文件，THE Parser SHALL 返回描述性错误消息并指出错误位置
3. THE Parser SHALL 支持 Python 3.8 至 Python 3.13 的所有语法特性
4. FOR ALL 有效的 Python 源文件，解析 → 提取签名 → 验证 SHALL 确保提取的签名与源代码一致（round-trip property）

#### Requirement 14: 扫描结果序列化器

**User Story:** 作为工具开发者，我需要可靠的扫描结果序列化器，这样我可以确保数据的完整性和一致性。

#### Acceptance Criteria

1. WHEN 提供 Scan_Result 对象，THE Serializer SHALL 序列化为 JSON 或 YAML 格式
2. THE Serializer SHALL 确保序列化后的数据可被标准 JSON/YAML 解析器解析
3. THE Serializer SHALL 处理特殊字符和 Unicode 字符
4. FOR ALL Scan_Result 对象，序列化 → 反序列化 SHALL 产生等价的对象（round-trip property）
5. THE Serializer SHALL 生成符合预定义 JSON Schema 的输出

#### Requirement 15: 配置文件解析器

**User Story:** 作为工具开发者，我需要可靠的配置文件解析器，这样我可以正确加载用户配置。

#### Acceptance Criteria

1. WHEN 提供有效的配置文件（.owlclaw-scan.yaml），THE Parser SHALL 解析为配置对象
2. WHEN 提供无效的配置文件，THE Parser SHALL 返回描述性错误消息并指出错误位置
3. THE Parser SHALL 验证配置项的类型和取值范围
4. FOR ALL 有效的配置对象，解析 → 序列化 → 解析 SHALL 产生等价的配置对象（round-trip property）

---

**维护者**: OwlClaw 核心团队  
**最后更新**: 2025-02-22  
**优先级**: P1  
**预估工作量**: 3-4 天
