# Design Document: mcp-server

> **目标**: 实现 MCP 协议服务器,将 OwlClaw 能力通过标准 MCP 协议暴露给外部 AI Agent 系统  
> **状态**: 设计中  
> **最后更新**: 2025-02-22

---

## 1. Overview

mcp-server 是 OwlClaw 的 Model Context Protocol (MCP) 服务器实现,负责将 OwlClaw 注册的业务能力(@handler)和 Skills 知识通过标准 MCP 协议暴露给外部 AI Agent 系统(如 OpenClaw、Kiro IDE、Claude Desktop)。

### 1.1 核心目标

- 完整实现 MCP 协议规范 1.0(基于 JSON-RPC 2.0)
- 支持 stdio 和 HTTP/SSE 两种传输方式
- 将 OwlClaw @handler 函数映射为 MCP Tools
- 将 OwlClaw SKILL.md 文档映射为 MCP Resources
- 集成 OwlClaw 治理层(审计、限流、预算控制)
- 提供协议合规性和安全性保障

### 1.2 设计原则

1. **协议优先**: 严格遵循 MCP 规范,确保与标准 MCP 客户端兼容
2. **零侵入**: 不修改 OwlClaw 核心,通过适配层桥接
3. **治理透明**: MCP 调用自动经过 OwlClaw 治理层
4. **传输灵活**: 同时支持本地进程(stdio)和远程访问(HTTP/SSE)
5. **性能优先**: 工具列表和资源列表缓存,减少重复计算

### 1.3 非目标(MVP 阶段)

- Prompts 支持(后续扩展)
- Sampling 支持(后续扩展)
- 多租户隔离(Self-hosted 默认单租户)
- 高级认证机制(HTTP 模式的 TLS 为可选)

---

## 2. Architecture

### 2.1 整体架构


```
┌─────────────────────────────────────────────────────────────────────┐
│                        MCP 客户端                                    │
│              (OpenClaw / Kiro IDE / Claude Desktop)                 │
└────────────────────────┬────────────────────────────────────────────┘
                         │ JSON-RPC 2.0 消息
                         │
        ┌────────────────┴────────────────┐
        │                                 │
   stdio 传输                        HTTP/SSE 传输
   (标准输入输出)                    (网络请求)
        │                                 │
        └────────────────┬────────────────┘
                         │
┌─────────────────────────▼────────────────────────────────────────────┐
│                     MCP 协议层                                        │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  JSON-RPC 2.0 消息处理                                        │   │
│  │  - 消息解析与验证                                             │   │
│  │  - 请求路由(initialize/tools/list/tools/call/resources/*)    │   │
│  │  - 响应序列化                                                 │   │
│  │  - 错误处理(标准错误码)                                       │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────┬────────────────────────────────────────────┘
                          │
┌─────────────────────────▼────────────────────────────────────────────┐
│                   能力适配层                                          │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Tool Adapter                                                 │   │
│  │  - 从 Capability Registry 获取已注册的 @handler               │   │
│  │  - 生成 Tool Schema(从 type hints + docstring)                │   │
│  │  - 工具调用参数验证                                           │   │
│  │  - 工具执行结果转换                                           │   │
│  └──────────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Resource Adapter                                             │   │
│  │  - 扫描 Skills 目录获取 SKILL.md 文档                         │   │
│  │  - 生成 Resource URI(skill://category/name)                   │   │
│  │  - 资源元数据提取(frontmatter)                                │   │
│  │  - 资源内容读取                                               │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────┬────────────────────────────────────────────┘
                          │
┌─────────────────────────▼────────────────────────────────────────────┐
│                   OwlClaw 治理集成                                    │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  - 可见性过滤(哪些 handler 可以暴露为 MCP Tools)              │   │
│  │  - 预算检查(月度成本限制、单次成本限制)                       │   │
│  │  - 限流控制(每分钟调用次数、每日调用次数)                     │   │
│  │  - Ledger 记录(所有工具调用自动记录)                          │   │
│  │  - 客户端标识隔离(不同 MCP 客户端独立配额)                    │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────┬────────────────────────────────────────────┘
                          │
┌─────────────────────────▼────────────────────────────────────────────┐
│                   OwlClaw 核心                                        │
│  - Capability Registry(已注册的 @handler 函数)                       │
│  - Skills 知识体系(SKILL.md 文档)                                    │
│  - Governance Layer(治理规则引擎)                                    │
│  - Ledger(执行记录系统)                                              │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 分层职责

| 层次 | 职责 | 输入 | 输出 |
|------|------|------|------|
| **传输层** | 接收/发送 JSON-RPC 消息 | stdio 行 / HTTP 请求 | JSON-RPC 消息对象 |
| **协议层** | MCP 协议实现 | JSON-RPC 消息 | 路由到对应 handler |
| **适配层** | OwlClaw 能力映射 | MCP 请求 | OwlClaw 调用 |
| **治理层** | 访问控制和记录 | 工具调用请求 | 允许/拒绝 + 记录 |
| **核心层** | 业务能力执行 | 参数 | 执行结果 |

### 2.3 关键设计决策

1. **独立进程部署**: mcp-server 作为独立进程运行,通过 `owlclaw mcp-server start` 启动
2. **复用 OwlClaw 配置**: 读取 `owlclaw.yaml` 获取 Capability Registry 和 Skills 路径
3. **治理层透明集成**: 所有 MCP 工具调用自动经过 OwlClaw 治理层,无需额外配置
4. **缓存策略**: 工具列表和资源列表在 Capability Registry 未变更时复用缓存
5. **异步执行**: 长时间运行的工具通过 Hatchet 异步执行,HTTP/SSE 模式推送进度

---

## 3. Components and Interfaces

### 3.1 传输层组件

#### 3.1.1 StdioTransport


**职责**: 通过标准输入输出进行 JSON-RPC 消息传输

**接口**:
```python
class StdioTransport:
    async def read_message(self) -> dict:
        """从 stdin 读取一行 JSON-RPC 消息"""
        
    async def write_message(self, message: dict) -> None:
        """向 stdout 写入一行 JSON-RPC 响应"""
        
    async def write_error(self, error: str) -> None:
        """向 stderr 写入日志/错误信息"""
        
    async def close(self) -> None:
        """优雅关闭(等待当前消息处理完成)"""
