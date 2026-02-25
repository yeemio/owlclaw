# Requirements Document: examples

## 文档联动

- requirements: `.kiro/specs/examples/requirements.md`
- design: `.kiro/specs/examples/design.md`
- tasks: `.kiro/specs/examples/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


## Introduction

examples（示例应用）是 OwlClaw 的端到端示例集合，用于展示 OwlClaw 的核心能力和最佳实践。作为用户学习和参考的重要资源，examples 提供完整的、可运行的业务场景示例，覆盖监控、分析、工作流、集成等常见应用场景。

> 说明（2026-02-25）：当前收口口径采用 `examples/tasks.md` 的 12 项可验证交付（目录资产 + 文档 + 单元测试）。超出该口径的扩展需求保留为后续迭代。

根据 OwlClaw 的核心定位"让已有业务系统获得 AI 自主能力"，examples 通过实际业务场景展示如何使用 @handler 装饰器、Skills 系统、触发器机制和治理能力，帮助用户快速理解 OwlClaw 的价值和使用方法。

examples 设计为独立可运行的示例应用集合，每个示例都包含完整的代码、配置、文档和 Docker Compose 环境，使用 mock 数据避免依赖真实外部服务。MVP 阶段提供 5 个核心场景示例，覆盖电商、金融、SaaS 等行业。

## Glossary

- **Examples**: 示例应用集合，展示 OwlClaw 核心能力的端到端示例
- **Example_App**: 单个示例应用，包含完整的代码、配置和文档
- **Scenario**: 业务场景，如库存监控、客户流失分析等
- **Handler**: 使用 @handler 装饰器标注的业务函数
- **Skill**: OwlClaw 的能力单元，通过 SKILL.md 文档描述
- **Trigger**: 触发器，包括定时触发、事件触发、Webhook 触发
- **Mock_Data**: 模拟数据，用于示例运行而不依赖真实外部服务
- **Docker_Compose**: 容器编排工具，用于一键启动示例环境
- **README**: 示例文档，包含功能说明、运行步骤、配置说明
- **Code_Comment**: 代码注释，详细解释代码逻辑和最佳实践
- **Best_Practice**: 最佳实践，展示推荐的使用模式和设计方法
- **Governance**: 治理能力，包括审计、监控、限流等

## Requirements

### Requirement 1: 库存监控示例

**User Story:** 作为电商平台开发者，我希望看到库存监控的完整示例，这样我可以学习如何使用 OwlClaw 实现定时监控和预警通知。

#### Acceptance Criteria

1. THE Example_App SHALL 提供库存监控场景的完整代码实现
2. THE Example_App SHALL 使用 @handler 装饰器标注库存检查函数
3. THE Example_App SHALL 使用定时 Trigger 每 5 分钟执行一次库存检查
4. WHEN 库存低于阈值，THE Handler SHALL 生成预警通知
5. THE Example_App SHALL 包含 SKILL.md 文档描述库存查询和通知发送能力
6. THE Example_App SHALL 使用 Mock_Data 模拟商品库存数据
7. THE Example_App SHALL 提供 Docker_Compose 配置实现一键启动
8. THE README SHALL 包含场景说明、运行步骤、配置说明和预期输出
9. THE Code_Comment SHALL 详细解释 @handler 使用方法和触发器配置
10. THE Example_App SHALL 在 3 分钟内完成启动并执行第一次检查

### Requirement 2: 客户流失分析示例

**User Story:** 作为 SaaS 平台开发者，我希望看到客户流失分析的完整示例，这样我可以学习如何使用 OwlClaw 实现数据分析和决策逻辑。

#### Acceptance Criteria

1. THE Example_App SHALL 提供客户流失分析场景的完整代码实现
2. THE Example_App SHALL 使用 @handler 装饰器标注流失分析函数
3. THE Handler SHALL 分析客户行为数据并计算流失风险评分
4. WHEN 流失风险评分高于阈值，THE Handler SHALL 创建挽留任务
5. THE Example_App SHALL 展示多步骤分析流程（数据提取 → 特征计算 → 风险评估 → 任务创建）
6. THE Example_App SHALL 使用 Mock_Data 模拟客户行为数据
7. THE SKILL.md SHALL 描述数据查询、风险评估、任务创建能力
8. THE Code_Comment SHALL 解释决策逻辑和评分算法
9. THE README SHALL 包含流失风险评估规则和任务创建逻辑说明
10. THE Example_App SHALL 提供可视化输出展示分析结果

### Requirement 3: 财务异常检测示例

**User Story:** 作为金融系统开发者，我希望看到财务异常检测的完整示例，这样我可以学习如何使用 OwlClaw 实现规则引擎和审计记录。

#### Acceptance Criteria

1. THE Example_App SHALL 提供财务异常检测场景的完整代码实现
2. THE Example_App SHALL 使用 @handler 装饰器标注异常检测函数
3. THE Handler SHALL 应用多条检测规则（金额异常、频率异常、时间异常）
4. WHEN 检测到异常，THE Handler SHALL 记录审计日志并触发告警
5. THE Example_App SHALL 展示 Governance 能力的使用（审计、监控）
6. THE Example_App SHALL 使用 Mock_Data 模拟交易数据
7. THE SKILL.md SHALL 描述数据查询、规则引擎、审计记录能力
8. THE Code_Comment SHALL 解释规则配置和异常判定逻辑
9. THE README SHALL 包含检测规则说明和告警机制说明
10. THE Example_App SHALL 提供规则配置文件支持动态调整检测规则

### Requirement 4: API 集成示例

**User Story:** 作为系统集成工程师，我希望看到 API 集成的完整示例，这样我可以学习如何使用 OwlClaw 实现外部 API 调用和错误处理。

#### Acceptance Criteria

1. THE Example_App SHALL 提供 API 集成场景的完整代码实现
2. THE Example_App SHALL 使用 @handler 装饰器标注 API 调用函数
3. THE Handler SHALL 调用外部 REST API 并处理响应
4. WHEN API 调用失败，THE Handler SHALL 执行重试逻辑（最多 3 次，指数退避）
5. THE Example_App SHALL 展示错误处理 Best_Practice（超时、重试、降级）
6. THE Example_App SHALL 使用 Mock API Server 模拟外部服务
7. THE SKILL.md SHALL 描述 HTTP 请求、响应解析、错误处理能力
8. THE Code_Comment SHALL 解释重试策略和错误分类逻辑
9. THE README SHALL 包含 API 配置说明和错误处理策略说明
10. THE Mock API Server SHALL 模拟成功、失败、超时等多种响应场景

### Requirement 5: 工作流自动化示例

**User Story:** 作为业务流程开发者，我希望看到工作流自动化的完整示例，这样我可以学习如何使用 OwlClaw 实现多步骤流程和条件分支。

#### Acceptance Criteria

1. THE Example_App SHALL 提供工作流自动化场景的完整代码实现
2. THE Example_App SHALL 使用多个 @handler 装饰器标注工作流步骤
3. THE Handler SHALL 实现多步骤流程（订单创建 → 库存检查 → 支付处理 → 发货通知）
4. THE Handler SHALL 实现条件分支逻辑（库存不足 → 补货流程，支付失败 → 重试流程）
5. WHEN 需要人工介入，THE Handler SHALL 暂停流程并发送通知
6. THE Example_App SHALL 展示流程编排 Best_Practice
7. THE SKILL.md SHALL 描述流程控制、状态管理、通知发送能力
8. THE Code_Comment SHALL 解释流程编排和状态转换逻辑
9. THE README SHALL 包含流程图和状态转换说明
10. THE Example_App SHALL 提供流程可视化界面展示执行状态

### Requirement 6: 示例结构规范

**User Story:** 作为示例维护者，我希望所有示例遵循统一的结构规范，这样我可以保证示例的一致性和可维护性。

#### Acceptance Criteria

1. THE Examples SHALL 使用统一的目录结构（app.py、skills/、config/、docker-compose.yml、README.md）
2. THE Example_App SHALL 在根目录提供 README.md 包含完整的使用说明
3. THE Example_App SHALL 在 skills/ 目录提供 SKILL.md 文档
4. THE Example_App SHALL 在 config/ 目录提供配置文件和配置说明
5. THE Example_App SHALL 提供 requirements.txt 或 pyproject.toml 声明依赖
6. THE Example_App SHALL 提供 .env.example 文件展示环境变量配置
7. THE Example_App SHALL 在 docker-compose.yml 中定义所有依赖服务
8. THE Code_Comment SHALL 使用中文注释并遵循统一的注释风格
9. THE README SHALL 包含"功能说明"、"快速开始"、"配置说明"、"预期输出"四个部分
10. THE Example_App SHALL 提供 Makefile 或脚本简化常用操作

### Requirement 7: Mock 数据管理

**User Story:** 作为示例用户，我希望示例使用 mock 数据而不依赖真实外部服务，这样我可以快速运行示例而无需复杂配置。

#### Acceptance Criteria

1. THE Example_App SHALL 使用 Mock_Data 模拟所有外部数据源
2. THE Mock_Data SHALL 存储在 data/ 目录下的 JSON 或 CSV 文件中
3. THE Example_App SHALL 提供数据生成脚本生成 Mock_Data
4. THE Mock_Data SHALL 包含足够的数据量展示示例功能（至少 100 条记录）
5. THE Mock_Data SHALL 包含正常数据和异常数据覆盖不同场景
6. WHERE 示例需要数据库，THE Example_App SHALL 使用 SQLite 或内存数据库
7. WHERE 示例需要外部 API，THE Example_App SHALL 提供 Mock API Server
8. THE README SHALL 说明 Mock_Data 的结构和生成方法
9. THE Example_App SHALL 在启动时自动加载 Mock_Data
10. THE Mock_Data SHALL 设计为可扩展，支持用户添加自定义数据

### Requirement 8: Docker Compose 环境

**User Story:** 作为示例用户，我希望使用 Docker Compose 一键启动示例环境，这样我可以避免复杂的环境配置。

#### Acceptance Criteria

1. THE Example_App SHALL 提供 docker-compose.yml 文件
2. WHEN 用户执行 `docker-compose up`，THE Example_App SHALL 自动启动所有依赖服务
3. THE Docker_Compose SHALL 包含应用容器和所有依赖服务容器
4. THE Docker_Compose SHALL 配置健康检查确保服务就绪
5. THE Docker_Compose SHALL 配置卷挂载持久化数据和日志
6. THE Docker_Compose SHALL 配置网络隔离保证服务间通信
7. THE Docker_Compose SHALL 使用环境变量配置支持自定义配置
8. THE README SHALL 包含 Docker Compose 使用说明和故障排查指南
9. THE Example_App SHALL 在容器启动后 2 分钟内完成初始化
10. THE Docker_Compose SHALL 提供日志输出帮助用户理解运行状态

### Requirement 9: 文档质量

**User Story:** 作为示例用户，我希望示例文档清晰完整，这样我可以快速理解示例功能和使用方法。

#### Acceptance Criteria

1. THE README SHALL 使用清晰的标题结构和格式
2. THE README SHALL 在开头提供场景说明和学习目标
3. THE README SHALL 提供"快速开始"部分包含最少步骤运行示例
4. THE README SHALL 提供"配置说明"部分解释所有配置项
5. THE README SHALL 提供"预期输出"部分展示运行结果
6. THE README SHALL 提供"故障排查"部分列出常见问题和解决方法
7. THE README SHALL 提供"扩展阅读"部分链接到相关文档
8. THE SKILL.md SHALL 清晰描述示例使用的所有 Skill
9. THE Code_Comment SHALL 解释关键代码逻辑和设计决策
10. THE README SHALL 包含示例的架构图或流程图

### Requirement 10: 代码质量

**User Story:** 作为示例维护者，我希望示例代码遵循最佳实践，这样我可以保证示例的教学价值和可维护性。

#### Acceptance Criteria

1. THE Example_App SHALL 遵循 PEP 8 代码风格规范
2. THE Example_App SHALL 使用类型注解提高代码可读性
3. THE Example_App SHALL 使用有意义的变量名和函数名
4. THE Example_App SHALL 将复杂逻辑拆分为小函数提高可读性
5. THE Example_App SHALL 使用配置文件而非硬编码配置
6. THE Example_App SHALL 提供适当的错误处理和日志记录
7. THE Example_App SHALL 避免过度设计保持代码简洁
8. THE Code_Comment SHALL 解释"为什么"而非"是什么"
9. THE Example_App SHALL 通过 pylint 或 ruff 代码检查（评分 > 8.0）
10. THE Example_App SHALL 提供单元测试覆盖核心逻辑

### Requirement 11: 示例索引

**User Story:** 作为示例用户，我希望有一个示例索引页面，这样我可以快速找到适合我的示例。

#### Acceptance Criteria

1. THE Examples SHALL 在根目录提供 README.md 作为示例索引
2. THE 索引 README SHALL 列出所有示例及其简要说明
3. THE 索引 README SHALL 按场景分类组织示例（监控、分析、工作流、集成）
4. THE 索引 README SHALL 标注每个示例的难度级别（入门、中级、高级）
5. THE 索引 README SHALL 标注每个示例展示的核心能力
6. THE 索引 README SHALL 提供学习路径建议
7. THE 索引 README SHALL 包含环境要求说明（Docker、Python 版本）
8. THE 索引 README SHALL 提供快速开始指南
9. THE 索引 README SHALL 链接到 OwlClaw 官方文档
10. THE 索引 README SHALL 包含贡献指南和反馈渠道

### Requirement 12: 可运行性验证

**User Story:** 作为 CI/CD 工程师，我希望示例可以自动化验证，这样我可以确保示例始终可运行。

#### Acceptance Criteria

1. THE Examples SHALL 提供自动化测试脚本验证示例可运行性
2. THE 测试脚本 SHALL 验证 Docker Compose 启动成功
3. THE 测试脚本 SHALL 验证应用容器健康检查通过
4. THE 测试脚本 SHALL 验证示例执行核心功能并产生预期输出
5. THE 测试脚本 SHALL 在 CI 环境中可执行
6. THE 测试脚本 SHALL 在 5 分钟内完成验证
7. WHEN 示例验证失败，THE 测试脚本 SHALL 输出详细的错误信息
8. THE Examples SHALL 提供 GitHub Actions 工作流配置
9. THE 测试脚本 SHALL 验证文档链接有效性
10. THE 测试脚本 SHALL 验证代码风格符合规范

## Special Requirements Guidance

### Parser and Serializer Requirements

examples 需要处理配置文件解析和数据序列化，需要特别关注解析器和序列化器的正确性。

#### Requirement 13: 配置文件解析器

**User Story:** 作为示例开发者，我需要可靠的配置文件解析器，这样我可以正确加载示例配置。

#### Acceptance Criteria

1. WHEN 提供有效的配置文件（YAML 或 JSON），THE Parser SHALL 解析为配置对象
2. WHEN 提供无效的配置文件，THE Parser SHALL 返回描述性错误消息并指出错误位置
3. THE Parser SHALL 验证配置项的类型和取值范围
4. THE Parser SHALL 提供默认值处理缺失的配置项
5. FOR ALL 有效的配置对象，解析 → 序列化 → 解析 SHALL 产生等价的配置对象（round-trip property）

#### Requirement 14: Mock 数据序列化器

**User Story:** 作为示例开发者，我需要可靠的数据序列化器，这样我可以正确加载和保存 Mock 数据。

#### Acceptance Criteria

1. WHEN 提供 Mock_Data 对象，THE Serializer SHALL 序列化为 JSON 或 CSV 格式
2. THE Serializer SHALL 确保序列化后的数据可被标准解析器解析
3. THE Serializer SHALL 处理特殊字符和 Unicode 字符
4. FOR ALL Mock_Data 对象，序列化 → 反序列化 SHALL 产生等价的对象（round-trip property）
5. THE Serializer SHALL 生成人类可读的格式便于手动编辑

---

**维护者**: OwlClaw 核心团队  
**最后更新**: 2025-02-22  
**优先级**: P1  
**预估工作量**: 3-5 天
