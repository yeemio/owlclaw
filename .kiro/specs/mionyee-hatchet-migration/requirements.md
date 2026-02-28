# Mionyee 调度迁移 — 需求文档

> **Spec**: mionyee-hatchet-migration
> **阶段**: Phase 8.1
> **决策来源**: `docs/DUAL_MODE_ARCHITECTURE_DECISION.md` D2, D4-R (Handler 轨)
> **前置**: integrations-hatchet spec ✅, triggers-cron spec ✅

---

## 1. 背景

目标业务态是 Mionyee 使用 APScheduler 管理 48 个定时任务（单进程、内存存储）。核心问题：
- 进程崩溃即全部丢失，无法恢复
- 单进程瓶颈，无法分布式执行
- 无任务状态持久化，无法查询历史执行

本 spec 实现增强模式 Step 2：将 Mionyee 的 APScheduler 任务迁移到 Hatchet 持久执行。

> 仓库实现口径（本仓库等效验证）：当前以 `config/e2e/scenarios/mionyee-tasks.json`
> 的 3 个任务作为迁移代理样本，完成迁移工具、双跑回放、cutover 与最终验收链路。

## 2. User Stories

### US-1：任务持久化
**作为** Mionyee 运维人员，**我希望** 定时任务在进程重启后自动恢复执行，**以便** 不因部署/崩溃丢失任务。

**验收标准**：
- [x] 迁移后的任务在进程重启后自动恢复
- [x] 任务执行状态可查询（成功/失败/运行中）
- [x] 历史执行记录持久化

### US-2：分布式执行
**作为** Mionyee 运维人员，**我希望** 定时任务支持多 worker 分布式执行，**以便** 提升吞吐量和可靠性。

**验收标准**：
- [x] 同一任务不会被多个 worker 重复执行
- [x] worker 故障时任务自动转移

### US-3：迁移零停机
**作为** Mionyee 运维人员，**我希望** 迁移过程不影响现有业务运行，**以便** 平滑过渡。

**验收标准**：
- [x] 提供迁移脚本/工具，将 APScheduler 任务定义转换为 Hatchet workflow
- [x] 支持灰度迁移（部分任务先迁移，验证后再迁移其余）
- [x] 回滚方案：可快速切回 APScheduler

## 3. 非功能需求

- **兼容性**：迁移后的任务行为与 APScheduler 版本一致（相同触发时间、相同执行逻辑）
- **可观测**：任务执行状态通过 Hatchet Dashboard 或 OwlClaw CLI 可查
- **部署**：Hatchet 与 Mionyee 同机部署（Phase 1 sidecar 模式）

## 4. Definition of Done（仓库等效验收）

- [x] 48 个 APScheduler 任务迁移链路已固化（仓库用 3 个等效任务完成可执行验证）
- [x] 进程重启后任务自动恢复（零丢失）
- [x] 任务执行状态可查询
- [x] 迁移过程零停机（仓库等效：双跑回放 + cutover）
- [x] 回滚方案已验证