```

**关键约束**:
- 每行一个完整的 JSON 消息(换行符分隔)
- stdout 仅用于 JSON-RPC 响应,日志输出到 stderr
- 支持不完整行缓冲(等待换行符)
- 收到 EOF 或 SIGTERM 时在 5 秒内完成清理

#### 3.1.2 HttpSseTransport

**职责**: 通过 HTTP/SSE 进行 JSON-RPC 消息传输和异步通知

**接口**:
```python
class HttpSseTransport:
    async def start_server(self, host: str, port: int) -> None:
        """启动 HTTP 服务器"""
        
    async def handle_rpc_request(self, request: Request) -> Response:
        """处理 POST /mcp 的 JSON-RPC 请求"""
        
    async def handle_sse_connection(self, request: Request) -> EventSourceResponse:
        """处理 GET /mcp/sse 的 SSE 连接"""
        
    async def push_notification(self, client_id: str, event: dict) -> None:
        """向指定客户端推送 SSE 事件"""
        
    async def handle_health_check(self, request: Request) -> Response:
        """处理 GET /health 健康检查"""
```

**关键约束**:
- 支持 CORS(可配置允许的来源)
- SSE 连接断开时自动清理资源
- 支持 TLS/HTTPS(可选,需配置证书)
- 响应头包含 `Content-Type: application/json`

### 3.2 协议层组件

#### 3.2.1 JsonRpcHandler

**职责**: JSON-RPC 2.0 消息解析、验证和路由

**接口**:
```python
class JsonRpcHandler:
    async def handle_message(self, raw_message: dict) -> dict:
        """处理 JSON-RPC 消息,返回响应"""
        
    def parse_request(self, raw: dict) -> JsonRpcRequest:
        """解析并验证 JSON-RPC 请求"""
        
    def create_response(self, id: Any, result: Any) -> dict:
        """创建 JSON-RPC 成功响应"""
        
    def create_error(self, id: Any, code: int, message: str, data: Any = None) -> dict:
        """创建 JSON-RPC 错误响应"""
```

**标准错误码**:
- `-32700`: Parse error(JSON 解析失败)
- `-32600`: Invalid Request(缺少必需字段)
- `-32601`: Method not found(不支持的方法)
- `-32602`: Invalid params(参数验证失败)
- `-32001`: Tool not found(MCP 扩展)
- `-32002`: Resource not found(MCP 扩展)
- `-32003`: Governance denied(MCP 扩展)
- `-32004`: Timeout(MCP 扩展)
- `-32005`: Execution error(MCP 扩展)

#### 3.2.2 McpProtocolHandler

**职责**: MCP 协议方法实现

**接口**:
```python
class McpProtocolHandler:
    async def handle_initialize(self, params: dict) -> dict:
        """处理 initialize 握手"""
        
    async def handle_tools_list(self, params: dict) -> dict:
        """处理 tools/list 请求"""
        
    async def handle_tools_call(self, params: dict) -> dict:
        """处理 tools/call 请求"""
        
    async def handle_resources_list(self, params: dict) -> dict:
        """处理 resources/list 请求"""
        
    async def handle_resources_read(self, params: dict) -> dict:
        """处理 resources/read 请求"""
