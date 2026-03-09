# OwlClaw 深度审计收口清单（2026-03-09）

> 范围：全仓历史深度审计结果收口（Critical/High/Medium），并合并 2026-03-09 当日新增复核结论  
> 说明：本清单用于发布前“一页看风险”；详细证据以 `docs/review/DEEP_AUDIT_REPORT.md` 和对应 spec 为准。

---

## 1) Critical（P0）

- **当前状态：无未收口 P0**
- 历史 P0（已收口）：
  - CircuitBreaker 状态匹配错误（已在 `audit-fix-critical` 完成）
  - Console API 挂载路径错误（已在 `audit-fix-critical` 完成）
  - OwlHub 权限提升与默认密钥类问题（已进入 `security-hardening` 与后续加固）

## 2) High（P1）

### 2.1 当日完成修复（已补测试）

1. **API async run result 未鉴权**
   - 变更：`owlclaw/triggers/api/server.py`
   - 修复：`/runs/{run_id}/result` 按 run 元数据执行鉴权，并校验 identity 绑定
   - 测试：`tests/unit/triggers/test_api.py`、`tests/integration/test_api_trigger_integration.py`

2. **API async 后台任务未纳管**
   - 变更：`owlclaw/triggers/api/server.py`
   - 修复：新增后台任务集合管理，`stop()` 统一 cancel + gather；任务取消状态可见
   - 测试：复用 API 触发器单测回归

3. **Queue 治理故障默认 fail-open**
   - 变更：`owlclaw/triggers/queue/trigger.py`、`owlclaw/triggers/queue/config.py`
   - 修复：默认 fail-close；增加 `governance_fail_open` 显式开关（默认 `false`）
   - 测试：`tests/unit/triggers/test_queue_trigger.py` 新增 fail-open 配置化回归

4. **Signal Admin tenant 绑定缺失**
   - 变更：`owlclaw/triggers/signal/api.py`
   - 修复：鉴权开启时强制 `x-owlclaw-tenant` 绑定并与请求体 tenant 一致，否则 403
   - 测试：`tests/unit/triggers/test_api.py` 新增 tenant binding 正反用例

5. **db_change 重试耗尽路径错误文本与 payload 泄露**
   - 变更：`owlclaw/triggers/db_change/manager.py`
   - 修复：DLQ 与 warning 日志统一脱敏（token/password/bearer/URL 凭据）
   - 测试：`tests/unit/triggers/test_db_change.py` 新增敏感信息脱敏回归

6. **Queue tenant 来源信任边界薄弱（头部直透）**
   - 变更：`owlclaw/triggers/queue/config.py`、`owlclaw/triggers/queue/trigger.py`
   - 修复：新增 `trust_tenant_header`（默认 `false`）+ `default_tenant_id`；默认不信任消息头 tenant，仅显式开启时透传
   - 测试：`test_queue_trigger.py` / `test_queue_trigger_properties.py` / `test_queue_trigger_e2e.py`

7. **Queue tenant 缺少来源真实性校验**
   - 变更：`owlclaw/triggers/queue/config.py`、`owlclaw/triggers/queue/trigger.py`
   - 修复：新增可选 HMAC 签名校验（`tenant_signature_secret_env` + `tenant_signature_header`），并支持 `tenant_signature_secret_envs` 多密钥轮换窗口，在 `trust_tenant_header=true` 场景进一步约束 tenant 注入
   - 测试：`test_queue_trigger.py`（签名正负路径）+ `test_queue_config*.py`

### 2.2 待继续收口（未在本轮改代码）

1. **Queue tenant 签名密钥治理未完全制度化（分发/轮换周期/泄露演练）**
   - 已完成：代码侧多密钥过渡能力（`tenant_signature_secret_envs`）
   - 未完成：组织级轮换周期与演练制度
   - 建议优先级：P1-Next（运维治理增强）

## 3) Medium / Low

- 重点集中在：
  - 脱敏规则覆盖面（Basic/Auth URL/连接串）
  - 状态语义一致性（error/failed/blocked）
  - 负向测试覆盖不足（越权、异常、并发竞态）
- 当日新增收口：
  - API run 查询结果补 `query_audit`（identity/tenant/query_count），降低异步链路排障成本
- 建议以“回归矩阵 + 失败注入测试”批量收口，不做分散点修。

---

## 4) 本轮验证结果

- 命令：
  - `poetry run pytest tests/unit/triggers/test_api.py tests/integration/test_api_trigger_integration.py tests/unit/triggers/test_queue_trigger.py -q`
  - `poetry run pytest tests/unit/triggers/test_api.py tests/unit/triggers/test_db_change.py -q`
  - `poetry run pytest tests/unit/triggers/test_queue_trigger.py tests/unit/triggers/test_queue_trigger_properties.py tests/integration/test_queue_trigger_e2e.py tests/unit/triggers/test_queue_config.py tests/unit/triggers/test_queue_config_properties.py -q`
  - `poetry run pytest tests/unit/triggers/test_api.py tests/unit/triggers/test_db_change.py tests/unit/triggers/test_queue_trigger.py tests/unit/triggers/test_queue_trigger_properties.py tests/integration/test_api_trigger_integration.py tests/integration/test_queue_trigger_e2e.py -q`
  - `pwsh ./scripts/regression-core.ps1 -IncludeIntegration:$false`
  - `poetry run pytest tests/unit/triggers/test_queue_trigger.py tests/unit/triggers/test_queue_config.py tests/unit/triggers/test_queue_config_properties.py -q`
  - `poetry run pytest tests/unit/triggers/test_queue_config.py tests/unit/triggers/test_queue_config_properties.py tests/unit/triggers/test_queue_trigger.py -q`
- 结果：
  - `43 passed`
  - `34 passed`
  - `36 passed`
  - `43 passed, 1 skipped`
  - `70 passed, 1 skipped`
  - `99 passed, 1 warning`
  - `34 passed`

---

## 5) 发布门禁建议

- 必须满足：
  - `Critical = 0`
  - `High` 中“跨租户控制面 / 凭据泄露 / 未鉴权查询面”全部关闭
  - 回归矩阵全绿（见 `docs/review/CORE_REGRESSION_MATRIX.md`）
- 当前结论：
  - **可进入“带条件发布”阶段**，但仍需继续清理剩余 P1。

