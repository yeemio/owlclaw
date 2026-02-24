# 设计文档: declarative-binding

## 文档联动

- requirements: `.kiro/specs/declarative-binding/requirements.md`
- design: `.kiro/specs/declarative-binding/design.md`
- tasks: `.kiro/specs/declarative-binding/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`
- architecture: `docs/ARCHITECTURE_ANALYSIS.md` §4.12

## 简介

本文档描述 Declarative Binding（声明式工具绑定）系统的技术设计。该系统由以下核心组件组成：

1. **Binding Schema** — binding 字段的 JSON Schema 定义和验证
2. **Binding Executor Registry** — 执行器注册表，按类型分发调用
3. **HTTPBinding** — HTTP REST API 执行器
4. **QueueBinding** — 消息队列执行器（复用 queue_adapters）
5. **SQLBinding** — 数据库查询执行器
6. **BindingTool** — 自动生成的工具实例，桥接 binding 声明与执行器
7. **CredentialResolver** — 环境变量引用解析器

## 架构例外声明

本 spec 无数据库铁律例外。Binding 执行器操作的是外部业务系统，不涉及 OwlClaw 内部数据库。Ledger 记录走已有的 governance.ledger 模块。

## 架构概览

```
SKILL.md / metadata.json
├── tools_schema
│   ├── tool_a (有 binding)  ──→ BindingTool ──→ Executor ──→ 外部系统
│   └── tool_b (无 binding)  ──→ 需要 @handler 注册
│
└── 业务知识（自然语言）     ──→ Agent prompt 注入

                    ┌──────────────────────────────────┐
                    │     BindingExecutorRegistry       │
                    │  ┌────────────┬────────────────┐  │
                    │  │ HTTPBinding│ QueueBinding   │  │
                    │  │            │ (→queue_adapters)│ │
                    │  ├────────────┼────────────────┤  │
                    │  │ SQLBinding │ gRPCBinding    │  │
                    │  │            │ (reserved)     │  │
                    │  └────────────┴────────────────┘  │
                    └──────────┬───────────────────────┘
                               │
                    ┌──────────┴───────────────────────┐
                    │        CredentialResolver         │
                    │  ${ENV_VAR} → actual value        │
                    │  sources: .env / os.environ /     │
                    │           owlclaw.yaml secrets    │
                    └──────────────────────────────────┘
```

### 数据流

```
Skills 加载时:
  SkillsLoader.scan()
    → 解析 metadata.json
    → 检测 tools_schema 中的 binding 字段
    → 有 binding → 创建 BindingTool 并注册到 CapabilityRegistry
    → 无 binding → 保持现有行为（等待 @handler 注册）

Agent Run 时:
  function calling 选择工具
    → CapabilityRegistry.invoke_handler(tool_name, **args)
    → 如果是 BindingTool:
        → CredentialResolver 解析 ${ENV_VAR}
        → BindingExecutorRegistry 按 type 分发
        → Executor 执行调用（active/shadow）
        → governance.ledger 记录调用
        → security 模块清洗输入/输出
        → 返回结果给 Agent
    → 如果是 @handler:
        → 传统调用路径（不变）
```

## 组件设计

### 1. Binding Schema

**职责：** 定义 binding 字段的结构和验证规则。

#### 1.1 通用 Binding Schema

```python
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class RetryConfig:
    max_attempts: int = 3
    backoff_ms: int = 1000
    backoff_multiplier: float = 2.0


@dataclass
class BindingConfig:
    """Base binding configuration shared by all types."""
    type: Literal["http", "queue", "sql", "grpc"]
    mode: Literal["active", "shadow"] = "active"
    timeout_ms: int = 5000
    retry: RetryConfig = field(default_factory=RetryConfig)
```

#### 1.2 HTTP Binding Schema

```python
@dataclass
class ResponseMapping:
    path: str | None = None           # JSONPath to extract data
    error_path: str | None = None     # JSONPath for error message
    status_codes: dict[str, str] = field(default_factory=dict)


@dataclass
class HTTPBindingConfig(BindingConfig):
    type: Literal["http"] = "http"
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = "GET"
    url: str = ""                     # supports {param} templates
    headers: dict[str, str] = field(default_factory=dict)
    body_template: dict | None = None # for POST/PUT/PATCH
    response_mapping: ResponseMapping = field(default_factory=ResponseMapping)
```

#### 1.3 Queue Binding Schema

