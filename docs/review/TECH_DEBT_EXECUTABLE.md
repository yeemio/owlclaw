# 技术债清单（可执行版）

> 原则：每项必须可直接开工，包含文件、改法、风险、预计工时。  
> 状态：2026-03-09 收尾盘点。

| 优先级 | 文件 | 改法（可执行） | 不做风险 | 预计工时 | 状态 |
|---|---|---|---|---|
| High | `owlclaw/triggers/webhook/http/app.py` | `/events` 返回结构统一做 datetime 安全序列化（避免直接 `asdict` 输出 datetime）并补 API 回归测 | 当前已鉴权，但该接口仍可能在有数据时触发 500，影响审计查询可用性 | 1.5h | 已完成 |
| High | `owlclaw/agent/tools.py` | 对 memory 相关 await 路径统一加真实 timeout（`asyncio.wait_for`）并清理“伪超时保护” | 高延迟依赖可能拖垮事件循环，线上表现为请求堆积 | 3h | 已完成（remember/recall） |
| High | `owlclaw/integrations/llm.py` + `owlclaw/agent/memory/embedder_litellm.py` | 为 `acompletion/aembedding` 显式注入 timeout 参数，补 provider timeout 测试 | 上游抖动时无硬超时边界，可能造成级联超时 | 3h | 已完成 |
| Medium | `owlclaw/owlhub/review/system.py` | 对 `review_id` 做路径片段白名单校验（仅 `[a-zA-Z0-9._-]`），统一 reject 非法片段 | 本地评审记录存在路径穿越风险 | 2h | 已完成 |
| Medium | `owlclaw/web/api/ws.py` | 对齐 REST/WS token 来源（支持 `OWLCLAW_CONSOLE_API_TOKEN` 一致策略）并补兼容测试 | 运维配置不一致时 WS 鉴权行为不可预期 | 1.5h | 已完成 |
| Medium | `owlclaw/triggers/webhook/execution.py` | 为 `_idempotency`/`_executions` 增加容量上限和淘汰策略，并补压力测试 | 长时间运行后内存增长不可控 | 2.5h | 已完成 |
| Medium | `owlclaw/owlhub/api/auth.py` | sessions/api_keys/rate_bucket 增加 TTL + max size，并提供周期清理 | 管理面请求高峰会导致内存持续膨胀 | 3h | 已完成 |
| Medium | `owlclaw/cli/db_backup.py` | 避免把完整 DB URL 直接传给进程参数，改为环境变量注入凭据 | 进程列表可能泄露数据库密码 | 2h | 已完成 |

## 执行建议

1. 当前表内技术债已全部落地，建议进入“全量回归 + 发布门禁验证”。  
2. 后续新增技术债继续按本模板维护（文件 + 改法 + 风险 + 工时 + 状态）。  
3. 每项必须绑定至少 1 个回归测试，避免“修一次、回归一次”。