```

**initialize 响应格式**:
```json
{
  "protocolVersion": "1.0",
  "serverInfo": {
    "name": "owlclaw-mcp-server",
    "version": "0.1.0"
  },
  "capabilities": {
    "tools": {"listChanged": true},
    "resources": {"listChanged": true, "subscribe": true}
  }
}
```

### 3.3 适配层组件

#### 3.3.1 ToolAdapter

**职责**: 将 OwlClaw @handler 映射为 MCP Tools

**接口**:
```python
class ToolAdapter:
    def __init__(self, capability_registry: CapabilityRegistry):
        self.registry = capability_registry
        self._cache: dict[str, ToolSchema] = {}
        
    async def list_tools(self, filters: dict = None) -> list[ToolSchema]:
        """获取可用工具列表(经过治理过滤)"""
        
    async def get_tool_schema(self, tool_name: str) -> ToolSchema:
        """获取指定工具的 Schema"""
        
    async def call_tool(self, tool_name: str, arguments: dict, context: CallContext) -> Any:
        """执行工具调用"""
        
    def generate_schema(self, handler: Callable) -> ToolSchema:
        """从 handler 生成 Tool Schema"""
```

**Tool Schema 生成规则**:
1. 工具名称: handler 的注册名称
2. 工具描述: handler 的 docstring 第一行
3. 参数定义: 从 Python type hints 提取,转换为 JSON Schema
4. 返回值类型: 从 return type hint 提取
5. 关联知识: 如果 handler 关联了 SKILL.md,将内容包含在描述中

**类型映射表**:
| Python Type | JSON Schema Type |
|-------------|------------------|
| `str` | `{"type": "string"}` |
| `int` | `{"type": "integer"}` |
| `float` | `{"type": "number"}` |
| `bool` | `{"type": "boolean"}` |
| `list[T]` | `{"type": "array", "items": {...}}` |
| `dict[str, T]` | `{"type": "object", "additionalProperties": {...}}` |
| `Optional[T]` | `{..., "nullable": true}` |
| `Union[T1, T2]` | `{"oneOf": [{...}, {...}]}` |

#### 3.3.2 ResourceAdapter

**职责**: 将 OwlClaw SKILL.md 映射为 MCP Resources

**接口**:
```python
class ResourceAdapter:
    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self._cache: dict[str, ResourceMetadata] = {}
        
    async def list_resources(self, filters: dict = None) -> list[ResourceMetadata]:
        """获取可用资源列表"""
        
    async def read_resource(self, uri: str) -> ResourceContent:
        """读取指定资源内容"""
        
    def generate_uri(self, skill_path: Path) -> str:
        """生成 Resource URI(skill://category/name)"""
        
    def parse_uri(self, uri: str) -> tuple[str, str]:
        """解析 Resource URI 为 (category, name)"""
```

**Resource URI 格式**:
- 格式: `skill://<category>/<name>`
- 示例: `skill://trading/entry-monitor`
- 通配符支持: `skill://trading/*`(列出 trading 分类下所有资源)

**Resource Metadata 结构**:
```python
@dataclass
class ResourceMetadata:
    uri: str                    # skill://category/name
    name: str                   # 资源名称
    description: str            # 资源描述(从 frontmatter)
    mime_type: str              # text/markdown
    size: int                   # 文件大小(字节)
    last_modified: datetime     # 最后更新时间
    tags: list[str]             # 标签(从 frontmatter)
    etag: str                   # ETag(用于缓存验证)
```

### 3.4 治理集成组件

#### 3.4.1 GovernanceFilter

**职责**: 在工具调用前应用治理规则

**接口**:
```python
class GovernanceFilter:
    async def filter_visible_tools(
        self, 
        all_tools: list[ToolSchema], 
        client_id: str
    ) -> list[ToolSchema]:
        """过滤可见工具列表"""
        
    async def check_call_permission(
        self, 
        tool_name: str, 
        client_id: str
    ) -> tuple[bool, str | None]:
        """检查工具调用权限,返回 (允许, 拒绝原因)"""
        
    async def record_call(
        self, 
        tool_name: str, 
        arguments: dict, 
        result: Any, 
        client_id: str,
        duration_ms: float,
        cost: float
    ) -> None:
        """记录工具调用到 Ledger"""
```

**治理规则应用顺序**:
1. 可见性过滤: 不可见的 handler 不出现在工具列表中
2. 预算检查: 月度成本超限 → 拒绝高成本工具
3. 限流检查: 调用频率超限 → 返回限流错误(包含重试时间)
4. 权限检查: 客户端无权限 → 返回权限拒绝错误
5. 执行记录: 所有调用(成功/失败)都记录到 Ledger

#### 3.4.2 ClientIdentifier

**职责**: 识别和隔离不同的 MCP 客户端

**接口**:
```python
class ClientIdentifier:
    def identify_client(self, context: dict) -> str:
        """从上下文识别客户端 ID"""
        
    def get_client_quota(self, client_id: str) -> QuotaConfig:
        """获取客户端的配额配置"""
```

**客户端识别策略**:
- stdio 模式: 从环境变量 `MCP_CLIENT_ID` 读取,默认 `"stdio-client"`
- HTTP 模式: 从请求头 `X-MCP-Client-ID` 读取,或使用 IP 地址