```python
@dataclass
class QueueBindingConfig(BindingConfig):
    type: Literal["queue"] = "queue"
    provider: Literal["kafka", "rabbitmq", "redis"] = "kafka"
    connection: str = ""              # ${ENV_VAR} reference
    topic: str = ""
    format: Literal["json", "avro", "protobuf"] = "json"
    headers_mapping: dict[str, str] = field(default_factory=dict)
```

#### 1.4 SQL Binding Schema

```python
@dataclass
class SQLBindingConfig(BindingConfig):
    type: Literal["sql"] = "sql"
    connection: str = ""              # ${ENV_VAR} reference
    query: str = ""                   # parameterized query with :param
    read_only: bool = True
    parameter_mapping: dict[str, str] = field(default_factory=dict)
    max_rows: int = 1000
```

### 2. CredentialResolver

**职责：** 解析 binding 配置中的 `${ENV_VAR}` 引用。

```python
import os
import re
import logging

logger = logging.getLogger(__name__)

ENV_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


class CredentialResolver:
    """Resolves ${ENV_VAR} references in binding configurations."""

    def __init__(self, extra_vars: dict[str, str] | None = None):
        self._extra_vars = extra_vars or {}

    def resolve(self, value: str) -> str:
        """Replace all ${ENV_VAR} references with actual values."""
        def _replace(match: re.Match) -> str:
            var_name = match.group(1)
            resolved = self._extra_vars.get(var_name) or os.environ.get(var_name)
            if resolved is None:
                raise ValueError(
                    f"Environment variable '{var_name}' not found. "
                    f"Set it in .env, system environment, or owlclaw.yaml secrets."
                )
            return resolved

        return ENV_VAR_PATTERN.sub(_replace, value)

    def resolve_dict(self, data: dict) -> dict:
        """Recursively resolve all string values in a dict."""
        resolved = {}
        for key, value in data.items():
            if isinstance(value, str):
                resolved[key] = self.resolve(value)
            elif isinstance(value, dict):
                resolved[key] = self.resolve_dict(value)
            else:
                resolved[key] = value
        return resolved

    @staticmethod
    def contains_potential_secret(value: str) -> bool:
        """Heuristic detection of plaintext secrets in binding config."""
        secret_patterns = [
            r"(?i)(bearer|token|key|secret|password|api.?key)\s*[:=]\s*['\"]?[A-Za-z0-9+/=]{20,}",
            r"(?i)^(sk-|pk-|ghp_|gho_|glpat-)",
        ]
        for pattern in secret_patterns:
            if re.search(pattern, value):
                return True
        return False
```

### 3. Binding Executor Registry

**职责：** 按 binding 类型注册和分发执行器。

```python
from abc import ABC, abstractmethod
from typing import Any


class BindingExecutor(ABC):
    """Base class for all binding executors."""

    @abstractmethod
    async def execute(
        self,
        config: BindingConfig,
        parameters: dict[str, Any],
        credential_resolver: CredentialResolver,
    ) -> dict[str, Any]:
        """Execute the binding call and return results."""
        ...

    @abstractmethod
    def validate_config(self, config: dict) -> list[str]:
        """Validate binding configuration, return list of errors."""
        ...

    @property
    @abstractmethod
    def supported_modes(self) -> list[str]:
        """Return supported execution modes."""
        ...


class BindingExecutorRegistry:
    """Registry of binding executors by type."""

    def __init__(self):
        self._executors: dict[str, BindingExecutor] = {}

    def register(self, binding_type: str, executor: BindingExecutor) -> None:
        self._executors[binding_type] = executor

    def get(self, binding_type: str) -> BindingExecutor:
        executor = self._executors.get(binding_type)
        if not executor:
            raise ValueError(
                f"No executor registered for binding type '{binding_type}'. "
                f"Available types: {list(self._executors.keys())}"
            )
        return executor

    def list_types(self) -> list[str]:
        return list(self._executors.keys())
```

### 4. HTTPBinding Executor

**职责：** 执行 HTTP REST API 调用。

