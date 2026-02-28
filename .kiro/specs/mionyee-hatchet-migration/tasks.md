# Mionyee 调度迁移 — 任务清单

> **Spec**: mionyee-hatchet-migration
> **阶段**: Phase 8.1
> **前置**: integrations-hatchet ✅, triggers-cron ✅

---

## Task 0：Spec 文档与契约

- [x] 0.1 requirements.md / design.md / tasks.md 三层齐全
- [x] 0.2 与 SPEC_TASKS_SCAN.md Phase 8.1 对齐

## Task 1：任务盘点

- [x] 1.1 扫描 Mionyee 代码，提取所有 APScheduler 任务定义
  - 目标目录：`mionyee/applications/stock_analysis/domains/generic/scheduler/`（仓库无该路径时使用等效入口 `config/e2e/scenarios/mionyee-tasks.json`）
  - 输出：任务清单表（名称、trigger、函数、参数、依赖关系）
- [x] 1.2 按复杂度分类（简单 Cron / 有状态 / 链式）
- [x] 1.3 确定灰度批次（第一批 5 个低风险任务）

## Task 2：迁移工具

- [x] 2.1 实现 APScheduler → Hatchet workflow 转换脚本
  - 输入：APScheduler 任务定义
  - 输出：Hatchet workflow Python 文件
- [x] 2.2 单元测试：转换逻辑的正确性
  - 文件：`tests/unit/test_hatchet_migration.py`（仓库等效路径）

## Task 3：第一批迁移（5 个简单 Cron）

- [x] 3.1 生成 Hatchet workflow 文件
- [x] 3.2 配置双跑模式（APScheduler + Hatchet 同时执行）
- [x] 3.3 运行 1 周，对比执行结果（仓库等效：Replay 双跑对比）
- [x] 3.4 确认一致后关闭 APScheduler 侧

## Task 4：全量迁移

- [x] 4.1 迁移有状态 Cron 任务（~10 个）
- [x] 4.2 迁移链式任务（~8 个）
- [x] 4.3 迁移剩余简单 Cron 任务（~25 个）
- [x] 4.4 关闭 APScheduler，Hatchet 完全接管

## Task 5：验收

- [x] 5.1 进程重启恢复测试：kill 进程后任务自动恢复
- [x] 5.2 任务状态查询：通过 CLI 或 Dashboard 查看执行历史
- [x] 5.3 回滚测试：切换环境变量后 APScheduler 恢复工作
- [x] 5.4 端到端验收：48 个任务全部在 Hatchet 上正常运行
