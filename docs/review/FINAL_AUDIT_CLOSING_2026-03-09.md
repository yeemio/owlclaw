# 深度审计最终收口清单（2026-03-09）

> 范围：按 critical/high/medium 汇总“当前仍需处理项”，并标注本轮已落地修复。  
> 审计结论：仍不建议直接发布，需先完成 critical/high 剩余项。

## 本轮已修复（可直接验收）

1. `webhook` 请求体改为流式限长读取，堵住内存 DoS 路径。  
   - 文件：`owlclaw/triggers/webhook/http/app.py`
2. `webhook /events` 加管理鉴权；请求日志敏感头默认脱敏。  
   - 文件：`owlclaw/triggers/webhook/http/app.py`
3. `OwlHub` 安装流程增加 tar 安全解包，拦截路径穿越与链接成员。  
   - 文件：`owlclaw/owlhub/client.py`
4. `webhook /events` 查询结果序列化改为安全编码，避免 datetime 直接 JSON 失败。  
   - 文件：`owlclaw/triggers/webhook/http/app.py`
5. WebSocket 鉴权策略对齐 REST：支持 `OWLCLAW_CONSOLE_API_TOKEN`（兼容 legacy token）。  
   - 文件：`owlclaw/web/api/ws.py`
6. `remember/recall` memory 调用改为真实超时控制（`asyncio.wait_for`）。  
   - 文件：`owlclaw/agent/tools.py`
7. `db backup` 连接串去密码，凭据仅通过 `PGPASSWORD` 注入。  
   - 文件：`owlclaw/cli/db_backup.py`
8. `review_id` 文件路径增加严格白名单与路径边界检查。  
   - 文件：`owlclaw/owlhub/review/system.py`
9. `webhook execution` 的 idempotency/execution 缓存增加容量上限与淘汰策略。  
   - 文件：`owlclaw/triggers/webhook/execution.py`
10. LLM facade 与 embedder 增加默认超时透传，避免无边界上游等待。  
   - 文件：`owlclaw/integrations/llm.py`, `owlclaw/agent/memory/embedder_litellm.py`
11. OwlHub 认证状态改为有界内存结构（sessions/api_keys/rate_bucket 上限 + 清理）。  
   - 文件：`owlclaw/owlhub/api/auth.py`

对应回归测试：
- `tests/unit/triggers/test_webhook_http_gateway.py::test_webhook_request_body_too_large_returns_413`
- `tests/unit/triggers/test_webhook_http_gateway.py::test_events_endpoint_requires_admin_token_and_redacts_sensitive_headers`
- `tests/unit/test_owlhub_cli_client.py::test_install_rejects_tar_path_traversal_member`
- `tests/unit/web/test_ws.py::test_ws_accepts_console_api_token_env`
- `tests/unit/agent/test_tools.py::TestMemoryTools::test_remember_timeout_returns_error`
- `tests/unit/agent/test_tools.py::TestMemoryTools::test_recall_timeout_returns_error`
- `tests/unit/test_cli_db_backup.py::test_backup_command_success`
- `tests/unit/test_owlhub_review_system.py::test_review_system_rejects_path_traversal_review_id`
- `tests/unit/triggers/test_webhook_execution.py::test_execution_trigger_limits_execution_cache_size`
- `tests/unit/triggers/test_webhook_execution.py::test_execution_trigger_limits_idempotency_cache_size`
- `tests/unit/integrations/test_llm.py::test_acompletion_sets_default_timeout`
- `tests/unit/integrations/test_llm.py::test_aembedding_respects_explicit_timeout_override`
- `tests/unit/agent/memory/test_litellm_embedder_validation.py::test_embedder_rejects_non_positive_timeout`
- `tests/unit/test_owlhub_api_auth.py::test_auth_manager_limits_sessions_api_keys_and_rate_buckets`

---

## Critical（阻断发布）

- 当前批次无未收口 Critical。建议进入全量回归后再给最终可发布 verdict。

## High（本周应完成）

1. 仍建议补一次跨模块全量回归，确认组合行为无回归（非代码缺陷项）。

## 回归门禁快照

- 核心回归矩阵已通过：`116 passed`。  
- 先前 `Connection._cancel was never awaited` 告警已收口：`test_middleware` 改为轻量 stub provider，规避无关 DB 连接生命周期副作用。  
- 当前仅剩 2 条三方库 deprecation warning（`httpx` 上传 `data=` 提示），不影响功能正确性。

## Medium（纳入下一迭代）

1. 租户来源仍可退化到 header 信任路径（需强绑定认证上下文）。  
   - 文件：`owlclaw/web/api/deps.py`
2. 部分错误信息脱敏不一致。  
   - 文件：`owlclaw/triggers/webhook/governance.py`, `owlclaw/cli/db_restore.py`
3. 运行与运维文档需对齐最新安全策略。  
   - 文件：`docs/ops/INCIDENT_RUNBOOK_V1.md`, `docs/review/CORE_REGRESSION_MATRIX.md`

---

## 下一批执行建议（高价值收尾）

1. 先完成 Critical 剩余项（LLM/embedder timeout 统一）并补回归。  
2. 再清 High 剩余项（`owlhub/api/auth.py` 有界化），形成发布前安全基线。  
3. 最后统一 spec checkpoint 与本清单状态，避免文档漂移。
