# 任务清单: declarative-binding

## 文档联动

- requirements: `.kiro/specs/declarative-binding/requirements.md`
- design: `.kiro/specs/declarative-binding/design.md`
- tasks: `.kiro/specs/declarative-binding/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`

## 任务

### Phase 0：契约与文档

- [x] **Task 0**: 契约与文档对齐
  - [x] 0.1 确认 requirements.md 完整且与架构文档 §4.12 一致
  - [x] 0.2 确认 design.md 完整且包含所有组件设计
  - [x] 0.3 确认 tasks.md 覆盖所有需求的实现
  - [x] 0.4 定义 Binding Schema 的 JSON Schema（语言无关契约，供跨语言验证）
  - [x] 0.5 定义 `tools` 简化声明语法（YAML 内联，降低 JSON Schema 书写门槛）
  - [x] 0.6 定义 `prerequisites` 字段规范（env/bins/config/python_packages/os）

### Phase 1：核心基础设施（MVP — P0）

- [x] **Task 1**: Binding Schema 与数据模型
  - [x] 1.1 创建 `owlclaw/capabilities/bindings/` 包结构
  - [x] 1.2 实现 `schema.py`：BindingConfig、RetryConfig 基类
  - [x] 1.3 实现 HTTPBindingConfig（method、url、headers、body_template、response_mapping）
  - [x] 1.4 实现 QueueBindingConfig（provider、connection、topic、format、headers_mapping）
  - [x] 1.5 实现 SQLBindingConfig（connection、query、read_only、parameter_mapping、max_rows）
  - [x] 1.6 实现 `parse_binding_config()` 工厂函数（dict → typed config）
  - [x] 1.7 实现 schema 验证函数（必填字段、类型检查、credential 引用格式）
  - [x] 1.8 单元测试：schema 解析、验证、round-trip 序列化

- [x] **Task 2**: CredentialResolver
  - [x] 2.1 实现 `credential.py`：CredentialResolver 类
  - [x] 2.2 实现 `resolve()` 方法（`${ENV_VAR}` → 实际值）
  - [x] 2.3 实现 `resolve_dict()` 方法（递归解析嵌套 dict）
  - [x] 2.4 实现 `contains_potential_secret()` 静态方法（启发式检测明文密钥）
  - [x] 2.5 支持多来源：os.environ → .env 文件 → owlclaw.yaml secrets
  - [x] 2.6 缺失变量时抛出 ValueError（明确错误信息）
  - [x] 2.7 单元测试：正常解析、缺失变量、嵌套 dict、secret 检测

- [x] **Task 3**: Binding Executor 抽象与注册表
  - [x] 3.1 实现 `executor.py`：BindingExecutor ABC（execute、validate_config、supported_modes）
  - [x] 3.2 实现 BindingExecutorRegistry（register、get、list_types）
  - [x] 3.3 未知类型时抛出 ValueError（含可用类型列表）
  - [x] 3.4 单元测试：注册、获取、未知类型错误

- [x] **Task 4**: HTTPBinding Executor（MVP 核心）
  - [x] 4.1 实现 `http_executor.py`：HTTPBindingExecutor 类
  - [x] 4.2 实现 URL 路径参数模板解析（`{param}` → 实际值）
  - [x] 4.3 实现 headers 的 credential 解析
  - [x] 4.4 实现 body_template 参数替换
  - [x] 4.5 实现 response_mapping（JSONPath 提取、status_codes 映射）
  - [x] 4.6 实现 active 模式：正常 HTTP 调用 + 超时 + 重试（指数退避）
  - [x] 4.7 实现 shadow 模式：GET 正常执行，写操作只记录不发送
  - [x] 4.8 单元测试：active GET/POST、shadow 拦截、超时重试、response mapping
  - [x] 4.9 集成测试：使用 httpx mock 的完整调用链路

- [ ] **Task 5**: BindingTool 与 Ledger 集成
  - [ ] 5.1 实现 `tool.py`：BindingTool 类
  - [ ] 5.2 实现 `__call__()` 方法（executor 分发 + 计时）
  - [ ] 5.3 实现 Ledger 记录（tool_name、binding_type、mode、parameters、result_summary、elapsed_ms、status）
  - [ ] 5.4 实现 `_summarize()` 结果摘要（截断长响应）
  - [ ] 5.5 错误处理：executor 异常时记录 Ledger 并重新抛出
  - [ ] 5.6 单元测试：正常调用、错误记录、Ledger 集成

