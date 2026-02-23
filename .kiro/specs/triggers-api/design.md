# API 调用触发器设计文档

## 文档联动

- requirements: `.kiro/specs/triggers-api/requirements.md`
- design: `.kiro/specs/triggers-api/design.md`
- tasks: `.kiro/specs/triggers-api/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


## 概述

API 触发器通过内置轻量 HTTP 服务暴露 REST 端点，外部系统通过 HTTP 请求触发 Agent Run。支持同步（等待 Agent 决策结果）和异步（立即返回 run_id）两种响应模式。

## 技术栈统一与架构对齐

为避免核心链路双栈维护和重复造轮子，API 触发器遵循以下规则：

1. 核心实现统一 Python（与 `owlclaw` 主栈一致），不引入 TypeScript/Node 核心实现。
2. 触发器仅负责接入与上下文组装，Agent 执行必须通过 `owlclaw.agent.runtime.AgentRuntime`。
3. 治理、审计、调度分别复用现有组件：`owlclaw.governance.visibility` / `owlclaw.governance.ledger` / `owlclaw.integrations.hatchet`。
4. 任何代码示例仅表达契约，不得绕过上述真实组件边界。

## 架构例外声明（实现阶段需固化）

本 spec 当前未引入业务层面的数据库铁律例外。实现阶段遵循以下约束：

1. API 触发请求日志与执行记录落库时，必须遵循 `tenant_id` 前缀索引与 `TIMESTAMPTZ` 规范。
2. 同步/异步响应模式仅影响交互层，不得绕过治理与审计链路。
3. `alembic_version` 属于 Alembic 系统表，不适用业务表约束。

## 架构概览

```
┌───────────────────────────────────────────────────────────┐
│                    External System                          │
│                                                             │
│  POST /api/v1/analysis  ──→  Authorization Header           │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP
                               ▼
┌───────────────────────────────────────────────────────────┐
│              OwlClaw API Trigger (Starlette)                │
│                                                             │
│  ┌───────────────┐                                        │
│  │  AuthMiddleware │   API Key / Bearer Token 验证          │
│  └───────┬───────┘                                        │
│          │                                                  │
│  ┌───────▼───────┐                                        │
│  │  InputSanitizer│   请求体 sanitization (security spec)   │
│  └───────┬───────┘                                        │
│          │                                                  │
│  ┌───────▼───────┐                                        │
│  │ GovernanceGate │   rate limit / budget check             │
│  │               │   429 Too Many Requests                  │
│  │               │   503 Service Unavailable                │
│  └───────┬───────┘                                        │
│          │                                                  │
│  ┌───────▼───────────────────────────────────────────┐    │
│  │  ResponseRouter                                     │    │
│  │                                                     │    │
│  │  ┌──────────────┐      ┌──────────────────────┐   │    │
│  │  │  Sync Mode    │      │  Async Mode           │   │    │
│  │  │  await result  │      │  return 202 + run_id  │   │    │
│  │  │  → 200 + body │      │  GET /runs/{id}/result │   │    │
│  │  └──────────────┘      └──────────────────────┘   │    │
│  └───────┬───────────────────────────────────────────┘    │
│          │                                                  │
│  ┌───────▼───────┐                                        │
│  │ AgentRunTrigger│   → Hatchet task dispatch               │
│  └───────────────┘                                        │
└───────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. APITriggerConfig（配置模型）

```python
from pydantic import BaseModel

class APITriggerConfig(BaseModel):
    path: str                           # /api/v1/analysis
    method: str = "POST"                # POST | GET
    event_name: str                     # analysis_request
    description: str = ""
    response_mode: str = "async"        # sync | async
    sync_timeout_seconds: int = 60      # 同步模式超时
    focus: str | None = None
    auth_required: bool = True
    fallback: Callable | None = None    # 可选：迁移期 fallback（migration_weight < 1.0）
```

### 2. APITriggerServer（HTTP 服务）

```python
from starlette.applications import Starlette
from starlette.routing import Route

class APITriggerServer:
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8080,
        auth_provider: AuthProvider | None = None,
        governance: GovernanceService | None = None,
        sanitizer: InputSanitizer | None = None,
    ):
        self._app = Starlette(routes=[], on_startup=[self._startup])
        self._triggers: dict[str, APITriggerConfig] = {}

    def register(self, config: APITriggerConfig) -> None:
        route = Route(
            config.path,
            endpoint=self._create_handler(config),
            methods=[config.method],
        )
        self._app.routes.append(route)
        self._triggers[config.path] = config

    def _create_handler(self, config: APITriggerConfig):
        async def handler(request):
            # 1. 认证
            if config.auth_required:
                await self._authenticate(request)

            # 2. 解析 + sanitize 请求体
            body = await self._parse_body(request)
            if self.sanitizer:
                sanitize_result = self.sanitizer.sanitize(json.dumps(body, ensure_ascii=False), source="api")
                body = self._parse_sanitized_payload(sanitize_result.sanitized)
                if sanitize_result.changed:
                    self._record_security_audit("sanitization", sanitize_result)

            # 3. 治理检查
            if not await self.governance_gate.allow_request(config.event_name):
                return self._rate_limited_response(config)

            # 4. 分发
            if config.response_mode == "sync":
                return await self._handle_sync(config, body, request)
            else:
                return await self._handle_async(config, body, request)

        return handler
```

