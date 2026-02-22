# API 调用触发器设计文档

## 概述

API 触发器通过内置轻量 HTTP 服务暴露 REST 端点，外部系统通过 HTTP 请求触发 Agent Run。支持同步（等待 Agent 决策结果）和异步（立即返回 run_id）两种响应模式。

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
    fallback: Callable | None = None    # 装饰器风格的 fallback handler
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
                body = self.sanitizer.sanitize(body)

            # 3. 治理检查
            if not await self.governance.check(config.event_name):
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
        run_id = await self.agent_runner.trigger(
            event_name=config.event_name,
            trigger_type="api_call",
            payload=body,
            focus=config.focus,
        )
        try:
            result = await asyncio.wait_for(
                self.agent_runner.wait_for_result(run_id),
                timeout=config.sync_timeout_seconds,
            )
            return JSONResponse({"run_id": str(run_id), "result": result})
        except asyncio.TimeoutError:
            return JSONResponse(
                {"run_id": str(run_id), "status": "timeout"},
                status_code=408,
            )

    async def _handle_async(self, config, body, request):
        """异步模式：立即返回 run_id"""
        run_id = await self.agent_runner.trigger(
            event_name=config.event_name,
            trigger_type="api_call",
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

## 测试策略

| 层级 | 覆盖 | 工具 |
|------|------|------|
| 单元测试 | APITriggerConfig 验证、路由注册、认证逻辑 | pytest |
| 单元测试 | 同步/异步响应路由、超时处理 | pytest + asyncio |
| 集成测试 | HTTP 请求 → 认证 → 治理 → Agent trigger 全流程 | pytest + httpx (TestClient) |
| 集成测试 | 异步模式：202 → 查询结果 → 200 | pytest + httpx |
| 安全测试 | 无认证拒绝、sanitization、大 payload 防护 | pytest |