- [ ] **Task 6**: Skills Loader 扩展 — binding 检测与自动注册
  - [ ] 6.1 扩展 `SkillsLoader._parse_skill_file()` 检测 tools_schema 中的 binding 字段
  - [ ] 6.2 实现 `auto_register_binding_tools()` 函数
  - [ ] 6.3 @handler 优先级：已有 @handler 的工具不被 binding 覆盖
  - [ ] 6.4 扩展 `OwlClaw.mount_skills()` 调用 auto_register_binding_tools
  - [ ] 6.5 集成测试：Skills 加载 → binding 检测 → BindingTool 注册 → 调用

- [ ] **Task 7**: `owlclaw skill validate` 扩展 — binding 验证 + 安全审计
  - [ ] 7.1 扩展 validate 命令检测 binding schema 格式
  - [ ] 7.2 验证必填字段（url for HTTP、topic for Queue、query for SQL）
  - [ ] 7.3 验证 credential 引用格式（`${ENV_VAR}` 而非明文）
  - [ ] 7.4 启发式检测明文密钥并发出警告
  - [ ] 7.5 验证 prerequisites 字段（env 变量是否存在、bins 是否在 PATH 中）
  - [ ] 7.6 binding 声明 vs 实际一致性检查（声明的 ${ENV_VAR} 是否在 prerequisites.env 中）
  - [ ] 7.7 单元测试：有效/无效 binding 验证、prerequisites 检查、一致性审计

### Phase 2：扩展执行器（P1）

- [ ] **Task 8**: QueueBinding Executor
  - [ ] 8.1 实现 `queue_executor.py`：QueueBindingExecutor 类
  - [ ] 8.2 复用 `owlclaw/integrations/queue_adapters/` 的 Kafka 适配器
  - [ ] 8.3 实现 headers_mapping 参数替换
  - [ ] 8.4 实现 shadow 模式（只记录不发送）
  - [ ] 8.5 单元测试：active publish、shadow 拦截、headers mapping

- [ ] **Task 9**: SQLBinding Executor
  - [ ] 9.1 实现 `sql_executor.py`：SQLBindingExecutor 类
  - [ ] 9.2 实现参数化查询（强制 `:param` 占位符）
  - [ ] 9.3 实现 read_only 强制（默认 true）
  - [ ] 9.4 实现 max_rows 限制
  - [ ] 9.5 validate_config 拒绝字符串拼接模式（%、f-string）
  - [ ] 9.6 实现 shadow 模式（写操作只记录）
  - [ ] 9.7 单元测试：参数化查询、read_only、string interpolation 拒绝、max_rows

- [ ] **Task 10**: Shadow 模式 → 对比报告
  - [ ] 10.1 shadow 执行结果写入 Ledger 并标记 `mode=shadow`
  - [ ] 10.2 实现 shadow 结果查询 API（按 tool_name、时间范围）
  - [ ] 10.3 与 `e2e-validation` report_generator 集成（shadow 数据作为对比输入）
  - [ ] 10.4 集成测试：shadow 调用 → Ledger → 查询 → 报告

### Phase 3：安全与治理（P1）

- [ ] **Task 11**: 安全集成
  - [ ] 11.1 binding 输入参数经过 InputSanitizer 清洗
  - [ ] 11.2 binding 返回数据经过 DataMasker 脱敏
  - [ ] 11.3 SQL binding write 操作联动 risk_level 确认流程
  - [ ] 11.4 单元测试：输入清洗、输出脱敏、risk_level 联动

- [ ] **Task 12**: 治理集成
  - [ ] 12.1 BindingTool 参与 governance.visibility 过滤
  - [ ] 12.2 BindingTool 调用消耗 governance.budget
  - [ ] 12.3 BindingTool 受 governance rate limiting 控制
  - [ ] 12.4 集成测试：visibility 过滤、budget 消耗、rate limiting

### Phase 4：开发者体验 + 示例（P2）

- [ ] **Task 13**: SKILL.md 书写门槛降低
  - [ ] 13.1 定义"最小可用 SKILL.md"规范：只需 name + description + body 即可工作
  - [ ] 13.2 `owlclaw skill init` 增加极简模式（只问 name 和 description）
  - [ ] 13.3 `tools` 简化声明：支持 YAML 内联的简化类型声明（`param: string` 替代完整 JSON Schema）
  - [ ] 13.4 运行时自动将简化声明展开为完整 JSON Schema
  - [ ] 13.5 编写 SKILL.md 书写指南（面向非技术用户，含最佳实践和常见模式）

