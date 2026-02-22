# Requirements Document: mcp-server

## Introduction

mcp-server（MCP Server）是 OwlClaw 的 MCP 协议服务器实现,用于将 OwlClaw 的业务能力通过 Model Context Protocol (MCP) 暴露给外部 AI Agent 系统。作为 OwlClaw 与 OpenClaw、Kiro IDE 等 AI 系统的标准通道,mcp-server 负责协议实现、能力发现、工具调用、资源访问和治理集成。

根据 OwlClaw 的核心定位"让已有业务系统获得 AI 自主能力",mcp-server 是实现跨系统 AI 协作的关键基础设施。它使得 OwlClaw 注册的业务函数(@handler)和 Skills 知识能够被其他 AI Agent 发现和调用,同时保持 OwlClaw 的治理边界(审计、限流、预算)。

MCP 协议由 Anthropic 发起并开源(modelcontextprotocol.io),已成为 AI Agent 互操作的行业标准。mcp-server 设计为独立可部署的服务,支持 stdio 和 HTTP/SSE 两种传输方式。MVP 阶段优先支持 Tools 和 Resources,后续扩展 Prompts 和 Sampling。

## Glossary

- **MCP_Server**: Model Context Protocol 服务器,实现 MCP 协议规范的服务端
- **MCP_Client**: MCP 协议客户端,如 OpenClaw、Kiro IDE、Claude Desktop
- **MCP_Protocol**: Model Context Protocol,Anthropic 发起的 AI Agent 互操作协议
- **Tool**: MCP 协议中的可调用函数,对应 OwlClaw 的 @handler 能力
- **Resource**: MCP 协议中的可读取文档,对应 OwlClaw 的 SKILL.md 知识
- **Prompt**: MCP 协议中的预定义提示模板(可选)
- **Sampling**: MCP 协议中的 LLM 采样请求(可选)
- **Transport**: MCP 传输层,支持 stdio(标准输入输出)和 HTTP/SSE(服务器推送事件)
- **JSON_RPC**: JSON-RPC 2.0 协议,MCP 的底层消息格式
- **Handler**: OwlClaw 中使用 @handler 装饰器注册的业务函数
- **Skill**: OwlClaw 的能力单元,通过 SKILL.md 文档描述
- **Capability_Registry**: OwlClaw 的能力注册表,存储所有 @handler 注册的函数
- **Governance_Layer**: OwlClaw 的治理层,包括审计、限流、预算控制
- **Ledger**: OwlClaw 的执行记录系统,记录所有能力调用
- **Tool_Schema**: 工具的 JSON Schema 定义,描述参数和返回值类型
- **Resource_URI**: 资源的唯一标识符,格式为 skill://category/name

## Requirements

### Requirement 1: MCP 协议实现

**User Story:** 作为 MCP 客户端开发者,我希望 mcp-server 完整实现 MCP 协议规范,这样我可以使用标准 MCP 客户端与 OwlClaw 交互。

#### Acceptance Criteria

1. THE MCP_Server SHALL 实现 MCP 协议规范 1.0 版本的所有必需消息类型
2. THE MCP_Server SHALL 使用 JSON_RPC 2.0 格式进行消息序列化和反序列化
3. THE MCP_Server SHALL 支持 initialize 握手流程(客户端能力协商)
4. THE MCP_Server SHALL 支持 tools/list 请求返回可用工具列表
5. THE MCP_Server SHALL 支持 tools/call 请求执行指定工具
6. THE MCP_Server SHALL 支持 resources/list 请求返回可用资源列表
7. THE MCP_Server SHALL 支持 resources/read 请求读取指定资源内容
8. WHEN 收到不支持的消息类型,THEN THE MCP_Server SHALL 返回标准错误响应(错误码 -32601)
9. WHEN 收到格式错误的消息,THEN THE MCP_Server SHALL 返回解析错误响应(错误码 -32700)
10. THE MCP_Server SHALL 在响应中包含 jsonrpc: "2.0" 和正确的 id 字段

### Requirement 2: stdio 传输支持

