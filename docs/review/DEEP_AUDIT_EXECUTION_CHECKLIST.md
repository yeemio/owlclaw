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

### Batch A：立即启动

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

**codex-gpt-work**

| ID | Finding | 文件 | 目标 | 验收 |
|---|---|---|---|---|
| D2 | P1-2 | `docs/` | 明确 tenant_id 当前行为与多租户边界 | 文档写清“仅自托管/非安全标签可接受” |
| D6 | Low-6 | `owlclaw/db/engine.py` | 收窄异常映射 | 非连接类异常不再误报 |
| D7 | Low-7 | `owlclaw/web/providers/capabilities.py` | 无 DB 时 `/capabilities` 不 500 | 返回 200 + 零统计 |
| D11 | Low-11 | `owlclaw/triggers/webhook/http/app.py` | 非 UTF-8 body 返回 400 | 有测试或手验 |

### Batch B：依赖 D4a 合并到 main 后启动

**codex-gpt-work**

| ID | Finding | 文件 | 前置 | 目标 | 验收 |
|---|---|---|---|---|---|
| D4b | Low-4b | `owlclaw/agent/runtime/heartbeat.py` | D4a 已合并到 `main` | Heartbeat 改走 Ledger 公开 API | grep 无 `_session_factory`；测试通过 |

---

## 3. 统筹下发模板

### 给 codex-work

- 批次：`audit-deep-remediation / Batch A`
- 任务：`D1 D3 D5 D4a D8 D9 D10`
- 文件边界：
  - 可改：`owlclaw/agent/runtime/runtime.py`
  - 可改：`owlclaw/governance/ledger.py`
  - 可改：`owlclaw/app.py`（仅 `health_status()`）
  - 禁止改：`heartbeat.py` `engine.py` `capabilities.py` `webhook http/app.py` `docs/`
- 审校移交条件：
  - 至少包含对应测试
  - `tasks.md` 勾选完成项
  - commit message 标注 `audit-deep-remediation`

### 给 codex-gpt-work

- 批次：`audit-deep-remediation / Batch A`
- 任务：`D2 D6 D7 D11`
- 文件边界：
  - 可改：`docs/`
  - 可改：`owlclaw/db/engine.py`
  - 可改：`owlclaw/web/providers/capabilities.py`
  - 可改：`owlclaw/triggers/webhook/http/app.py`
  - 禁止改：`runtime.py` `ledger.py` `app.py`
- 额外说明：
  - `D4b` 不在本轮启动
  - 待 `D4a` 合并到 `main` 后再接第二轮

### 给 review-work

- 审校顺序：
  1. 先审 `codex-work` 的 `D1/D4a`
  2. 一旦 `D4a` 合入 `main`，通知 `codex-gpt-work` 可启动 `D4b`
  3. 再审 `codex-gpt-work` 的 `D2/D6/D7/D11`
  4. 最后审 `D4b`
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

其余 Low 项允许同轮完成，但若要切批次，上述 5 项优先级最高。

---

## 5. 完成定义

- 编码分支有明确 commit
- `.kiro/specs/audit-deep-remediation/tasks.md` 对应项勾选
- 有测试或明确手验记录
- review-work 给出 `APPROVE` 或 `FIX_NEEDED`
- 合入 `main` 后同步所有 worktree