---

## 4. Data Models

### 4.1 MCP 消息模型

#### 4.1.1 JSON-RPC Request

```python
@dataclass
class JsonRpcRequest:
    jsonrpc: str = "2.0"        # 必须是 "2.0"
    method: str                 # MCP 方法名
    params: dict | None = None  # 方法参数
    id: int | str | None = None # 请求 ID(通知消息为 None)
```

#### 4.1.2 JSON-RPC Response

```python
@dataclass
class JsonRpcResponse:
    jsonrpc: str = "2.0"
    id: int | str
    result: Any | None = None   # 成功响应
    error: JsonRpcError | None = None  # 错误响应
```

#### 4.1.3 JSON-RPC Error

```python
@dataclass
class JsonRpcError:
    code: int                   # 错误码
    message: str                # 错误消息
    data: Any | None = None     # 额外错误信息
```

### 4.2 Tool 模型

#### 4.2.1 ToolSchema

```python
@dataclass
class ToolSchema:
    name: str                   # 工具名称
    description: str            # 工具描述
    input_schema: dict          # JSON Schema 定义参数
    governance_hints: dict | None = None  # 治理提示(成本、限流)
```

**input_schema 示例**:
```json
{
  "type": "object",
  "properties": {
    "session": {
      "type": "string",
      "description": "数据库会话标识"
    },
    "user_id": {
      "type": "integer",
      "description": "用户 ID"
    }
  },
  "required": ["session"]
}
```

#### 4.2.2 ToolCallRequest

```python
@dataclass
class ToolCallRequest:
    name: str                   # 工具名称
    arguments: dict             # 工具参数
```

#### 4.2.3 ToolCallResponse

```python
@dataclass
class ToolCallResponse:
    content: list[ContentBlock] # 返回内容块
    is_error: bool = False      # 是否为错误
```

### 4.3 Resource 模型

#### 4.3.1 ResourceMetadata

```python
@dataclass
class ResourceMetadata:
    uri: str                    # skill://category/name
    name: str                   # 资源名称
    description: str            # 资源描述
    mime_type: str              # MIME 类型
    size: int                   # 文件大小
    last_modified: datetime     # 最后更新时间
    tags: list[str]             # 标签
    etag: str                   # ETag
```

#### 4.3.2 ResourceContent

```python
@dataclass
class ResourceContent:
    uri: str                    # 资源 URI
    mime_type: str              # MIME 类型
    text: str | None = None     # 文本内容(text/*)
    blob: bytes | None = None   # 二进制内容(其他类型)
```

### 4.4 治理模型

#### 4.4.1 CallContext

```python
@dataclass
class CallContext:
    client_id: str              # 客户端标识
    tool_name: str              # 工具名称
    arguments: dict             # 工具参数
    timestamp: datetime         # 调用时间
    request_id: str             # 请求 ID(用于追踪)
```

#### 4.4.2 QuotaConfig

```python
@dataclass
class QuotaConfig:
    monthly_budget: float       # 月度预算(元)
    max_calls_per_minute: int   # 每分钟最大调用次数
    max_calls_per_day: int      # 每日最大调用次数
    max_cost_per_call: float    # 单次调用最大成本(元)
```

---

## 5. Implementation Details

### 5.1 JSON-RPC 消息处理流程


```python
async def handle_message(self, raw_message: dict) -> dict:
    """JSON-RPC 消息处理主流程"""
    try:
        # 1. 解析请求
        request = self.parse_request(raw_message)
        
        # 2. 验证 JSON-RPC 格式
        if request.jsonrpc != "2.0":
            return self.create_error(
                request.id, -32600, "Invalid Request: jsonrpc must be '2.0'"
            )
        
        # 3. 路由到对应的 MCP 方法
        if request.method == "initialize":
            result = await self.mcp_handler.handle_initialize(request.params)
        elif request.method == "tools/list":
            result = await self.mcp_handler.handle_tools_list(request.params)
        elif request.method == "tools/call":
            result = await self.mcp_handler.handle_tools_call(request.params)
        elif request.method == "resources/list":
            result = await self.mcp_handler.handle_resources_list(request.params)
        elif request.method == "resources/read":
            result = await self.mcp_handler.handle_resources_read(request.params)
        else:
            return self.create_error(
                request.id, -32601, f"Method not found: {request.method}"
            )
        
        # 4. 返回成功响应
        return self.create_response(request.id, result)
        
    except json.JSONDecodeError as e:
        return self.create_error(None, -32700, f"Parse error: {e}")
    except ValidationError as e:
        return self.create_error(
            raw_message.get("id"), -32602, f"Invalid params: {e}"
        )
    except Exception as e:
        logger.exception("Unexpected error handling message")
        return self.create_error(
            raw_message.get("id"), -32005, f"Execution error: {e}"
        )
```

