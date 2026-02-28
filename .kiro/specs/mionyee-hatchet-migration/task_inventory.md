# Mionyee APScheduler 任务盘点（等效入口）

> 基于仓库现状，原目标目录 `mionyee/applications/stock_analysis/domains/generic/scheduler/` 不存在。  
> 本盘点使用等效入口：`config/e2e/scenarios/mionyee-tasks.json`，并由
> `scripts/mionyee_apscheduler_to_hatchet.py` + `owlclaw.integrations.hatchet_migration` 提取。

## 任务清单

| 任务名 | Cron | 源函数映射 | 复杂度 | 依赖 |
|---|---|---|---|---|
| mionyee task 1 | `30 9 * * 1-5` | `mionyee.scheduler.entry_monitor` | simple_cron | - |
| mionyee task 2 | `0 12 * * 1-5` | `mionyee.scheduler.risk_review` | stateful_cron | - |
| mionyee task 3 | `30 14 * * 1-5` | `mionyee.scheduler.position_adjust` | chained | mionyee task 1 |

## 灰度批次（第一批低风险）

- 第一批候选（目标最多 5 个，当前可用 1 个）：
  - `mionyee task 1`（simple_cron）
- 说明：当前仓库仅含 3 个 mionyee 示例任务，待真实业务仓库接入后扩展到 48 个任务并重跑盘点。

## 产物

- 迁移库函数：`owlclaw/integrations/hatchet_migration.py`
- 迁移脚本：`scripts/mionyee_apscheduler_to_hatchet.py`
- 生成示例：`examples/mionyee-trading/generated_hatchet_tasks.py`
- 分类迁移产物：
  - `examples/mionyee-trading/generated_hatchet_tasks_simple_cron.py`
  - `examples/mionyee-trading/generated_hatchet_tasks_stateful_cron.py`
  - `examples/mionyee-trading/generated_hatchet_tasks_chained.py`
- 双跑与切换：
  - replay 脚本：`scripts/mionyee_dual_run_replay.py`
  - cutover 脚本：`scripts/mionyee_scheduler_cutover.py`
  - 决策文件：`.kiro/specs/mionyee-hatchet-migration/cutover_decision.json`
