# 深度审计执行清单（统筹分配版）

> **来源**: [DEEP_AUDIT_REPORT.md](/D:/AI/owlclaw/docs/review/DEEP_AUDIT_REPORT.md)
> **对应 spec**: [audit-deep-remediation/tasks.md](/D:/AI/owlclaw/.kiro/specs/audit-deep-remediation/tasks.md)
> **用途**: 供“统筹”在下一轮直接分配给 `codex-work` / `codex-gpt-work` / `review-work`
> **最后更新**: 2026-03-06

---

## 1. 分配原则

- `P1` 先于 `Low`
- 先做解除依赖的任务，再做依赖其结果的任务
- `codex-work` 负责 `runtime.py` / `ledger.py` / `app.py`
- `codex-gpt-work` 负责 `docs/` / `heartbeat.py` / `engine.py` / `capabilities.py` / `webhook`
- `review-work` 不做功能实现，只做审校、轻量修正、合并把关

---

## 2. 当前可直接分配批次

### Batch A：历史批次（其中 codex-work 主体已完成并合入 `main`）

**codex-work**

| ID | Finding | 文件 | 目标 | 验收 |
|---|---|---|---|---|
| D1 | P1-1 | `owlclaw/agent/runtime/runtime.py` | Skill env 仅允许 `OWLCLAW_SKILL_` 前缀 | 非前缀 key 不注入；有测试 |
| D3 | Low-3 | `owlclaw/agent/runtime/runtime.py` | 两处 runtime cache 改为 LRU | 满容量时逐出最近最少使用项；测试通过 |
| D5 | Low-5 | `owlclaw/agent/runtime/runtime.py` | LLM 异常不再把 `str(exc)` 放入会话 | grep 与测试确认 |
| D4a | Low-4a | `owlclaw/governance/ledger.py` | Ledger 暴露 `get_readonly_session_factory()` | Heartbeat 后续可改用公开 API |
| D8 | Low-8 | `owlclaw/app.py` | `health_status()` 不读 `_states` / `_configs` | 无私有属性访问或有公开只读属性 |
| D9 | Low-9 | `owlclaw/governance/ledger.py` | `_background_writer` 异常时写 fallback | batch 不丢；有异常路径验证 |
| D10 | Low-10 | `owlclaw/governance/ledger.py` | `_write_queue` 有界或背压 | 队列上限明确；行为可验证 |
| D12 | Low-12 | `owlclaw/web/api/middleware.py` | token 校验改为常量时间比较 | 已转入 Batch B 继续执行 |

**codex-gpt-work**

| ID | Finding | 文件 | 目标 | 验收 |
|---|---|---|---|---|
| D2 | P1-2 | `docs/` | 明确 tenant_id 当前行为与多租户边界 | 已转入 Batch B 待 review-work 审校 |
| D6 | Low-6 | `owlclaw/db/engine.py` | 收窄异常映射 | 已转入 Batch B 待 review-work 审校 |
| D7 | Low-7 | `owlclaw/web/providers/capabilities.py` | 无 DB 时 `/capabilities` 不 500 | 已转入 Batch B 待 review-work 审校 |
| D11 | Low-11 | `owlclaw/triggers/webhook/http/app.py` | 非 UTF-8 body 返回 400 | 已转入 Batch B 待 review-work 审校 |
| D13 | Low-13 | `owlclaw/governance/visibility.py` | evaluator 增加 timeout 或文档边界 | 仍待实现 |
| D14 | Low-14 | `owlclaw/integrations/hatchet.py` | 收敛 Windows SIGQUIT 兼容逻辑作用域 | 仍待实现 |

### Batch B：当前待执行

**codex-gpt-work**

| ID | Finding | 文件 | 前置 | 目标 | 验收 |
|---|---|---|---|---|---|
| D4b | Low-4b | `owlclaw/agent/runtime/heartbeat.py` | D4a 已合入 `main`，可直接启动 | Heartbeat 改走 Ledger 公开 API | grep 无 `_session_factory`；测试通过 |

**codex-work**

| ID | Finding | 文件 | 目标 | 验收 |
|---|---|---|---|---|
| D12 | Low-12 | `owlclaw/web/api/middleware.py` | Console API token 校验改为常量时间比较 | 使用 `hmac.compare_digest`；有测试或手验 |
| D15 | Low-15 | `owlclaw/capabilities/bindings/http_executor.py` | 明确或收紧空 `allowed_hosts` 的 SSRF 边界 | 有测试、配置校验或文档说明 |
| D16 | Low-16 | `owlclaw/capabilities/bindings/tool.py` | BindingTool ledger 错误信息脱敏 | 不再写原始 `str(exc)`；有测试 |
| D21 | Low-21 | `owlclaw/capabilities/registry.py` | CapabilityRegistry 异常包装脱敏 | 调用方不再收到原始异常字符串 |

**codex-gpt-work**