```python
import httpx
import logging

logger = logging.getLogger(__name__)


class HTTPBindingExecutor(BindingExecutor):
    """Executes HTTP binding calls."""

    @property
    def supported_modes(self) -> list[str]:
        return ["active", "shadow"]

    def validate_config(self, config: dict) -> list[str]:
        errors = []
        if not config.get("url"):
            errors.append("HTTP binding requires 'url' field")
        method = config.get("method", "GET")
        if method not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
            errors.append(f"Unsupported HTTP method: {method}")
        return errors

    async def execute(
        self,
        config: HTTPBindingConfig,
        parameters: dict[str, Any],
        credential_resolver: CredentialResolver,
    ) -> dict[str, Any]:
        url = credential_resolver.resolve(config.url)
        # Resolve path parameters: {param_name} → actual value
        for key, value in parameters.items():
            url = url.replace(f"{{{key}}}", str(value))

        headers = credential_resolver.resolve_dict(config.headers)

        is_write = config.method in ("POST", "PUT", "PATCH", "DELETE")

        if config.mode == "shadow" and is_write:
            return {
                "_shadow": True,
                "_method": config.method,
                "_url": url,
                "_body": config.body_template,
                "_parameters": parameters,
                "_action": "logged_not_executed",
            }

        async with httpx.AsyncClient(timeout=config.timeout_ms / 1000) as client:
            body = None
            if config.body_template and is_write:
                body = self._resolve_body(config.body_template, parameters)

            for attempt in range(config.retry.max_attempts):
                try:
                    response = await client.request(
                        method=config.method,
                        url=url,
                        headers=headers,
                        json=body,
                    )
                    return self._map_response(response, config.response_mapping)
                except httpx.TimeoutException:
                    if attempt == config.retry.max_attempts - 1:
                        raise
                    backoff = config.retry.backoff_ms * (
                        config.retry.backoff_multiplier ** attempt
                    ) / 1000
                    await asyncio.sleep(backoff)

    def _resolve_body(self, template: dict, parameters: dict) -> dict:
        """Replace parameter references in body template."""
        import json
        body_str = json.dumps(template)
        for key, value in parameters.items():
            body_str = body_str.replace(f"{{{key}}}", json.dumps(value))
        return json.loads(body_str)

    def _map_response(
        self, response: httpx.Response, mapping: ResponseMapping
    ) -> dict:
        """Extract relevant data from HTTP response."""
        status = str(response.status_code)
        semantic_status = mapping.status_codes.get(
            status, "success" if response.is_success else "error"
        )

        try:
            data = response.json()
        except Exception:
            data = response.text

        if mapping.path and isinstance(data, dict):
            data = self._extract_path(data, mapping.path)

        if semantic_status != "success" and mapping.error_path and isinstance(data, dict):
            error_msg = self._extract_path(data, mapping.error_path)
            return {"status": semantic_status, "error": error_msg, "status_code": response.status_code}

        return {"status": semantic_status, "data": data, "status_code": response.status_code}

    @staticmethod
    def _extract_path(data: dict, path: str) -> Any:
        """Simple JSONPath-like extraction ($.key1.key2)."""
        keys = path.lstrip("$.").split(".")
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current
```

### 5. QueueBinding Executor

**职责：** 执行消息队列发送操作，复用 `owlclaw/integrations/queue_adapters/`。

```python
class QueueBindingExecutor(BindingExecutor):
    """Executes queue binding calls, reusing existing queue adapters."""

    @property
    def supported_modes(self) -> list[str]:
        return ["active", "shadow"]

    def validate_config(self, config: dict) -> list[str]:
        errors = []
        if not config.get("connection"):
            errors.append("Queue binding requires 'connection' field")
        if not config.get("topic"):
            errors.append("Queue binding requires 'topic' field")
        provider = config.get("provider", "kafka")
        if provider not in ("kafka", "rabbitmq", "redis"):
            errors.append(f"Unsupported queue provider: {provider}")
        return errors

    async def execute(
        self,
        config: QueueBindingConfig,
        parameters: dict[str, Any],
        credential_resolver: CredentialResolver,
    ) -> dict[str, Any]:
        connection = credential_resolver.resolve(config.connection)

        if config.mode == "shadow":
            return {
                "_shadow": True,
                "_provider": config.provider,
                "_topic": config.topic,
                "_message": parameters,
                "_action": "logged_not_executed",
            }

        # Resolve headers_mapping
        headers = {}
        for key, template in config.headers_mapping.items():
            for param_key, param_value in parameters.items():
                template = template.replace(f"{{{param_key}}}", str(param_value))
            headers[key] = template

        from owlclaw.integrations.queue_adapters import get_adapter
        adapter = get_adapter(config.provider, connection)
        await adapter.publish(
            topic=config.topic,
            message=parameters,
            headers=headers,
        )

        return {"status": "published", "topic": config.topic}
```

### 6. SQLBinding Executor

**职责：** 执行参数化 SQL 查询。