**User Story:** 作为本地进程用户,我希望 mcp-server 支持 stdio 传输,这样我可以通过标准输入输出与 OwlClaw 通信。

#### Acceptance Criteria

1. WHEN 启动 mcp-server 时未指定传输方式,THEN THE MCP_Server SHALL 默认使用 stdio 传输
2. THE MCP_Server SHALL 从标准输入读取 JSON-RPC 消息(每行一个消息)
3. THE MCP_Server SHALL 向标准输出写入 JSON-RPC 响应(每行一个响应)
4. THE MCP_Server SHALL 将日志和诊断信息输出到标准错误(不污染标准输出)
5. THE MCP_Server SHALL 支持优雅关闭(收到 EOF 或 SIGTERM 时完成当前请求后退出)
6. THE MCP_Server SHALL 在 stdio 模式下禁用交互式提示和进度条
7. WHEN 标准输入关闭,THEN THE MCP_Server SHALL 在 5 秒内完成清理并退出
8. THE MCP_Server SHALL 处理标准输入的不完整行(缓冲直到收到换行符)

### Requirement 3: HTTP/SSE 传输支持

**User Story:** 作为远程客户端用户,我希望 mcp-server 支持 HTTP/SSE 传输,这样我可以通过网络与 OwlClaw 通信。

#### Acceptance Criteria

1. WHEN 启动 mcp-server 时指定 --transport http,THEN THE MCP_Server SHALL 启动 HTTP 服务器
2. THE MCP_Server SHALL 在指定端口监听 HTTP 请求(默认 8080)
3. THE MCP_Server SHALL 支持 POST /mcp 端点接收 JSON-RPC 请求
4. THE MCP_Server SHALL 支持 GET /mcp/sse 端点建立 Server-Sent Events 连接
5. THE MCP_Server SHALL 通过 SSE 连接推送异步通知(工具执行进度、资源变更)
6. THE MCP_Server SHALL 支持 CORS 跨域请求(可配置允许的来源)
7. THE MCP_Server SHALL 在 HTTP 响应头中包含 Content-Type: application/json
8. WHEN 客户端断开 SSE 连接,THEN THE MCP_Server SHALL 清理相关资源
9. THE MCP_Server SHALL 支持 HTTP 健康检查端点 GET /health
10. THE MCP_Server SHALL 在 HTTP 模式下支持 TLS/HTTPS(可选配置证书)

### Requirement 4: 工具发现

**User Story:** 作为 MCP 客户端,我希望能发现 OwlClaw 提供的所有可用工具,这样我可以了解可以调用哪些能力。

#### Acceptance Criteria

1. WHEN 客户端发送 tools/list 请求,THEN THE MCP_Server SHALL 返回所有已注册的 Handler 列表
2. THE MCP_Server SHALL 为每个工具生成符合 MCP 规范的 Tool_Schema
3. THE Tool_Schema SHALL 包含工具名称、描述、参数定义和返回值类型
4. THE MCP_Server SHALL 从 Handler 的类型注解提取参数类型(Python type hints)
5. THE MCP_Server SHALL 从 Handler 的 docstring 提取工具描述
6. WHERE Handler 关联了 SKILL.md,THE MCP_Server SHALL 将 SKILL.md 内容包含在工具描述中
7. THE MCP_Server SHALL 应用治理层的可见性过滤(不可见的 Handler 不出现在工具列表中)
8. THE MCP_Server SHALL 在工具列表中标注每个工具的治理约束(最大调用频率、成本限制)
9. THE MCP_Server SHALL 支持分页返回工具列表(当工具数量超过 100 个时)
10. THE MCP_Server SHALL 缓存工具列表(当 Capability_Registry 未变更时复用缓存)

### Requirement 5: 工具调用

**User Story:** 作为 MCP 客户端,我希望能调用 OwlClaw 的工具并获得执行结果,这样我可以使用 OwlClaw 的业务能力。

#### Acceptance Criteria

