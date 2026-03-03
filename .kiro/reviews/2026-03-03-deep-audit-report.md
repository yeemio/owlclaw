# 2026-03-03 全方位深度审计报告

> **审计范围**: 全代码库逐行审计（4 维度并行）
> **审计者**: Cursor（主 worktree）
> **发现总数**: 80+ 个问题
> **新建 Spec**: 4 个（config-propagation-fix / security-hardening / runtime-robustness / governance-hardening）

---

## 审计维度与方法

| 维度 | 审计对象 | 方法 |
|------|---------|------|
| **1. Agent Runtime 决策循环** | `runtime.py` 逐行审计 | 消息构建、工具格式、工具调用解析、异常处理、并发安全、内存集成、安全 |
| **2. App 生命周期 + 集成层** | `app.py` + `integrations/` + `web/` + `memory/` | 生命周期方法、mount/handler/configure、Hatchet/Langfuse/LangChain、CORS、WebSocket |
| **3. 触发器 + 能力系统** | `triggers/` + `capabilities/` | 6 类触发器逐个审计、registry、skills loader、bindings 执行器、knowledge injector |
| **4. 数据库 + 安全** | `db/` + `security/` + `migrations/` + `mcp/` | engine/session/models、迁移、InputSanitizer、SecurityAuditLog、认证、prompt injection |

---

## 发现汇总（按严重度）

### P0 / High（必须修复）

| # | 问题 | 位置 | Spec |
|---|------|------|------|
| 1 | SKILL.md 内容直接注入系统提示，无消毒 | `knowledge.py:174`, `runtime.py:1570` | security-hardening |
| 2 | 工具调用结果回传 LLM 无消毒（prompt injection via tool output） | `runtime.py:848` | security-hardening |
| 3 | Webhook 管理接口（POST/PUT/DELETE）无鉴权 | `webhook/http/app.py:226-306` | security-hardening |
| 4 | Webhook 请求体无大小限制（DoS 风险） | `webhook/http/app.py:123` | security-hardening |
| 5 | Webhook transformer 使用 eval（即使有 AST 白名单） | `webhook/transformer.py:210-218` | security-hardening |
| 6 | db_change 重试循环无限制（可永远重试） | `db_change/manager.py:188-204` | runtime-robustness |
| 7 | Handler 无超时机制（可无限阻塞） | `registry.py:144-154` | runtime-robustness |
| 8 | app.start() 可重复调用，不清理旧 runtime | `app.py:708-745` | runtime-robustness |
| 9 | app.start() 部分启动失败不清理 | `app.py:982-1015` | runtime-robustness |
| 10 | _tool_call_timestamps 并发不安全 | `runtime.py:1272-1278` | runtime-robustness |
| 11 | WebhookIdempotencyKeyModel 非 UUID 主键 | `webhook/persistence/models.py:74` | governance-hardening |
| 12 | MCP Server 无认证层 | `mcp/server.py` | security-hardening |
| 13 | 工具调用参数未消毒即传给 handler | `runtime.py:881` | security-hardening |
| 14 | 工具结果未消毒即回传 LLM（prompt injection） | `runtime.py:848-852` | security-hardening |

### P1 / Medium（重要缺陷）

| # | 问题 | 位置 | Spec |
|---|------|------|------|
| 15 | max_iterations 耗尽后 final_response 为空 | `runtime.py:854-856` | runtime-robustness |
| 16 | 无总 prompt context window 检查 | `runtime.py:1185-1218` | runtime-robustness |
| 17 | skills_context_cache 不含 tenant_id（跨租户泄漏） | `runtime.py:1553-1556` | runtime-robustness |
| 18 | mount_skills() 第二次调用替换 registry 但不迁移 handler | `app.py:244-273` | runtime-robustness |
| 19 | configure() 在 start() 后调用无保护 | `app.py:466-479` | config-propagation-fix |
| 20 | Hatchet connect() 无超时 | `hatchet.py:184-206` | runtime-robustness |
| 21 | Langfuse atexit 重复注册 | `langfuse.py:221` | runtime-robustness |
| 22 | LangChain adapter handler 名冲突 | `langchain/adapter.py:348-363` | runtime-robustness |
| 23 | CORS allow_credentials=True + allow_origins=["*"] | `web/api/middleware.py:75-77` | security-hardening |
| 24 | API trigger server CORS 同样问题 | `triggers/api/server.py:110-111` | security-hardening |
| 25 | WebSocket 断连后 generator 未显式关闭 | `web/api/ws.py:63-121` | runtime-robustness |
| 26 | InMemoryStore 无锁（线程不安全） | `store_inmemory.py:39` | runtime-robustness |
| 27 | InMemoryStore 从 pgvector 导入 time_decay | `store_inmemory.py:14` | runtime-robustness |
| 28 | Redis idempotency 传 dict 给 Redis set() | `idempotency.py:39-40` | runtime-robustness |
| 29 | Queue executor 每次创建新 adapter | `queue_executor.py:61-62` | runtime-robustness |
| 30 | API handler JSON 解析失败返回空 dict 而非 400 | `api/handler.py:21-32` | runtime-robustness |
| 31 | Skills loader 无文件大小限制 | `skills.py:320` | runtime-robustness |
| 32 | Token 估算使用 word split（不准确） | `knowledge.py:36-40` | runtime-robustness |
| 33 | XML 解析可能 XXE | `webhook/transformer.py:38` | security-hardening |
| 34 | Webhook create_endpoint 输入验证不足 | `webhook/http/app.py:229-253` | security-hardening |
| 35 | InputSanitizer 可被 Unicode 混淆绕过 | `security/sanitizer.py` | security-hardening |
| 36 | SecurityAuditLog 仅内存，不持久 | `security/audit.py:24-38` | security-hardening |
| 37 | Console API 无鉴权 | `web/mount.py` | security-hardening |
| 38 | Webhook auth_token 明文存储 | `webhook/persistence/models.py:27` | security-hardening |
| 39 | Ledger 索引缺 tenant_id 前缀 | `migrations/002` | governance-hardening |
| 40 | SkillQualityStore 索引缺 tenant_id | `quality_store.py:38` | governance-hardening |
| 41 | Ledger fallback 路径硬编码 | `governance/ledger.py:361` | governance-hardening |
| 42 | MODEL_PRICING 覆盖不全 | `langfuse.py:116-125` | governance-hardening |
| 43 | Session factory 每次重建 | `db/session.py:48` | governance-hardening |
| 44 | DB 连接失败原始异常泄漏 | `db/engine.py` | governance-hardening |
| 45 | DB 无 SSL/TLS 配置 | `db/engine.py:65-73` | governance-hardening |
| 46 | Cron 任务无去重（可重叠运行） | `triggers/cron.py` | governance-hardening |
| 47 | Queue 连接无重连机制 | `triggers/queue/protocols.py` | runtime-robustness |
| 48 | signal.SIGQUIT 全局覆盖 | `hatchet.py:401-403` | runtime-robustness |
| 49 | Alembic env.py 未导入 OwlHub 模型 | `migrations/env.py` | governance-hardening |
| 50 | HTTP executor 无显式 SSL 控制 | `bindings/http_executor.py:82` | runtime-robustness |
| 51 | 决策循环中无 STM/LTM 主动召回 | `runtime.py` | runtime-robustness |
| 52 | SKILL.md 可覆盖系统指令 | `runtime.py:1542-1575` | security-hardening |