### 5.2 Tool Schema 生成实现

```python
def generate_schema(self, handler: Callable) -> ToolSchema:
    """从 handler 生成 Tool Schema"""
    # 1. 获取函数签名
    sig = inspect.signature(handler)
    
    # 2. 提取 docstring
    doc = inspect.getdoc(handler) or ""
    description = doc.split("\n")[0] if doc else handler.__name__
    
    # 3. 生成参数 schema
    properties = {}
    required = []
    
    for param_name, param in sig.parameters.items():
        # 跳过特殊参数(self, session 等)
        if param_name in ("self", "session"):
            continue
            
        # 从 type hint 生成 JSON Schema
        param_schema = self._type_to_json_schema(param.annotation)
        
        # 从 docstring 提取参数描述
        param_desc = self._extract_param_description(doc, param_name)
        if param_desc:
            param_schema["description"] = param_desc
        
        properties[param_name] = param_schema
        
        # 判断是否必需(无默认值)
        if param.default == inspect.Parameter.empty:
            required.append(param_name)
    
    # 4. 构建 input_schema
    input_schema = {
        "type": "object",
        "properties": properties,
    }
    if required:
        input_schema["required"] = required
    
    # 5. 获取治理提示
    governance_hints = None
    if hasattr(handler, "_owlclaw_metadata"):
        metadata = handler._owlclaw_metadata
        governance_hints = {
            "estimated_cost": metadata.get("estimated_cost", 0.0),
            "max_duration_seconds": metadata.get("max_duration_seconds", 300),
        }
    
    return ToolSchema(
        name=handler.__name__,
        description=description,
        input_schema=input_schema,
        governance_hints=governance_hints,
    )

def _type_to_json_schema(self, type_hint: Any) -> dict:
    """将 Python type hint 转换为 JSON Schema"""
    # 处理 None
    if type_hint is type(None):
        return {"type": "null"}
    
    # 处理基础类型
    if type_hint == str:
        return {"type": "string"}
    elif type_hint == int:
        return {"type": "integer"}
    elif type_hint == float:
        return {"type": "number"}
    elif type_hint == bool:
        return {"type": "boolean"}
    
    # 处理泛型类型
    origin = get_origin(type_hint)
    args = get_args(type_hint)
    
    if origin == list:
        item_schema = self._type_to_json_schema(args[0]) if args else {}
        return {"type": "array", "items": item_schema}
    
    elif origin == dict:
        value_schema = self._type_to_json_schema(args[1]) if len(args) > 1 else {}
        return {"type": "object", "additionalProperties": value_schema}
    
    elif origin == Union:
        # Optional[T] = Union[T, None]
        if len(args) == 2 and type(None) in args:
            non_none_type = args[0] if args[1] is type(None) else args[1]
            schema = self._type_to_json_schema(non_none_type)
            schema["nullable"] = True
            return schema
        else:
            # Union[T1, T2, ...]
            return {"oneOf": [self._type_to_json_schema(t) for t in args]}
    
    # 默认: object
    return {"type": "object"}
```

### 5.3 Resource URI 解析实现

```python
def parse_uri(self, uri: str) -> tuple[str, str]:
    """解析 Resource URI 为 (category, name)
    
    格式: skill://<category>/<name>
    示例: skill://trading/entry-monitor
    """
    if not uri.startswith("skill://"):
        raise ValueError(f"Invalid resource URI scheme: {uri}")
    
    path = uri[8:]  # 去掉 "skill://"
    parts = path.split("/")
    
    if len(parts) != 2:
        raise ValueError(f"Invalid resource URI format: {uri}")
    
    category, name = parts
    
    if not category or not name:
        raise ValueError(f"Invalid resource URI: empty category or name")
    
    return category, name

def generate_uri(self, skill_path: Path) -> str:
    """生成 Resource URI
    
    路径: capabilities/trading/entry-monitor/SKILL.md
    URI: skill://trading/entry-monitor
    """
    # 获取相对于 skills_dir 的路径
    rel_path = skill_path.relative_to(self.skills_dir)
    
    # 去掉 SKILL.md 文件名
    parts = rel_path.parts[:-1]
    
    if len(parts) < 2:
        raise ValueError(f"Invalid skill path structure: {skill_path}")
    
    category = parts[0]
    name = parts[1]
    
    return f"skill://{category}/{name}"
```

### 5.4 工具调用执行流程