- [ ] **Task 14**: Reference Implementation
  - [ ] 14.1 创建 `examples/binding-http/` 示例（HTTP binding 调用 REST API）
  - [ ] 14.2 创建示例的 SKILL.md（含 binding 声明 + 简化 tools 语法）
  - [ ] 14.3 创建 mock HTTP server 用于示例运行
  - [ ] 14.4 创建 shadow 模式对比示例
  - [ ] 14.5 创建"无 binding 无 handler"示例（body 含 curl 命令，Agent 通过 shell 工具执行）
  - [ ] 14.6 编写 README 说明三种 skill 模式（binding / @handler / shell 指令）

- [ ] **Task 15**: 文档更新
  - [ ] 15.1 更新 `examples/` 索引 README 包含 binding 示例
  - [ ] 15.2 更新 SKILL.md 模板库（skill-templates）增加 binding 示例模板
  - [ ] 15.3 更新 `owlclaw skill init` 生成的模板包含 binding 字段注释
  - [ ] 15.4 更新 `owlclaw skill init` 默认模板为"最小可用"版本

### Phase 5：cli-migrate 自动生成（P1，依赖 cli-migrate spec）

- [ ] **Task 16**: BindingGenerator — 从 OpenAPI 生成 HTTP Binding SKILL.md
  - [ ] 16.1 实现 `BindingGenerator` 类（位于 cli-migrate 的 generators 模块）
  - [ ] 16.2 实现 `generate_from_openapi()`：operationId/summary → name，description → SKILL.md description
  - [ ] 16.3 实现 OpenAPI parameters + requestBody → tools_schema + binding 映射
  - [ ] 16.4 实现 security schemes → `${ENV_VAR}` headers + prerequisites.env 映射
  - [ ] 16.5 实现 response schema → response_mapping 映射
  - [ ] 16.6 生成 SKILL.md body 含业务规则占位符（提示业务用户填写）
  - [ ] 16.7 生成的 SKILL.md 通过 `owlclaw skill validate` 验证
  - [ ] 16.8 单元测试：从 OpenAPI 规范生成 → 验证 binding 完整性 → 验证 prerequisites

- [ ] **Task 17**: BindingGenerator — 从 ORM 模型生成 SQL Binding SKILL.md
  - [ ] 17.1 实现 `generate_from_orm()`：model/table → name，columns → 参数化查询
  - [ ] 17.2 生成的 SQL binding 强制 `read_only: true`（默认），写操作需显式声明
  - [ ] 17.3 实现 connection string → prerequisites.env 映射
  - [ ] 17.4 生成 SKILL.md body 含数据访问规则占位符
  - [ ] 17.5 单元测试：从 ORM 模型生成 → 验证 SQL 参数化 → 验证 read_only

- [ ] **Task 18**: cli-migrate `--output-mode binding` 集成
  - [ ] 18.1 扩展 `owlclaw migrate scan` 命令增加 `--output-mode` 参数（handler/binding/both）
  - [ ] 18.2 `--output-mode binding` 时调用 BindingGenerator 替代 HandlerGenerator
  - [ ] 18.3 `--output-mode both` 时同时生成 @handler 代码和 binding SKILL.md
  - [ ] 18.4 集成测试：OpenAPI 规范 → `--output-mode binding` → 生成 SKILL.md → validate → Agent 加载
  - [ ] 18.5 集成测试：ORM 模型 → `--output-mode binding` → 生成 SKILL.md → validate → Agent 加载

- [ ] **Task 19**: 三种角色工作流文档与示例
  - [ ] 19.1 编写 IT 运维工作流文档（运行命令 + 配置环境变量）
  - [ ] 19.2 编写业务用户工作流文档（自然语言编写 SKILL.md body）
  - [ ] 19.3 创建端到端示例：OpenAPI → binding SKILL.md → 业务规则填写 → Agent 调用
  - [ ] 19.4 `owlclaw skill init --from-binding` 模式：从已有 binding SKILL.md 生成业务规则模板

## Backlog

- [ ] gRPC Binding Executor（Phase 3 里程碑，按需评估）
- [ ] 自定义 Binding 类型注册机制（Phase 3 里程碑）
- [ ] OwlHub binding 模板（依赖 owlhub Phase 2）
- [ ] GraphQL Binding Executor（社区需求驱动）
- [ ] Skill 信任等级（trusted/untrusted，依赖 OwlHub 审核机制）
- [ ] Skill 版本管理运行时支持（semver 比较、自动升级提示）

---

**维护者**: OwlClaw 核心团队
**最后更新**: 2026-02-24
