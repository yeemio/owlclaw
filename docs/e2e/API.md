# E2E Validation API

## `E2EConfig`

路径：`owlclaw.e2e.configuration`

字段：

- `mode: str = "full"`
- `scenario_file: str | None = None`
- `task_id: str = "1"`
- `timeout_seconds: int = 300`
- `fail_fast: bool = False`
- `output_file: str | None = None`

## `load_e2e_config`

路径：`owlclaw.e2e.configuration.load_e2e_config`

签名：

```python
def load_e2e_config(
    *,
    config_path: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> E2EConfig
```

说明：从 JSON 文件加载配置，并应用 `OWLCLAW_E2E_*` 环境变量覆盖。

## `run_cli`

路径：`owlclaw.e2e.cli.run_cli`

签名：

```python
def run_cli(
    argv: list[str] | None = None,
    *,
    orchestrator: TestOrchestrator | None = None,
) -> dict[str, Any]
```

参数：

- `--mode`: `full|mionyee|comparison|integration|performance|concurrency`
- `--scenario-file`: 场景 JSON 文件路径
- `--task-id`: mionyee 任务 ID
- `--timeout-seconds`: 单场景超时时间
- `--fail-fast`: 失败即停
- `--output-file`: 结果输出文件
- `--config`: 配置文件路径

返回：标准化字典结果，结构由对应模式决定。

## `TestOrchestrator`

路径：`owlclaw.e2e.orchestrator.TestOrchestrator`

核心方法：

- `run_full_validation(scenarios, timeout_seconds=300, fail_fast=False)`
- `run_mionyee_task(task_id, params=None)`
- `run_decision_comparison(scenarios)`
- `run_integration_tests(scenarios)`

## `ExecutionEngine`

路径：`owlclaw.e2e.execution_engine.ExecutionEngine`

核心方法：

- `execute_scenario(scenario)`
- `execute_scenarios_concurrently(scenarios, max_concurrency=5)`
- `execute_mionyee_task(task_id, params=None)`
- `inject_error(component, error_type)`
- `cleanup()`

支持错误类型：`timeout`、`network_failure`、`resource_exhausted`。