```python
async def handle_tools_call(self, params: dict) -> dict:
    """处理 tools/call 请求"""
    # 1. 提取参数
    tool_name = params.get("name")
    arguments = params.get("arguments", {})
    
    if not tool_name:
        raise ValueError("Missing required parameter: name")
    
    # 2. 构建调用上下文
    context = CallContext(
        client_id=self.client_identifier.identify_client(params),
        tool_name=tool_name,
        arguments=arguments,
        timestamp=datetime.now(),
        request_id=str(uuid.uuid4()),
    )
    
    # 3. 治理检查
    allowed, reason = await self.governance.check_call_permission(
        tool_name, context.client_id
    )
    if not allowed:
        raise GovernanceDeniedError(reason)
    
    # 4. 参数验证
    tool_schema = await self.tool_adapter.get_tool_schema(tool_name)
    self._validate_arguments(arguments, tool_schema.input_schema)
    
    # 5. 执行工具调用
    start_time = time.time()
    try:
        result = await self.tool_adapter.call_tool(tool_name, arguments, context)
        duration_ms = (time.time() - start_time) * 1000
        
        # 6. 计算成本(从 Langfuse trace 获取)
        cost = await self._calculate_cost(context.request_id)
        
        # 7. 记录到 Ledger
        await self.governance.record_call(
            tool_name, arguments, result, context.client_id, duration_ms, cost
        )
        
        # 8. 返回结果
        return {
            "content": [
                {"type": "text", "text": json.dumps(result, ensure_ascii=False)}
            ]
        }
        
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        
        # 记录失败
        await self.governance.record_call(
            tool_name, arguments, {"error": str(e)}, 
            context.client_id, duration_ms, 0.0
        )
        
        raise
```

### 5.5 缓存策略实现

```python
class CachedToolAdapter:
    """带缓存的 Tool Adapter"""
    
    def __init__(self, capability_registry: CapabilityRegistry):
        self.registry = capability_registry
        self._cache: dict[str, ToolSchema] = {}
        self._cache_version: int = 0
        self._registry_version: int = 0
    
    async def list_tools(self, filters: dict = None) -> list[ToolSchema]:
        """获取工具列表(带缓存)"""
        # 检查 registry 是否变更
        current_version = self.registry.get_version()
        if current_version != self._registry_version:
            # Registry 变更,清空缓存
            self._cache.clear()
            self._registry_version = current_version
            self._cache_version += 1
        
        # 如果缓存为空,重新生成
        if not self._cache:
            handlers = await self.registry.get_all_handlers()
            for handler in handlers:
                schema = self.generate_schema(handler)
                self._cache[schema.name] = schema
        
        # 应用过滤
        tools = list(self._cache.values())
        if filters:
            tools = self._apply_filters(tools, filters)
        
        return tools
    
    def get_cache_version(self) -> int:
        """获取缓存版本号(用于客户端缓存验证)"""
        return self._cache_version
```

### 5.6 异步工具执行(HTTP/SSE 模式)

```python
async def handle_tools_call_async(self, params: dict, client_id: str) -> dict:
    """异步工具调用(长时间运行的工具)"""
    tool_name = params.get("name")
    arguments = params.get("arguments", {})
    
    # 1. 检查工具是否支持异步执行
    tool_schema = await self.tool_adapter.get_tool_schema(tool_name)
    if not tool_schema.governance_hints.get("supports_async", False):
        # 不支持异步,直接同步执行
        return await self.handle_tools_call(params)
    
    # 2. 创建 Hatchet 任务
    task_id = str(uuid.uuid4())
    await self.hatchet_client.schedule_task(
        task_name=f"mcp_tool_call_{tool_name}",
        task_id=task_id,
        input={
            "tool_name": tool_name,
            "arguments": arguments,
            "client_id": client_id,
        },
    )
    
    # 3. 返回任务 ID
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps({
                    "status": "pending",
                    "task_id": task_id,
                    "message": "Tool execution started asynchronously"
                })
            }
        ]
    }

@hatchet.task()
async def execute_tool_async(ctx: Context):
    """Hatchet 任务: 异步执行工具"""
    input_data = ctx.workflow_input()
    tool_name = input_data["tool_name"]
    arguments = input_data["arguments"]
    client_id = input_data["client_id"]
    
    # 执行工具
    result = await tool_adapter.call_tool(tool_name, arguments, context)
    
    # 通过 SSE 推送结果
    await sse_transport.push_notification(client_id, {
        "type": "tool_result",
        "task_id": ctx.workflow_run_id(),
        "tool_name": tool_name,
        "result": result,
    })
    
    return result
```

---

## 6. Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: JSON-RPC Message Round Trip

*For any* valid JSON-RPC 2.0 message object, serializing to JSON then parsing back should produce an equivalent message object with the same jsonrpc version, method, params, and id fields.

**Validates: Requirements 1.2, 13.5**

### Property 2: Tool Schema Generation Completeness

*For any* registered @handler function with type hints, the generated Tool Schema should include all non-special parameters (excluding self, session) with their corresponding JSON Schema types derived from the Python type hints.

**Validates: Requirements 4.2, 4.3, 14.2, 14.3**

### Property 3: Resource URI Round Trip

*For any* valid skill file path under the skills directory, generating a Resource URI then parsing it back should produce the same category and name components.

**Validates: Requirements 6.2, 15.5**

### Property 4: Tool Call Governance Enforcement

