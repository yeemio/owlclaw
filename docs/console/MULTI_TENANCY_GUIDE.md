# Console 多租户与 tenant_id 指南

> **创建时间**: 2026-03-06
> **状态**: 已完成 (audit-deep-remediation D2/P1-2)
> **关联**: `.kiro/specs/audit-deep-remediation/tasks.md` Task 5

---

## 1. 当前行为

### 1.1 tenant_id 来源

当前 Console API 的 `tenant_id` 从 HTTP 请求头 `X-OwlClaw-Tenant` 读取：

```python
# owlclaw/web/api/deps.py
async def get_tenant_id(x_owlclaw_tenant: str | None = Header(default=None)) -> str:
    """Extract tenant id from request header with default fallback."""
    if x_owlclaw_tenant is None or not x_owlclaw_tenant.strip():
        return "default"
    return x_owlclaw_tenant.strip()
```

**关键行为**：
- 如果请求头缺失或为空，返回 `"default"` 作为默认租户 ID
- 不强制要求认证推导 tenant_id
- 适用于单租户部署或开发环境

### 1.2 可选依赖处理

Console 后端设计为**优雅降级**，当数据库未配置时：

| API 端点 | 无 DB 行为 | 实现位置 |
|---------|----------|---------|
| `GET /capabilities` | 返回空 stats（零统计） | `web/providers/capabilities.py` |
| `GET /ledger/...` | 返回空列表 | `web/providers/ledger.py` |
| `GET /overview` | 返回基础健康状态（无 DB 指标） | `web/providers/overview.py` |
| `GET /agents/{id}` | 返回空统计 | `web/providers/agents.py` |
| `GET /triggers` | 返回已注册触发器（无执行历史） | `web/providers/triggers.py` |

**实现示例**：

```python
# web/providers/capabilities.py
async def _collect_capability_stats(self, tenant_id: str) -> dict[str, dict[str, Any]]:
    try:
        engine = get_engine()
        session_factory = create_session_factory(engine)
    except ConfigurationError:
        # Database not configured - return empty stats for graceful degradation
        logger.debug("Database not configured, returning empty capability stats")
        return {}
    # ... 正常查询逻辑
```

---

## 2. 适用场景

### 2.1 单租户部署（默认）

**场景**：内部工具、个人使用、小团队

- 使用默认 `tenant_id = "default"`
- 无需配置认证头
- 所有数据共享同一租户空间

### 2.2 多租户部署

**场景**：SaaS、企业客户、多团队隔离

**配置方式**：

1. **客户端请求头**：
   ```
   X-OwlClaw-Tenant: tenant-123
   ```

2. **从认证推导 tenant_id（推荐）**：

   生产环境应从认证 token 中提取 tenant_id，而不是依赖客户端提供的头：

   ```python
   # 示例：从 JWT token 推导 tenant_id
   async def get_tenant_id_from_token(
       token: str = Depends(oauth2_scheme)
   ) -> str:
       """Extract tenant_id from authenticated token claims."""
       payload = decode_jwt(token)
       tenant_id = payload.get("tenant_id")
       if not tenant_id:
           raise HTTPException(status_code=403, detail="tenant_id missing in token")
       return tenant_id
   ```

3. **数据库隔离**：
   - LedgerRecord 索引包含 `tenant_id` 前缀
   - 所有查询必须过滤 `tenant_id`
   - 参考：`docs/DATABASE_ARCHITECTURE.md` §1.1 铁律

---

## 3. 安全考虑

### 3.1 当前风险

**租户隔离依赖客户端输入**：
- 当前实现允许客户端任意指定 `X-OwlClaw-Tenant` 头
- 恶意用户可访问其他租户数据

### 3.2 推荐措施

**生产环境必须**：

1. **从认证推导 tenant_id**：
   - 不要信任客户端提供的 tenant_id
   - 从 JWT/OAuth token 解析租户身份

2. **添加中间件验证**：
   ```python
   # 示例中间件
   class TenantIsolationMiddleware(BaseHTTPMiddleware):
       async def dispatch(self, request, call_next):
           token = request.headers.get("Authorization")
           tenant_from_token = extract_tenant_from_token(token)
           tenant_from_header = request.headers.get("X-OwlClaw-Tenant")

           # 防止租户跨越：header 必须与 token 一致
           if tenant_from_header and tenant_from_header != tenant_from_token:
               return JSONResponse(status_code=403, content={"error": "tenant mismatch"})

           request.state.tenant_id = tenant_from_token
           return await call_next(request)
   ```

3. **数据库行级安全**：
   - 所有查询必须包含 `WHERE tenant_id = :tenant_id`
   - 参考 LedgerRecord 索引：`idx_ledger_tenant_*`

---

## 4. 配置示例

### 4.1 开发环境（无 DB）

```bash
# .env
OWLCLAW_CONSOLE_API_TOKEN=dev-token
OWLCLAW_REQUIRE_AUTH=false
# 不设置 OWLCLAW_DATABASE_URL
```

启动后访问 `GET /capabilities` 返回：
```json
{
  "items": [
    {
      "name": "my-handler",
      "category": "handler",
      "stats": {
        "executions": 0,
        "success_rate": 0.0,
        "avg_latency_ms": 0.0
      }
    }
  ]
}
```

### 4.2 生产环境（多租户）

```bash
# .env
OWLCLAW_CONSOLE_API_TOKEN=prod-secure-token
OWLCLAW_REQUIRE_AUTH=true
OWLCLAW_DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/owlclaw
OWLCLAW_CONSOLE_CORS_ORIGINS=https://console.example.com
```

客户端请求：
```http
GET /api/v1/ledger/records
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
X-OwlClaw-Tenant: tenant-123
```

---

## 5. 待决事项

### 5.1 认证中间件增强

当前 `TokenAuthMiddleware` 仅支持单 token 验证，不支持：
- JWT/OAuth token 解析
- tenant_id 从 token 提取
- 多租户 token 管理

**追踪**：`.kiro/specs/console-backend-api/tasks.md` 后续版本

### 5.2 租户管理 UI

Console 前端未提供：
- 租户切换器
- 租户管理页面
- 跨租户数据隔离验证

---

## 6. 关联文档

- `docs/DATABASE_ARCHITECTURE.md` - 数据库架构（tenant_id 铁律）
- `docs/ARCHITECTURE_ANALYSIS.md` - 总架构文档 §8.5 安全模型
- `owlclaw/web/api/middleware.py` - Token 认证中间件实现
- `owlclaw/web/api/deps.py` - tenant_id 依赖注入

---

**维护者**: yeemio
**下次审核**: 2026-04-01
