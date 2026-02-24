# 任务清单: declarative-binding

## 文档联动

- requirements: `.kiro/specs/declarative-binding/requirements.md`
- design: `.kiro/specs/declarative-binding/design.md`
- tasks: `.kiro/specs/declarative-binding/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`

## 任务

### Phase 0：契约与文档

- [ ] **Task 0**: 契约与文档对齐
  - [ ] 0.1 确认 requirements.md 完整且与架构文档 §4.12 一致
  - [ ] 0.2 确认 design.md 完整且包含所有组件设计
  - [ ] 0.3 确认 tasks.md 覆盖所有需求的实现
  - [ ] 0.4 定义 Binding Schema 的 JSON Schema（语言无关契约，供跨语言验证）

### Phase 1：核心基础设施（MVP — P0）

- [ ] **Task 1**: Binding Schema 与数据模型
  - [ ] 1.1 创建 `owlclaw/capabilities/bindings/` 包结构
  - [ ] 1.2 实现 `schema.py`：BindingConfig、RetryConfig 基类
  - [ ] 1.3 实现 HTTPBindingConfig（method、url、headers、body_template、response_mapping）
  - [ ] 1.4 实现 QueueBindingConfig（provider、connection、topic、format、headers_mapping）
  - [ ] 1.5 实现 SQLBindingConfig（connection、query、read_only、parameter_mapping、max_rows）
  - [ ] 1.6 实现 `parse_binding_config()` 工厂函数（dict → typed config）
  - [ ] 1.7 实现 schema 验证函数（必填字段、类型检查、credential 引用格式）
  - [ ] 1.8 单元测试：schema 解析、验证、round-trip 序列化

- [ ] **Task 2**: CredentialResolver
  - [ ] 2.1 实现 `credential.py`：CredentialResolver 类
  - [ ] 2.2 实现 `resolve()` 方法（`${ENV_VAR}` → 实际值）
  - [ ] 2.3 实现 `resolve_dict()` 方法（递归解析嵌套 dict）
  - [ ] 2.4 实现 `contains_potential_secret()` 静态方法（启发式检测明文密钥）
  - [ ] 2.5 支持多来源：os.environ → .env 文件 → owlclaw.yaml secrets
  - [ ] 2.6 缺失变量时抛出 ValueError（明确错误信息）
  - [ ] 2.7 单元测试：正常解析、缺失变量、嵌套 dict、secret 检测

- [ ] **Task 3**: Binding Executor 抽象与注册表
  - [ ] 3.1 实现 `executor.py`：BindingExecutor ABC（execute、validate_config、supported_modes）
  - [ ] 3.2 实现 BindingExecutorRegistry（register、get、list_types）
  - [ ] 3.3 未知类型时抛出 ValueError（含可用类型列表）
  - [ ] 3.4 单元测试：注册、获取、未知类型错误

- [ ] **Task 4**: HTTPBinding Executor（MVP 核心）
  - [ ] 4.1 实现 `http_executor.py`：HTTPBindingExecutor 类
  - [ ] 4.2 实现 URL 路径参数模板解析（`{param}` → 实际值）
  - [ ] 4.3 实现 headers 的 credential 解析
  - [ ] 4.4 实现 body_template 参数替换
  - [ ] 4.5 实现 response_mapping（JSONPath 提取、status_codes 映射）
  - [ ] 4.6 实现 active 模式：正常 HTTP 调用 + 超时 + 重试（指数退避）
  - [ ] 4.7 实现 shadow 模式：GET 正常执行，写操作只记录不发送
  - [ ] 4.8 单元测试：active GET/POST、shadow 拦截、超时重试、response mapping
  - [ ] 4.9 集成测试：使用 httpx mock 的完整调用链路

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

- [ ] **Task 7**: `owlclaw skill validate` 扩展 — binding 验证
  - [ ] 7.1 扩展 validate 命令检测 binding schema 格式
  - [ ] 7.2 验证必填字段（url for HTTP、topic for Queue、query for SQL）
  - [ ] 7.3 验证 credential 引用格式（`${ENV_VAR}` 而非明文）
  - [ ] 7.4 启发式检测明文密钥并发出警告
  - [ ] 7.5 单元测试：有效/无效 binding 验证

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

### Phase 4：示例与文档（P2）

- [ ] **Task 13**: Reference Implementation
  - [ ] 13.1 创建 `examples/binding-http/` 示例（HTTP binding 调用 REST API）
  - [ ] 13.2 创建示例的 SKILL.md + metadata.json（含 binding 声明）
  - [ ] 13.3 创建 mock HTTP server 用于示例运行
  - [ ] 13.4 创建 shadow 模式对比示例
  - [ ] 13.5 编写 README 说明 binding 使用方法

- [ ] **Task 14**: 文档更新
  - [ ] 14.1 更新 `examples/` 索引 README 包含 binding 示例
  - [ ] 14.2 更新 SKILL.md 模板库（skill-templates）增加 binding 示例模板
  - [ ] 14.3 更新 `owlclaw skill init` 生成的模板包含 binding 字段注释

## Backlog

- [ ] gRPC Binding Executor（Phase 3 里程碑，按需评估）
- [ ] 自定义 Binding 类型注册机制（Phase 3 里程碑）
- [ ] OwlHub binding 模板（依赖 owlhub Phase 2）
- [ ] GraphQL Binding Executor（社区需求驱动）

---

**维护者**: OwlClaw 核心团队
**最后更新**: 2026-02-24