*For any* tool call request, if the governance layer check fails (budget exceeded, rate limit hit, or permission denied), the tool should not be executed and an error response with code -32003 should be returned.

**Validates: Requirements 8.2, 8.3, 8.4, 8.5**

### Property 5: Error Response Standard Compliance

*For any* error condition (parse error, invalid request, method not found, invalid params), the returned error response should be a valid JSON-RPC 2.0 error with the correct error code, a descriptive message, and the original request id.

**Validates: Requirements 1.8, 1.9, 9.1, 9.2, 9.3**

### Property 6: Tool List Visibility Filtering

*For any* client requesting tools/list, all returned tools should pass the governance visibility filter for that client, and no tools marked as invisible should appear in the response.

**Validates: Requirements 4.7, 8.1**

### Property 7: Resource Content Integrity

*For any* existing SKILL.md file, reading it via resources/read should return content that exactly matches the file content on disk, with the correct MIME type (text/markdown).

**Validates: Requirements 7.1, 7.4**

### Property 8: Stdio Transport Message Isolation

*For any* sequence of JSON-RPC messages sent to stdio transport, each message should be processed independently, with responses written to stdout and logs written to stderr, ensuring no cross-contamination between output streams.

**Validates: Requirements 2.2, 2.3, 2.4**

### Property 9: HTTP SSE Connection Cleanup

*For any* SSE connection established to /mcp/sse, when the client disconnects, all associated resources (event streams, subscriptions, client state) should be cleaned up within a reasonable time period.

**Validates: Requirements 3.8**

### Property 10: Tool Execution Ledger Recording

*For any* tool call (successful or failed), a complete record should be written to the Ledger including tool name, arguments, result/error, client ID, duration, and cost.

**Validates: Requirements 5.6, 8.6**

### Property 11: Cache Invalidation on Registry Change

*For any* change to the Capability Registry (handler added, removed, or modified), the tool list cache should be invalidated and the next tools/list request should reflect the updated registry state.

**Validates: Requirements 4.10**

### Property 12: Parameter Validation Before Execution

*For any* tools/call request, if the provided arguments do not conform to the tool's input schema (missing required fields, wrong types, extra fields when not allowed), the tool should not be executed and an error response with code -32602 should be returned.

**Validates: Requirements 5.2, 5.3**

---

## 7. Error Handling

### 7.1 Error Response Structure

All errors follow JSON-RPC 2.0 error response format:

```python
{
    "jsonrpc": "2.0",
    "id": <request_id>,
    "error": {
        "code": <error_code>,
        "message": "<human_readable_message>",
        "data": {  # Optional additional context
            "details": "<detailed_error_info>",
            "retryable": <boolean>,
            "retry_after": <seconds>  # For rate limiting
        }
    }
}
```

### 7.2 Error Code Mapping

| Error Code | Error Type | Trigger Condition | Retryable |
|-----------|-----------|-------------------|-----------|
| -32700 | Parse error | Invalid JSON | No |
| -32600 | Invalid Request | Missing required fields | No |
| -32601 | Method not found | Unsupported MCP method | No |
| -32602 | Invalid params | Parameter validation failed | No |
| -32001 | Tool not found | Tool name doesn't exist | No |
| -32002 | Resource not found | Resource URI doesn't exist | No |
| -32003 | Governance denied | Budget/rate limit/permission | Maybe |
| -32004 | Timeout | Tool execution exceeded timeout | Yes |
| -32005 | Execution error | Tool threw exception | Maybe |

### 7.3 Error Handling Strategy

1. **Validation Errors**: Caught early, return immediately with descriptive message
2. **Governance Errors**: Include remaining quota and retry-after information
3. **Execution Errors**: Log full stack trace (dev mode), return sanitized message to client
4. **Timeout Errors**: Cancel ongoing execution, clean up resources
5. **Transport Errors**: Log and attempt graceful degradation

### 7.4 Error Logging

All errors are logged with structured context:

```python
logger.error(
    "Tool execution failed",
    extra={
        "error_code": -32005,
        "tool_name": tool_name,
        "client_id": client_id,
        "request_id": request_id,
        "error_type": type(e).__name__,
        "error_message": str(e),
        "stack_trace": traceback.format_exc()  # Dev mode only
    }
)
```

---

## 8. Testing Strategy

### 8.1 Dual Testing Approach

The testing strategy combines unit tests for specific scenarios and property-based tests for universal properties:

**Unit Tests**:
- Specific examples demonstrating correct behavior
- Edge cases (empty inputs, boundary values, special characters)
- Error conditions and exception handling
- Integration points between components

**Property-Based Tests**:
- Universal properties that hold for all inputs
- Comprehensive input coverage through randomization
- Minimum 100 iterations per property test
- Each property test references its design document property

### 8.2 Property-Based Testing Configuration

**Framework**: Use `hypothesis` for Python property-based testing