### Low（改进项）

| # | 问题 | 位置 |
|---|------|------|
| 53 | tool_call_id 合成 ID 可能碰撞 | `runtime.py:847` |
| 54 | _perf_metrics 无锁 | `runtime.py:763` |
| 55 | SecurityAuditLog 不防篡改 | `security/audit.py` |
| 56 | 无效 sanitizer 规则静默跳过 | `security/sanitizer.py:60-62` |
| 57 | InMemoryStore 无大小限制 | `store_inmemory.py` |
| 58 | Hatchet disconnect 不调 SDK 清理 | `hatchet.py:206-212` |
| 59 | Langfuse sampling_rate < 1 时 trace 不完整 | `langfuse.py:265-272` |
| 60 | LangChain max_version 排除 0.3.0 | `langchain/version.py:36-39` |
| 61 | WebSocket 断连无日志 | `web/api/ws.py:152-153` |
| 62 | mount_skills 空目录无警告 | `app.py:269-273` |
| 63 | handler 注册无锁 | `app.py:323-332` |
| 64 | configure 多次调用不影响已启动组件 | `app.py:470-471` |
| 65 | 配置值无类型/范围验证 | `app.py:481-518` |
| 66 | Cron run_id 类型未校验 | `triggers/cron.py:1262` |
| 67 | Non-UTF-8 webhook body 未处理 | `webhook/http/app.py:123` |
| 68 | Idempotency lock map 无限增长 | `triggers/queue/execution.py:61-66` |
| 69 | JSON parse fallback 为 raw_payload | `db_change/adapter.py:115-121` |
| 70 | Signal 输入无长度验证 | `signal/handlers.py` |
| 71 | Capability schema additionalProperties: True | `runtime.py:1355-1357` |
| 72 | 重复 except 块 | `runtime.py:335-342` |
| 73 | Cache eviction 策略简单 | `runtime.py:1584` |
| 74 | Focus 无匹配时 skills 为空 | `runtime.py:1560-1565` |
| 75 | Path traversal 风险（skills loader） | `skills.py:269` |
| 76 | Credential resolver .env 解析简单 | `bindings/credential.py:67-78` |
| 77 | KafkaQueueAdapter 导入无错误处理 | `bindings/queue_executor.py:26-29` |
| 78 | Pool timeout 未显式映射 | `db/engine.py` |
| 79 | 无 deadlock 重试 | `db/session.py` |
| 80 | GIN index drop 参数匹配 | `migrations/003` |

---

## 与已有 Spec 的交叉引用

| 已有 Spec | 重叠项 | 处理方式 |
|-----------|--------|---------|
| lite-mode-e2e F5 | R12（pgvector 硬依赖） | 保留在 lite-mode-e2e，runtime-robustness 标注"见 lite-mode-e2e F5" |
| lite-mode-e2e F9 | CP2（model 传递） | 保留在 config-propagation-fix（更完整），lite-mode-e2e F9 标注"见 CP2" |
| lite-mode-e2e F10 | CP4（Router 返回 None） | 保留在 config-propagation-fix，lite-mode-e2e F10 标注"见 CP4" |

---

## 建议执行顺序

1. **config-propagation-fix**（P0，7 task）— 配置链路是所有功能的基础
2. **security-hardening**（P0/P1，14 task）— 安全缺陷不可延期
3. **runtime-robustness**（P1，19 task）— 稳定性直接影响用户体验
4. **governance-hardening**（P1，11 task）— 治理合规

Phase 11 lite-mode-e2e 可与 Phase 12 并行（文件边界不重叠）。
