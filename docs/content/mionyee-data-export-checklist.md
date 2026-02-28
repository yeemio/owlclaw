# Mionyee 真实数据导出执行清单

用于 `content-launch` Task 1（真实数据采集），配合以下工具：

- `docs/content/mionyee-data-collection-guide.md`
- `scripts/content/verify_mionyee_case_inputs.py`
- `scripts/content/collect_mionyee_case_data.py`

## 1. 输入文件清单

请在同一目录准备 4 份 CSV：

1. `llm_before.csv`
2. `llm_after.csv`
3. `scheduler_before.csv`
4. `scheduler_after.csv`

## 2. 列要求

### LLM CSV 必填列

- `cost_usd`
- `calls_total`
- `calls_blocked`

### Scheduler CSV 必填列

- `total_tasks`
- `success_tasks`
- `failed_tasks`
- `recovery_seconds`

## 3. 执行步骤

1. 先校验输入完整性

```bash
poetry run python scripts/content/verify_mionyee_case_inputs.py --input-dir ./data/mionyee --output ./docs/content/mionyee-input-validation.json
```

2. 校验通过后生成对比报告

```bash
poetry run python scripts/content/collect_mionyee_case_data.py \
  --llm-before ./data/mionyee/llm_before.csv \
  --llm-after ./data/mionyee/llm_after.csv \
  --scheduler-before ./data/mionyee/scheduler_before.csv \
  --scheduler-after ./data/mionyee/scheduler_after.csv \
  --output-json ./docs/content/mionyee-case-data.json \
  --output-md ./docs/content/mionyee-case-data.md
```

## 4. 通过标准

- 校验报告 `status` 为 `pass`
- 每个输入文件 `rows` > 0
- 汇总报告包含 4 个源文件 `sha256`
- 未使用任何手工编造数值