1. WHEN 客户端发送 tools/call 请求,THEN THE MCP_Server SHALL 查找对应的 Handler 并执行
2. THE MCP_Server SHALL 验证工具调用参数符合 Tool_Schema 定义
3. WHEN 参数验证失败,THEN THE MCP_Server SHALL 返回错误响应(错误码 -32602)
4. THE MCP_Server SHALL 在执行前应用治理层检查(预算、限流、权限)
5. WHEN 治理检查失败,THEN THE MCP_Server SHALL 返回错误响应并说明原因
6. THE MCP_Server SHALL 将工具调用记录到 Ledger(包括参数、结果、耗时、成本)
7. THE MCP_Server SHALL 支持异步工具执行(长时间运行的工具不阻塞其他请求)
8. WHERE 工具执行超过 30 秒,THE MCP_Server SHALL 通过 SSE 推送进度通知
9. WHEN 工具执行失败,THEN THE MCP_Server SHALL 返回错误响应并包含详细错误信息
10. THE MCP_Server SHALL 支持工具执行超时配置(默认 300 秒)

### Requirement 6: 资源发现

**User Story:** 作为 MCP 客户端,我希望能发现 OwlClaw 提供的所有可用资源,这样我可以了解可以读取哪些知识文档。

#### Acceptance Criteria