```python
class SQLBindingExecutor(BindingExecutor):
    """Executes SQL binding calls with mandatory parameterized queries."""

    @property
    def supported_modes(self) -> list[str]:
        return ["active", "shadow"]

    def validate_config(self, config: dict) -> list[str]:
        errors = []
        if not config.get("connection"):
            errors.append("SQL binding requires 'connection' field")
        if not config.get("query"):
            errors.append("SQL binding requires 'query' field")
        query = config.get("query", "")
        # Reject queries with string interpolation patterns
        if "%" in query or "f'" in query or 'f"' in query:
            errors.append("SQL binding query must use parameterized placeholders (:param), not string interpolation")
        if not config.get("parameter_mapping") and ":" in query:
            errors.append("SQL binding with parameterized query requires 'parameter_mapping' field")
        return errors

    async def execute(
        self,
        config: SQLBindingConfig,
        parameters: dict[str, Any],
        credential_resolver: CredentialResolver,
    ) -> dict[str, Any]:
        connection_url = credential_resolver.resolve(config.connection)

        if not config.read_only:
            # Write operations in shadow mode only log
            if config.mode == "shadow":
                return {
                    "_shadow": True,
                    "_query": config.query,
                    "_parameters": parameters,
                    "_action": "logged_not_executed",
                }

        # Map tool parameters to SQL parameters
        sql_params = {}
        for sql_name, tool_param in config.parameter_mapping.items():
            sql_params[sql_name] = parameters.get(tool_param.lstrip(":"))

        import sqlalchemy
        engine = sqlalchemy.create_engine(connection_url)
        async with engine.connect() as conn:
            result = await conn.execute(
                sqlalchemy.text(config.query),
                sql_params,
            )
            if config.read_only:
                rows = result.fetchmany(config.max_rows)
                columns = list(result.keys())
                return {
                    "status": "success",
                    "data": [dict(zip(columns, row)) for row in rows],
                    "row_count": len(rows),
                }
            else:
                return {
                    "status": "success",
                    "affected_rows": result.rowcount,
                }
```

### 7. BindingTool

**职责：** 桥接 binding 声明与执行器，作为 CapabilityRegistry 中的工具实例。

```python
class BindingTool:
    """Auto-generated tool from binding declaration."""

    def __init__(
        self,
        name: str,
        description: str,
        parameters_schema: dict,
        binding_config: BindingConfig,
        executor_registry: BindingExecutorRegistry,
        credential_resolver: CredentialResolver,
        ledger: "Ledger | None" = None,
    ):
        self.name = name
        self.description = description
        self.parameters_schema = parameters_schema
        self.binding_config = binding_config
        self.executor_registry = executor_registry
        self.credential_resolver = credential_resolver
        self.ledger = ledger

    async def __call__(self, **kwargs) -> dict:
        """Execute the binding tool."""
        import time
        start = time.monotonic()

        executor = self.executor_registry.get(self.binding_config.type)
        try:
            result = await executor.execute(
                self.binding_config,
                kwargs,
                self.credential_resolver,
            )
            elapsed_ms = (time.monotonic() - start) * 1000

            if self.ledger:
                self.ledger.record(
                    tool_name=self.name,
                    binding_type=self.binding_config.type,
                    mode=self.binding_config.mode,
                    parameters=kwargs,
                    result_summary=self._summarize(result),
                    elapsed_ms=elapsed_ms,
                    status="success",
                )

            return result
        except Exception as e:
            elapsed_ms = (time.monotonic() - start) * 1000
            if self.ledger:
                self.ledger.record(
                    tool_name=self.name,
                    binding_type=self.binding_config.type,
                    mode=self.binding_config.mode,
                    parameters=kwargs,
                    result_summary=str(e),
                    elapsed_ms=elapsed_ms,
                    status="error",
                )
            raise

    @staticmethod
    def _summarize(result: dict, max_length: int = 500) -> str:
        """Create a summary of the result for Ledger recording."""
        import json
        text = json.dumps(result, ensure_ascii=False, default=str)
        if len(text) > max_length:
            return text[:max_length] + "...(truncated)"
        return text
```

### 8. Skills Loader 扩展

**职责：** 在 `SkillsLoader.scan()` 中检测 binding 字段，自动创建 BindingTool。

扩展点位于 `owlclaw/capabilities/skills.py` 的 `SkillsLoader` 类：