### 3. AuthProvider（认证抽象）

```python
class AuthProvider(ABC):
    @abstractmethod
    async def authenticate(self, request: Request) -> AuthResult: ...

class APIKeyAuthProvider(AuthProvider):
    """X-API-Key header 认证"""
    def __init__(self, valid_keys: set[str]): ...

class BearerTokenAuthProvider(AuthProvider):
    """Authorization: Bearer <token> 认证"""
    def __init__(self, token_validator: Callable): ...
```

### 4. 同步/异步响应处理

```python
class APITriggerServer:
    async def _handle_sync(self, config, body, request):
        """同步模式：等待 Agent Run 完成"""
        result = await self.agent_runtime.trigger_event(
            event_name=config.event_name,
            focus=config.focus,
            payload=body,
            tenant_id=self._tenant_id_from_request(request),
        )
        try:
            return JSONResponse(result)
        except asyncio.TimeoutError:
            return JSONResponse(
                {"status": "timeout"},
                status_code=408,
            )

    async def _handle_async(self, config, body, request):
        """异步模式：立即返回 run_id"""
        run_id = await self._dispatch_async_run(
            event_name=config.event_name,
            tenant_id=self._tenant_id_from_request(request),
            payload=body,
            focus=config.focus,
        )
        return JSONResponse(
            {"run_id": str(run_id), "status": "accepted"},
            status_code=202,
            headers={"Location": f"/runs/{run_id}/result"},
        )
```

### 5. Run 结果查询端点

```python
# 内建端点：查询异步 run 的结果
@Route("/runs/{run_id}/result", methods=["GET"])
async def get_run_result(request):
    run_id = request.path_params["run_id"]
    run = await agent_runner.get_run(run_id)
    if run is None:
        return JSONResponse({"error": "not_found"}, status_code=404)
    if run.status == "completed":
        return JSONResponse({"run_id": run_id, "status": "completed", "result": run.result})
    return JSONResponse({"run_id": run_id, "status": run.status}, status_code=200)
```

### 6. API 集成（装饰器 + 函数调用双模式）

```python
# 装饰器风格（带 fallback）
@app.api(
    path="/api/v1/analysis",
    method="POST",
    response_mode="sync",
    sync_timeout_seconds=30,
)
async def analysis_handler(payload: dict) -> dict:
    """Fallback: 固定分析逻辑"""
    return await legacy_analysis(payload)

# 函数调用风格（纯 Agent）
from owlclaw.triggers import api_call
app.trigger(api_call(
    path="/api/v1/smart-analysis",
    method="POST",
    event_name="smart_analysis_request",
    response_mode="async",
))
```

## HTTP 响应规范

| 状态码 | 场景 |
|--------|------|
| 200 | 同步模式成功返回结果 |
| 202 | 异步模式已接受 |
| 401 | 认证失败 |
| 408 | 同步模式超时 |
| 422 | 请求体验证失败 |
| 429 | 治理限流 |
| 503 | 治理预算耗尽 |

## 配置模型

```yaml
triggers:
  api:
    host: 0.0.0.0
    port: 8080
    auth_type: api_key        # api_key | bearer | none
    api_keys:
      - ${OWLCLAW_API_KEY}
    default_response_mode: async
    default_sync_timeout: 60
    cors_origins: ["*"]
```

## 与 Webhook 触发器的关系

| 维度 | API 触发器 | Webhook 触发器 |
|------|-----------|---------------|
| 方向 | OwlClaw 暴露端点 ← 外部调用 | 外部服务 → OwlClaw 接收回调 |
| 认证 | OwlClaw 验证调用方身份 | OwlClaw 验证回调签名 |
| 响应 | 支持同步返回 Agent 结果 | 通常只返回 200 ACK |
| 用途 | 主动查询/分析请求 | 被动接收事件通知 |

两者共享 HTTP 服务基础设施（Starlette），但路由和处理逻辑独立。

## 实施约束（禁止项）

1. 禁止在 `triggers/api` 直接调用第三方 LLM SDK，必须走 `owlclaw.integrations.llm`。
2. 禁止在 `triggers/api` 直接 import `hatchet_sdk`，必须走 `owlclaw.integrations.hatchet`。
3. 禁止绕过 `Ledger` 写自定义审计存储。
4. 任何新增持久化表必须满足：`tenant_id`、`TIMESTAMPTZ`、tenant 前缀索引、Alembic 迁移。

## 测试策略

| 层级 | 覆盖 | 工具 |
|------|------|------|
| 单元测试 | APITriggerConfig 验证、路由注册、认证逻辑 | pytest |
| 单元测试 | 同步/异步响应路由、超时处理 | pytest + asyncio |
| 集成测试 | HTTP 请求 → 认证 → 治理 → Agent trigger 全流程 | pytest + httpx (TestClient) |
| 集成测试 | 异步模式：202 → 查询结果 → 200 | pytest + httpx |
| 安全测试 | 无认证拒绝、sanitization、大 payload 防护 | pytest |