**Configuration**:
```python
from hypothesis import given, settings
import hypothesis.strategies as st

@settings(max_examples=100)
@given(message=st.json_rpc_messages())
def test_property_1_json_rpc_round_trip(message):
    """
    Feature: mcp-server, Property 1: JSON-RPC Message Round Trip
    
    For any valid JSON-RPC 2.0 message object, serializing to JSON 
    then parsing back should produce an equivalent message object.
    """
    serialized = json.dumps(message)
    parsed = json.loads(serialized)
    assert_equivalent_messages(message, parsed)
```

### 8.3 Test Coverage Requirements

| Component | Unit Test Coverage | Property Tests |
|-----------|-------------------|----------------|
| JSON-RPC Handler | 90%+ | 2 properties |
| Tool Adapter | 85%+ | 3 properties |
| Resource Adapter | 85%+ | 2 properties |
| Governance Filter | 90%+ | 2 properties |
| Transport Layer | 80%+ | 2 properties |

### 8.4 Integration Testing

Integration tests verify end-to-end flows:

1. **stdio Transport Flow**: Send JSON-RPC message via stdin → verify response on stdout
2. **HTTP/SSE Flow**: POST to /mcp → verify JSON response → establish SSE → verify events
3. **Tool Discovery Flow**: tools/list → verify all registered handlers appear
4. **Tool Execution Flow**: tools/call → verify governance check → verify execution → verify ledger record
5. **Resource Access Flow**: resources/list → resources/read → verify content matches disk

### 8.5 Test Data Generation

Use realistic test data:
- Sample @handler functions with various type signatures
- Sample SKILL.md files with different metadata
- Sample governance configurations
- Sample client identifiers and quotas

---

## 9. Configuration

### 9.1 配置文件结构

**文件路径**: `mcp-server.yaml`

```yaml
# MCP Server 配置
mcp_server:
  # 传输方式: stdio | http
  transport: stdio
  
  # HTTP 传输配置(仅当 transport=http 时生效)
  http:
    host: "0.0.0.0"
    port: 8080
    cors:
      enabled: true
      allowed_origins:
        - "http://localhost:3000"
        - "https://app.example.com"
    tls:
      enabled: false
      cert_file: "/path/to/cert.pem"
      key_file: "/path/to/key.pem"
  
  # 工具执行配置
  tools:
    default_timeout_seconds: 300
    async_threshold_seconds: 30  # 超过此时间的工具异步执行
    cache_ttl_seconds: 300
  
  # 资源配置
  resources:
    skills_dir: "./capabilities"
    cache_ttl_seconds: 600
  
  # 治理配置
  governance:
    enabled: true
    default_quota:
      monthly_budget: 500.0
      max_calls_per_minute: 60
      max_calls_per_day: 1000
      max_cost_per_call: 10.0
  
  # 日志配置
  logging:
    level: INFO
    format: json
    output: stderr  # stdio 模式必须是 stderr
```

### 9.2 环境变量覆盖

| 环境变量 | 配置项 | 默认值 |
|---------|--------|--------|
| `MCP_SERVER_TRANSPORT` | `mcp_server.transport` | `stdio` |
| `MCP_SERVER_HTTP_PORT` | `mcp_server.http.port` | `8080` |
| `MCP_SERVER_TOOLS_TIMEOUT` | `mcp_server.tools.default_timeout_seconds` | `300` |
| `MCP_SERVER_SKILLS_DIR` | `mcp_server.resources.skills_dir` | `./capabilities` |
| `MCP_SERVER_GOVERNANCE_ENABLED` | `mcp_server.governance.enabled` | `true` |

### 9.3 命令行参数

```bash
# 启动 MCP Server
owlclaw mcp-server start [OPTIONS]

Options:
  --transport [stdio|http]     传输方式(默认: stdio)
  --port INTEGER               HTTP 端口(默认: 8080)
  --config PATH                配置文件路径(默认: mcp-server.yaml)
  --skills-dir PATH            Skills 目录路径
  --help                       显示帮助信息

# 验证配置
owlclaw mcp-server config validate [--config PATH]

# 列出可用工具
owlclaw mcp-server tools list [--config PATH]

# 列出可用资源
owlclaw mcp-server resources list [--config PATH]
```

### 9.4 Security Configuration

**TLS/HTTPS Configuration** (HTTP mode only):
```yaml
http:
  tls:
    enabled: true
    cert_file: "/etc/owlclaw/certs/server.crt"
    key_file: "/etc/owlclaw/certs/server.key"
    # Optional: client certificate verification
    client_ca_file: "/etc/owlclaw/certs/ca.crt"
    verify_client: false
```

**CORS Configuration**:
```yaml
http:
  cors:
    enabled: true
    allowed_origins:
      - "https://app.example.com"
      - "https://admin.example.com"
    allowed_methods: ["GET", "POST", "OPTIONS"]
    allowed_headers: ["Content-Type", "Authorization", "X-MCP-Client-ID"]
    max_age: 3600
```

---