```python
# 在 SkillsLoader._parse_skill_file() 中增加 binding 检测
# 在 CapabilityRegistry 中增加 register_binding_tool() 方法

def auto_register_binding_tools(
    skills_loader: SkillsLoader,
    registry: CapabilityRegistry,
    executor_registry: BindingExecutorRegistry,
    credential_resolver: CredentialResolver,
    ledger: "Ledger | None" = None,
) -> list[str]:
    """Scan all skills and auto-register tools with binding declarations."""
    registered = []
    for skill in skills_loader.list_skills():
        tools_schema = skill.metadata.get("tools_schema", {})
        for tool_name, tool_def in tools_schema.items():
            binding = tool_def.get("binding")
            if not binding:
                continue
            # Parse binding config
            config = parse_binding_config(binding)
            # Create BindingTool
            tool = BindingTool(
                name=tool_name,
                description=tool_def.get("description", ""),
                parameters_schema=tool_def.get("parameters", {}),
                binding_config=config,
                executor_registry=executor_registry,
                credential_resolver=credential_resolver,
                ledger=ledger,
            )
            # Register — @handler takes precedence if already registered
            if tool_name not in registry.handlers:
                registry.register_handler(tool_name, tool)
                registered.append(tool_name)
    return registered
```

## 包结构

```
owlclaw/capabilities/
├── __init__.py
├── skills.py              # 已有 — 扩展 binding 检测
├── registry.py            # 已有 — 扩展 BindingTool 注册
├── knowledge.py           # 已有 — 不变
└── bindings/              # 新增
    ├── __init__.py        # 导出 BindingExecutorRegistry, BindingTool
    ├── schema.py          # BindingConfig, HTTPBindingConfig, etc.
    ├── executor.py        # BindingExecutor ABC, BindingExecutorRegistry
    ├── http_executor.py   # HTTPBindingExecutor
    ├── queue_executor.py  # QueueBindingExecutor
    ├── sql_executor.py    # SQLBindingExecutor
    ├── credential.py      # CredentialResolver
    └── tool.py            # BindingTool
```

## 与治理层的集成

BindingTool 注册到 CapabilityRegistry 后，自动受以下治理约束：

1. **visibility 过滤**：BindingTool 与 @handler 工具一样参与可见性过滤，Agent 只能看到治理层允许的工具子集
2. **ledger 记录**：所有 binding 调用记录到 Ledger，shadow 模式额外标记 `mode=shadow`
3. **budget 控制**：binding 调用消耗预算（按调用次数或 token 计），超预算时拒绝调用
4. **rate limiting**：binding 调用受限流控制，防止 Agent 过度调用外部系统

## 安全模型

1. **输入清洗**：binding 调用的参数经过 `owlclaw.security.InputSanitizer` 清洗（防 prompt injection 注入到 URL/SQL）
2. **输出清洗**：binding 返回的数据经过 `owlclaw.security.DataMasker` 脱敏（PII/敏感字段）
3. **SQL 注入防护**：SQL binding 强制参数化查询，validate_config 拒绝字符串拼接模式
4. **credential 隔离**：`${ENV_VAR}` 在运行时解析，SKILL.md 中不包含明文密钥
5. **risk_level 联动**：SQL write 操作需要 SKILL.md 声明 `risk_level: high`，触发人工确认流程

## 测试策略

### 单元测试

- CredentialResolver: 正常解析、缺失变量报错、嵌套 dict 解析、secret 检测
- HTTPBindingExecutor: active GET/POST、shadow 写操作拦截、超时重试、response mapping
- QueueBindingExecutor: active publish、shadow 拦截、headers mapping
- SQLBindingExecutor: 参数化查询、read_only 强制、string interpolation 拒绝
- BindingTool: Ledger 记录、executor 分发、错误处理
- Binding Schema 验证: 必填字段、类型检查、credential 引用格式

### 集成测试

- Skills 加载 → binding 检测 → BindingTool 注册 → 调用完整链路
- @handler 与 BindingTool 共存（@handler 优先）
- governance visibility 过滤 BindingTool
- shadow 模式 → Ledger 记录 → 可查询

### 属性测试

- CredentialResolver.resolve(resolve(x)) == resolve(x)（幂等性）
- 所有 binding config 可 JSON 序列化/反序列化 round-trip

## 依赖关系

### 外部依赖

- **httpx**: HTTP 客户端（async，已在项目中使用）
- **sqlalchemy**: SQL 执行（已在项目中使用）

### 内部依赖

- **owlclaw.capabilities.skills**: SkillsLoader 扩展
- **owlclaw.capabilities.registry**: CapabilityRegistry 扩展
- **owlclaw.governance.ledger**: 调用记录
- **owlclaw.governance.visibility**: 可见性过滤
- **owlclaw.security**: 输入/输出清洗
- **owlclaw.config**: 配置解析（owlclaw.yaml secrets）
- **owlclaw.integrations.queue_adapters**: Queue binding 复用

---

**维护者**: OwlClaw 核心团队
**最后更新**: 2026-02-24
