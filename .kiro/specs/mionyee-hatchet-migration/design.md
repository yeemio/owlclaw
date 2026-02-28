# Mionyee 调度迁移 — 设计文档

> **Spec**: mionyee-hatchet-migration
> **阶段**: Phase 8.1
> **接入模式**: 增强模式（Handler 轨）

---

## 1. 迁移策略

### 1.1 任务分类

Mionyee 目标业务态的 48 个 APScheduler 任务按复杂度分类：

| 类别 | 数量（估计） | 迁移复杂度 | 说明 |
|------|------------|-----------|------|
| 简单 Cron | ~30 | 低 | 固定时间触发，无状态 |
| 有状态 Cron | ~10 | 中 | 依赖上次执行结果 |
| 链式任务 | ~8 | 高 | 多步骤，有依赖关系 |

仓库等效验证使用 3 个任务样本（来自 `config/e2e/scenarios/mionyee-tasks.json`）：

| 类别 | 样本数 | 代表任务 |
|------|--------|---------|
| 简单 Cron | 1 | mionyee task 1 |
| 有状态 Cron | 1 | mionyee task 2 |
| 链式任务 | 1 | mionyee task 3（依赖 task 1） |

### 1.2 迁移路径

```
APScheduler 任务定义
    │
    ▼
迁移工具扫描（提取 trigger + func + args）
    │
    ▼
生成 Hatchet Workflow 定义
    │
    ▼
灰度验证（双跑对比）
    │
    ▼
切换（关闭 APScheduler，Hatchet 接管）
```

## 2. Hatchet Workflow 映射

### 2.1 简单 Cron 映射

```python
# APScheduler 原始
scheduler.add_job(func=check_stock_price, trigger='cron', hour=9, minute=30)

# Hatchet 等效
@hatchet.workflow(on_crons=["30 9 * * *"])
class CheckStockPriceWorkflow:
    @hatchet.step()
    async def run(self, context):
        return await check_stock_price()
```

### 2.2 有状态任务映射

利用 Hatchet 的 step data 传递状态，替代 APScheduler 的 jobstore。

### 2.3 链式任务映射

利用 Hatchet 的多 step workflow，替代 APScheduler 的手动链式调用。

## 3. 迁移工具

当前实现为独立脚本链路：

- `scripts/mionyee_apscheduler_to_hatchet.py`
- `scripts/mionyee_dual_run_replay.py`
- `scripts/mionyee_scheduler_cutover.py`
- `scripts/mionyee_migration_acceptance.py`

输入：`config/e2e/scenarios/mionyee-tasks.json`（等效入口）  
输出：Hatchet workflow Python 文件 + 双跑报告 + cutover 决策 + 最终验收报告

## 4. 灰度迁移

1. 先迁移 5 个低风险简单 Cron 任务
2. 双跑 1 周（APScheduler + Hatchet 同时执行，对比结果，仓库等效为 replay 对比）
3. 确认一致后关闭 APScheduler 侧
4. 逐批迁移剩余任务

## 5. 回滚方案

- APScheduler 配置保留不删除
- 环境变量/配置 `SCHEDULER_BACKEND=apscheduler|dual|hatchet` 控制切换
- 回滚操作：改环境变量 + 重启

## 6. 部署

Hatchet 与 Mionyee 同机部署（复用 OwlClaw 的 Hatchet 集成层 `owlclaw.integrations.hatchet`）。

## 7. 测试策略

- **单元测试**：迁移工具的 APScheduler → Hatchet 转换逻辑
- **集成测试**：迁移后任务的触发时间和执行结果与原始一致
- **恢复测试**：进程 kill 后任务自动恢复
- **灰度测试**：双跑对比结果一致性
- **最终验收**：`final_acceptance_report.json` gate 必须为 `passed=true`