1. WHEN 客户端发送 resources/list 请求,THEN THE MCP_Server SHALL 返回所有 SKILL.md 文档列表
2. THE MCP_Server SHALL 为每个资源生成唯一的 Resource_URI(格式: skill://category/name)
3. THE MCP_Server SHALL 在资源列表中包含资源名称、描述、MIME 类型和大小
4. THE MCP_Server SHALL 从 SKILL.md 的 frontmatter 提取资源元数据
5. THE MCP_Server SHALL 支持按分类过滤资源(如 skill://ecommerce/*)
6. THE MCP_Server SHALL 支持按标签搜索资源(从 SKILL.md metadata 中提取标签)
7. THE MCP_Server SHALL 在资源列表中标注资源的最后更新时间
8. THE MCP_Server SHALL 支持分页返回资源列表(当资源数量超过 50 个时)
9. THE MCP_Server SHALL 缓存资源列表(当 Skills 目录未变更时复用缓存)
10. THE MCP_Server SHALL 支持资源变更通知(通过 SSE 推送资源列表更新事件)

### Requirement 7: 资源读取

**User Story:** 作为 MCP 客户端,我希望能读取 OwlClaw 的资源内容,这样我可以获取业务知识用于决策。

#### Acceptance Criteria

1. WHEN 客户端发送 resources/read 请求,THEN THE MCP_Server SHALL 返回指定资源的完整内容
2. THE MCP_Server SHALL 验证 Resource_URI 格式正确且资源存在
3. WHEN 资源不存在,THEN THE MCP_Server SHALL 返回错误响应(错误码 -32002)
4. THE MCP_Server SHALL 返回资源的 MIME 类型(SKILL.md 为 text/markdown)
5. THE MCP_Server SHALL 支持资源内容的增量读取(通过 range 参数)
6. THE MCP_Server SHALL 在响应中包含资源的 ETag(用于缓存验证)
7. WHERE 客户端提供 If-None-Match 头,THE MCP_Server SHALL 支持 304 Not Modified 响应
8. THE MCP_Server SHALL 记录资源读取到 Ledger(包括资源 URI、读取时间、客户端标识)
9. THE MCP_Server SHALL 支持资源读取权限控制(某些资源可能需要特定权限)
10. THE MCP_Server SHALL 在资源读取时应用治理层的访问频率限制

### Requirement 8: 治理集成

**User Story:** 作为 OwlClaw 管理员,我希望 mcp-server 集成 OwlClaw 的治理层,这样我可以控制外部 Agent 的访问边界。

#### Acceptance Criteria

1. THE MCP_Server SHALL 在工具调用前应用 Governance_Layer 的可见性过滤
2. THE MCP_Server SHALL 在工具调用前检查预算限制(月度成本、单次成本)
3. WHEN 预算超限,THEN THE MCP_Server SHALL 拒绝调用并返回预算超限错误
4. THE MCP_Server SHALL 在工具调用前检查限流规则(每分钟调用次数、每日调用次数)
5. WHEN 触发限流,THEN THE MCP_Server SHALL 拒绝调用并返回限流错误(包含重试时间)
6. THE MCP_Server SHALL 将所有工具调用记录到 Ledger(包括客户端标识、参数、结果、成本)
7. THE MCP_Server SHALL 支持按客户端标识隔离治理配额(不同客户端独立计算预算和限流)
8. THE MCP_Server SHALL 支持治理规则的动态更新(无需重启服务)
9. THE MCP_Server SHALL 在响应头中包含治理信息(剩余配额、限流状态)
10. THE MCP_Server SHALL 提供治理统计 API(查询各客户端的调用统计和配额使用情况)

### Requirement 9: 错误处理

**User Story:** 作为 MCP 客户端开发者,我希望 mcp-server 提供清晰的错误信息,这样我可以快速定位和解决问题。

#### Acceptance Criteria

1. WHEN 发生错误,THEN THE MCP_Server SHALL 返回符合 JSON-RPC 2.0 规范的错误响应
2. THE MCP_Server SHALL 使用标准错误码(-32700 解析错误、-32600 无效请求、-32601 方法不存在、-32602 参数无效)
3. THE MCP_Server SHALL 为 MCP 特定错误定义扩展错误码(-32001 工具不存在、-32002 资源不存在、-32003 治理拒绝)
4. THE MCP_Server SHALL 在错误响应中包含详细的错误消息和上下文信息
5. THE MCP_Server SHALL 在错误响应中包含错误堆栈(仅在开发模式下)
6. WHEN 工具执行超时,THEN THE MCP_Server SHALL 返回超时错误(错误码 -32004)
7. WHEN 工具执行抛出异常,THEN THE MCP_Server SHALL 捕获异常并返回执行错误(错误码 -32005)
8. THE MCP_Server SHALL 将所有错误记录到日志(包括错误类型、上下文、堆栈)
9. THE MCP_Server SHALL 支持错误重试建议(在错误响应中包含 retryable 字段)
10. THE MCP_Server SHALL 在严重错误时发送告警通知(如数据库连接失败、治理层不可用)

### Requirement 10: 配置管理

**User Story:** 作为 OwlClaw 部署者,我希望能灵活配置 mcp-server 的行为,这样我可以适配不同的部署环境。

#### Acceptance Criteria

1. THE MCP_Server SHALL 支持配置文件(mcp-server.yaml)
2. THE MCP_Server SHALL 支持环境变量覆盖配置文件(格式: MCP_SERVER_<KEY>)
3. THE MCP_Server SHALL 支持命令行参数覆盖配置文件和环境变量
4. THE MCP_Server SHALL 提供配置验证命令(owlclaw mcp-server config validate)
5. THE MCP_Server SHALL 在启动时验证配置并输出配置摘要
6. THE MCP_Server SHALL 支持配置传输方式(stdio / http)
7. THE MCP_Server SHALL 支持配置 HTTP 端口、CORS 来源、TLS 证书
8. THE MCP_Server SHALL 支持配置工具执行超时、资源缓存 TTL
9. THE MCP_Server SHALL 支持配置治理规则(预算限制、限流规则)
10. THE MCP_Server SHALL 支持配置日志级别和日志输出格式

### Requirement 11: 日志和监控

**User Story:** 作为运维工程师,我希望 mcp-server 提供详细的日志和监控指标,这样我可以追踪问题和优化性能。

#### Acceptance Criteria

1. THE MCP_Server SHALL 使用结构化日志(JSON 格式)
2. THE MCP_Server SHALL 记录所有 MCP 请求和响应(包括请求 ID、方法、参数、耗时)
3. THE MCP_Server SHALL 记录工具调用的详细信息(工具名、参数、结果、耗时、成本)
4. THE MCP_Server SHALL 记录治理决策(允许/拒绝、原因、剩余配额)
5. THE MCP_Server SHALL 支持日志级别配置(DEBUG/INFO/WARNING/ERROR)
6. THE MCP_Server SHALL 暴露 Prometheus 指标端点(GET /metrics)
7. THE MCP_Server SHALL 提供以下指标: 请求总数、请求耗时分布、工具调用次数、错误率、治理拒绝率
8. THE MCP_Server SHALL 支持分布式追踪(OpenTelemetry 集成)
9. THE MCP_Server SHALL 在日志中包含请求追踪 ID(用于关联分布式调用链)
10. THE MCP_Server SHALL 提供健康检查端点(GET /health)返回服务状态和依赖检查结果

### Requirement 12: 命令行接口

**User Story:** 作为命令行工具用户,我希望 mcp-server 提供友好的 CLI,这样我可以方便地启动和管理服务。

#### Acceptance Criteria

1. THE MCP_Server SHALL 提供 owlclaw mcp-server start 命令启动服务
2. THE MCP_Server SHALL 提供 --transport 参数选择传输方式(stdio / http)
3. THE MCP_Server SHALL 提供 --port 参数指定 HTTP 端口(默认 8080)
4. THE MCP_Server SHALL 提供 --config 参数指定配置文件路径
5. THE MCP_Server SHALL 提供 owlclaw mcp-server config validate 命令验证配置
6. THE MCP_Server SHALL 提供 owlclaw mcp-server tools list 命令列出可用工具
7. THE MCP_Server SHALL 提供 owlclaw mcp-server resources list 命令列出可用资源
8. THE MCP_Server SHALL 提供 --help 参数显示帮助信息
9. THE MCP_Server SHALL 提供 --version 参数显示版本信息
10. THE MCP_Server SHALL 在启动时输出服务地址和配置摘要

## Special Requirements Guidance

### Parser and Serializer Requirements

mcp-server 的核心功能是解析 MCP 协议消息和序列化响应,需要特别关注解析器和序列化器的正确性。

#### Requirement 13: JSON-RPC 消息解析器

**User Story:** 作为协议实现者,我需要可靠的 JSON-RPC 消息解析器,这样我可以正确处理客户端请求。

#### Acceptance Criteria

1. WHEN 提供有效的 JSON-RPC 2.0 消息,THE Parser SHALL 解析为消息对象并提取方法名和参数
2. WHEN 提供无效的 JSON-RPC 消息,THE Parser SHALL 返回描述性错误消息并指出错误位置
3. THE Parser SHALL 验证消息包含必需字段(jsonrpc、method、id)
4. THE Parser SHALL 支持批量请求(JSON 数组包含多个请求)
5. FOR ALL 有效的 JSON-RPC 消息,解析 → 序列化 → 解析 SHALL 产生等价的消息对象(round-trip property)

#### Requirement 14: Tool Schema 生成器

**User Story:** 作为工具发现功能的实现者,我需要可靠的 Tool Schema 生成器,这样我可以准确描述工具接口。

#### Acceptance Criteria

1. WHEN 提供 Handler 函数,THE Generator SHALL 生成符合 MCP 规范的 Tool_Schema
2. THE Generator SHALL 从 Python type hints 提取参数类型并转换为 JSON Schema 类型
3. THE Generator SHALL 从 docstring 提取工具描述和参数说明
4. THE Generator SHALL 处理复杂类型(List、Dict、Optional、Union)
5. FOR ALL Handler 函数,生成的 Tool_Schema SHALL 能被标准 JSON Schema 验证器验证通过

#### Requirement 15: Resource URI 解析器

**User Story:** 作为资源访问功能的实现者,我需要可靠的 Resource URI 解析器,这样我可以正确定位资源文件。

#### Acceptance Criteria

1. WHEN 提供有效的 Resource_URI(格式: skill://category/name),THE Parser SHALL 解析为分类和名称
2. WHEN 提供无效的 Resource_URI,THE Parser SHALL 返回描述性错误消息
3. THE Parser SHALL 验证 URI scheme 为 "skill"
4. THE Parser SHALL 支持通配符匹配(如 skill://ecommerce/*)
5. FOR ALL 有效的资源路径,路径 → URI → 路径 SHALL 产生等价的路径(round-trip property)

---

**维护者**: OwlClaw 核心团队  
**最后更新**: 2025-02-22  
**优先级**: P0  
**预估工作量**: 5-7 天