| ID | Finding | 文件 | 前置 | 目标 | 验收 |
|---|---|---|---|---|---|
| D2 | P1-2 | `docs/` | 无 | 明确 tenant_id 当前行为与多租户边界 | 文档写清“仅自托管/非安全标签可接受” |
| D4b | Low-4b | `owlclaw/agent/runtime/heartbeat.py` | D4a 已合入 `main` | Heartbeat 改走 Ledger 公开 API | grep 无 `_session_factory`；测试通过 |
| D6 | Low-6 | `owlclaw/db/engine.py` | 无 | 收窄异常映射 | 非连接类异常不再误报 |
| D7 | Low-7 | `owlclaw/web/providers/capabilities.py` | 无 | 无 DB 时 `/capabilities` 不 500 | 返回 200 + 零统计 |
| D11 | Low-11 | `owlclaw/triggers/webhook/http/app.py` | 无 | 非 UTF-8 body 返回 400 | 有测试或手验 |
| D13 | Low-13 | `owlclaw/governance/visibility.py` | 无 | evaluator 增加 timeout 或文档边界 | 单个 evaluator 不再无限卡住过滤 |
| D14 | Low-14 | `owlclaw/integrations/hatchet.py` | 无 | 收敛 Windows SIGQUIT 兼容逻辑作用域 | 兼容逻辑边界清晰 |
| D17 | Low-17 | `owlclaw/triggers/api/server.py` | 无 | body 大小在读取时强制限制 | 超限请求在伪造 header 时仍被拒绝 |
| D18 | Low-18 | `owlclaw/triggers/api/server.py` | 无 | API trigger ledger 错误信息脱敏 | 不再写原始 `str(exc)`；有测试 |
| D19 | Low-19 | `owlclaw/triggers/api/auth.py` | 无 | API trigger auth 常量时间比较 | 使用 `hmac.compare_digest`；有测试或手验 |
| D20 | Low-20 | `owlclaw/triggers/cron.py` | D18 优先 | Cron 历史接口避免暴露未脱敏 ledger 错误 | 输出 redacted 或由上游统一脱敏 |

---

## 3. 统筹下发模板

### 给 codex-work

- 批次：`audit-deep-remediation / Batch B`
- 任务：`D12 D15 D16 D21`
- 文件边界：
  - 可改：`owlclaw/web/api/middleware.py`
  - 可改：`owlclaw/capabilities/bindings/http_executor.py`
  - 可改：`owlclaw/capabilities/bindings/tool.py`
  - 可改：`owlclaw/capabilities/registry.py`
  - 禁止改：`heartbeat.py` `engine.py` `capabilities.py` `webhook http/app.py` `docs/` `triggers/api/`
- 审校移交条件：
  - 至少包含对应测试
  - `tasks.md` 勾选完成项
  - commit message 标注 `audit-deep-remediation`

### 给 codex-gpt-work

- 批次：`audit-deep-remediation / Batch B`
- 任务：`D2 D4b D6 D7 D11 D13 D14 D17 D18 D19 D20`
- 文件边界：
  - 可改：`docs/`
  - 可改：`owlclaw/db/engine.py`
  - 可改：`owlclaw/web/providers/capabilities.py`
  - 可改：`owlclaw/triggers/webhook/http/app.py`
  - 可改：`owlclaw/governance/visibility.py`
  - 可改：`owlclaw/integrations/hatchet.py`
  - 可改：`owlclaw/triggers/api/server.py`
  - 可改：`owlclaw/triggers/api/auth.py`
  - 可改：`owlclaw/triggers/cron.py`
  - 可改：`owlclaw/agent/runtime/heartbeat.py`
  - 禁止改：`runtime.py` `ledger.py` `app.py` `capabilities/bindings/` `capabilities/registry.py`
- 额外说明：
  - `D4b` 现已解锁，可与其余项并行
  - `D18` 与 `D20` 最好共用一套错误消息脱敏策略

### 给 review-work

- 审校顺序：
  1. 先审 `codex-gpt-work` 已提交的 `D2/D6/D7/D11`，给出 `APPROVE` 或 `FIX_NEEDED`
  2. 再审 `codex-work` 的 `D12/D15/D16/D21`
  3. 最后审 `codex-gpt-work` 的 `D4b/D13/D14/D17/D18/D19/D20`
- 审校重点：
  - `P1` 是否真的封住信任边界
  - `Low` 是否引入回归
  - `heartbeat.py` 是否彻底去掉私有属性耦合

---

## 4. 发布前最低收口线

以下项完成后，可视为本轮“发布条件修复”达标：

- D1 `skill env` 安全边界完成
- D2 tenant_id 多租户文档完成
- D4a + D4b Heartbeat/Ledger 解耦完成
- D7 `/capabilities` 无 DB 不 500
- D11 非 UTF-8 webhook 返回 400
- D12 Console API token 常量时间比较完成

其余 Low 项允许同轮完成，但若要切批次，上述 5 项优先级最高。

---

## 5. 完成定义

- 编码分支有明确 commit
- `.kiro/specs/audit-deep-remediation/tasks.md` 对应项勾选
- 有测试或明确手验记录
- review-work 给出 `APPROVE` 或 `FIX_NEEDED`
- 合入 `main` 后同步所有 worktree
