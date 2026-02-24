# E2E Validation 使用说明

## 概览

E2E Validation 模块用于验证 OwlClaw 关键链路：

- mionyee 任务端到端执行（Cron -> Runtime -> Skills -> Governance -> Hatchet）
- V3 Agent 与 Original Cron 的决策对比
- 组件集成、错误注入、并发执行与性能场景

主要入口：

- `owlclaw.e2e.orchestrator.TestOrchestrator`
- `owlclaw.e2e.execution_engine.ExecutionEngine`
- `owlclaw.e2e.cli.run_cli`

## 快速开始

1. 准备场景文件（参考 `config/e2e/scenarios/`）。
2. 使用 Python 调用 CLI 入口：

```python
from owlclaw.e2e.cli import run_cli

result = run_cli([
    "--mode", "full",
    "--scenario-file", "config/e2e/scenarios/decision-comparison.json",
    "--timeout-seconds", "120",
    "--fail-fast",
])
print(result)
```

## 配置

支持 JSON 配置文件和环境变量覆盖：

- 配置文件字段：`mode`、`scenario_file`、`task_id`、`timeout_seconds`、`fail_fast`、`output_file`
- 环境变量：
  - `OWLCLAW_E2E_MODE`
  - `OWLCLAW_E2E_SCENARIO_FILE`
  - `OWLCLAW_E2E_TASK_ID`
  - `OWLCLAW_E2E_TIMEOUT_SECONDS`
  - `OWLCLAW_E2E_FAIL_FAST`
  - `OWLCLAW_E2E_OUTPUT_FILE`

## 常见模式

- `full`: 执行完整验证
- `mionyee`: 执行单个 mionyee 任务
- `comparison`: 执行双系统决策对比
- `integration`: 执行集成测试场景
- `performance`: 执行性能场景
- `concurrency`: 执行并发场景

## 输出

可选 `--output-file` 生成 JSON 报告，便于归档与后处理。
