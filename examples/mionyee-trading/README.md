# mionyee-trading

基于 `owlclaw.e2e` 组件的完整链路示例，覆盖 mionyee 三个核心任务：
- `1`: entry-monitor
- `2`: morning-decision
- `3`: knowledge-feedback

## 快速开始

在仓库根目录执行：

```bash
poetry run python examples/mionyee-trading/app.py --all --json
```

单任务执行：

```bash
poetry run python examples/mionyee-trading/app.py --task-id 2 --symbol TSLA --json
```

## 预期输出

- 进程退出码为 `0`
- 每个任务返回 `status: "passed"`
- 输出中包含 `hatchet_workflow_id`（如 `wf-1`）

## 目录结构

- `app.py`: 示例入口，可运行全部任务或单任务
- `skills/`: 三个任务的 SKILL.md 示例

