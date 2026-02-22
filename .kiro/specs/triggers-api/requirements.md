# Requirements: API 调用触发器

> **目标**：通过 HTTP REST 端点接收外部系统请求，触发 Agent Run 并返回智能响应  
> **优先级**：P2  
> **预估工作量**：4-6 天

---

## 1. 背景与动机

### 1.1 当前问题

架构文档 §5.3.1 定义了六类触发入口，其中「API 调用」是业务应用的同步交互入口。与 Webhook 的被动回调不同，API 触发器主动暴露端点供外部系统调用，让 Agent 智能响应请求而非执行固定的 request-response 逻辑。

### 1.2 设计目标

- 暴露 REST API 端点，外部系统通过 HTTP 请求触发 Agent Run
- 支持同步（等待 Agent 决策结果）和异步（立即返回 run_id）两种模式
- 与治理层集成，自动应用限流和预算约束
- 安全层集成，外部请求体经过 sanitization

---

## 2. 用户故事

### 2.1 作为业务开发者

**故事 1**：注册 API 触发器
```
作为业务开发者
我希望通过 @app.api 装饰器暴露一个 REST 端点
这样外部系统可以请求 Agent 智能分析并返回结果
```

**验收标准**：
- [ ] `@app.api(path="/api/v1/analysis", method="POST")` 注册 API 端点
- [ ] 请求 body 作为触发上下文传递给 Agent
- [ ] 支持 sync/async 响应模式

---

## 3. 功能需求

#### FR-1：API 端点注册

**需求**：通过装饰器注册 REST API 端点，由内置 HTTP 服务器（如 uvicorn + starlette）暴露。

**验收标准**：
- [ ] 支持 POST / GET 方法
- [ ] 支持路径参数和查询参数
- [ ] 端点自动注册到 Agent 的触发器列表

#### FR-2：请求认证

**需求**：支持 API Key 和 Bearer Token 认证。

**验收标准**：
- [ ] 无认证的请求返回 401
- [ ] 认证方式通过配置指定

#### FR-3：同步/异步响应

**需求**：支持两种响应模式。

**验收标准**：
- [ ] 同步模式：等待 Agent Run 完成，返回结果（含超时控制）
- [ ] 异步模式：立即返回 202 + run_id，调用方后续查询结果
- [ ] 默认模式通过端点配置指定

#### FR-4：治理集成

**需求**：API 请求经过治理层的限流和预算检查。

**验收标准**：
- [ ] 超过限流返回 429 Too Many Requests
- [ ] 超过预算返回 503 Service Unavailable
- [ ] 执行记录写入 Ledger

---

## 4. 依赖

- `owlclaw.agent.runtime`：Agent Run 触发
- `owlclaw.governance`：限流、预算、Ledger
- `owlclaw.security`：输入 sanitization
- starlette / uvicorn（可选，轻量 HTTP 框架）

---

## 5. 参考文档

- [OwlClaw 架构分析](../../docs/ARCHITECTURE_ANALYSIS.md) §5.3.1 六类触发入口
- [Triggers Webhook Spec](../triggers-webhook/)
- [Security Spec](../security/)

---

**维护者**：OwlClaw Team  
**最后更新**：2026-02-22
