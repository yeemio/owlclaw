# Mionyee 案例数据采集指南（真实数据）

本指南用于 `content-launch` 的真实数据采集，严格禁止编造数据。

## 目标

产出两类 before/after 对比：

- LLM 治理：成本、调用量、拦截量
- 调度迁移：任务总量、成功/失败、恢复时间

## 数据导出格式

### 1) LLM 数据（治理前/后各一份 CSV）

必填列：

- `cost_usd`
- `calls_total`
- `calls_blocked`

### 2) 调度数据（迁移前/后各一份 CSV）

必填列：

- `total_tasks`
- `success_tasks`
- `failed_tasks`
- `recovery_seconds`

## 生成对比报告

运行脚本（仅聚合已提供的真实 CSV）：

```bash
poetry run python scripts/content/collect_mionyee_case_data.py \
  --llm-before ./data/mionyee/llm_before.csv \
  --llm-after ./data/mionyee/llm_after.csv \
  --scheduler-before ./data/mionyee/scheduler_before.csv \
  --scheduler-after ./data/mionyee/scheduler_after.csv \
  --output-json ./docs/content/mionyee-case-data.json \
  --output-md ./docs/content/mionyee-case-data.md
```

输出：

- `mionyee-case-data.json`：结构化指标与源文件哈希
- `mionyee-case-data.md`：可直接引用的对比表

## 真实性规则

- 仅允许使用导出的原始数据文件做聚合
- 报告必须保留源文件 SHA256
- 未拿到真实数据时不得填写“结果”段落

