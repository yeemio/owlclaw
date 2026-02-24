# API 调用触发器实现任务

## 文档联动

- requirements: `.kiro/specs/triggers-api/requirements.md`
- design: `.kiro/specs/triggers-api/design.md`
- tasks: `.kiro/specs/triggers-api/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


## 任务列表

### Phase 0：协议契约先行（Protocol-first，决策 4.11）

- [x] **Task 0**: 定义 API 触发器协议契约
  - [x] 0.1 提交 OpenAPI/JSON Schema：端点注册格式、请求/响应 schema、错误码表（400/401/429/503/408）
  - [x] 0.2 确认同步/异步两种响应模式的协议语义（202 + run_id vs 直接结果）
  - [x] 0.3 协议层不泄漏 Python 特有语义（无 Callable/装饰器元数据）
  - _说明：Task 1 的 Python 实现必须从本契约派生，禁止跳过契约直接做 Python API_

### Phase 1：HTTP 服务与端点注册

- [x] **Task 1**: 创建 `owlclaw/triggers/api/` 模块结构
  - 创建 `__init__.py`, `server.py`, `auth.py`, `config.py`, `handler.py`
  - 定义 `APITriggerConfig` Pydantic 模型
  - 添加 starlette + uvicorn 到可选依赖

- [x] **Task 2**: 实现 `APITriggerServer`
  - Starlette 应用初始化 + 路由管理
  - `register()` 动态注册端点
  - uvicorn 启动/停止生命周期
  - CORS 中间件配置

- [x] **Task 3**: 实现 `AuthProvider` 认证体系
  - `APIKeyAuthProvider`: X-API-Key header 验证
  - `BearerTokenAuthProvider`: Authorization Bearer 验证
  - 认证失败 → 401 JSON 响应
  - 认证类型通过配置切换

- [x] **Task 4**: 实现请求处理管道
  - 请求体解析（JSON body / query params / path params）
  - InputSanitizer 集成（security spec）
  - GovernanceGate 集成（rate limit → 429, budget → 503）
  - Ledger 记录（请求来源、认证身份、处理结果）

- [x] **Task 5**: 实现同步/异步响应模式
  - 同步模式：await Agent Run result + 超时控制（408）
  - 异步模式：返回 202 + run_id + Location header
  - 内建 `/runs/{run_id}/result` 查询端点
  - 配置默认模式 + 每端点覆盖

- [x] **Task 6**: 实现装饰器 + 函数调用 API
  - `@app.api()` 装饰器（fallback handler 绑定）
  - `app.trigger(api_call(...))` 函数调用风格
  - 与 APITriggerServer 注册集成

### Phase 2：测试与安全

- [ ] **Task 7**: 单元测试
  - APITriggerConfig 验证
  - AuthProvider 各实现
  - 同步/异步响应路由逻辑
  - 超时处理
  - 目标覆盖率：> 90%

- [ ] **Task 8**: 集成测试
  - httpx TestClient 测试 HTTP 端点
  - 认证成功/失败流程
  - 治理阻断流程（429/503）
  - 同步模式端到端：请求 → Agent Run → 响应
  - 异步模式端到端：请求 → 202 → 查询结果

- [ ] **Task 9**: 安全测试
  - 无认证请求拒绝
  - Sanitization 注入防护
  - 大 payload 防护（body size limit）
  - 并发请求压力测试

### Phase 3：文档

- [ ] **Task 10**: 文档
  - API 端点注册指南
  - 认证配置指南
  - 同步 vs 异步模式选择指南
  - OpenAPI schema 自动生成（可选）
