# 技术债清单（可执行版）

> 原则：每条必须包含“文件 + 改法 + 风险 + 预计工时”，避免泛化建议。  
> 估时口径：单人有效编码时间（不含评审排队）。

---

## P1（优先处理）

| # | 文件 | 改法（可执行） | 不改风险 | 预计工时 |
|---|---|---|---|---|
| 1 | `docs/ops/INCIDENT_RUNBOOK_V1.md` + ops 策略 | 固化 tenant 签名密钥治理制度（轮换周期、分发流程、泄露应急演练）；代码侧多密钥过渡已完成 | 若仅有代码能力无制度，轮换执行仍易遗漏 | 3h |
| 2 | `owlclaw/triggers/api/server.py` | 为 `_runs` 增加 TTL 清理任务与容量指标；完善 cancelled/failed 可观测字段 | 运行期状态缓存膨胀与诊断盲区 | 3h |

## Medium（批量处理）

| # | 文件 | 改法（可执行） | 不改风险 | 预计工时 |
|---|---|---|---|---|
| 5 | `owlclaw/triggers/queue/security.py` | 补 Basic/Auth URL/DSN 脱敏 regex；加属性测试 | 日志残留凭据片段 | 2.5h |
| 6 | `owlclaw/web/providers/governance.py` | 状态枚举统一（failure/error/timeout/failed）+ schema 常量化 | Console 状态误判 | 3h |

---

## 建议执行顺序

1. #1（租户隔离）
2. #2（稳定性与可运维）
3. #5~#7（一致性与可观测）

---

## 当日已完成（2026-03-09）

- `owlclaw/triggers/signal/api.py`：tenant 绑定校验 + 回归测试
- `owlclaw/triggers/db_change/manager.py`：DLQ/日志脱敏 + 回归测试
- `owlclaw/triggers/queue/config.py` + `trigger.py`：tenant header 默认不信任 + 显式开关 + 回归测试
- `owlclaw/triggers/queue/config.py` + `trigger.py`：producer allowlist + 可选 tenant HMAC 签名校验 + 回归测试
- `owlclaw/triggers/queue/config.py` + `trigger.py`：`tenant_signature_secret_envs` 多密钥轮换窗口支持 + 回归测试
- `owlclaw/triggers/api/server.py` + `tests/unit/triggers/test_api.py`：run 查询 API 输出 `query_audit`（identity/tenant/count）+ 回归测试

