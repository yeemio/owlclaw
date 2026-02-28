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

## 基于真实数据选择文章方向（Task 2.1）

当 `mionyee-case-data.json` 生成后，执行：

```bash
poetry run python scripts/content/select_article_direction.py \
  --input-json ./docs/content/mionyee-case-data.json \
  --output-json ./docs/content/article-direction-decision.json
```

输出字段：

- `direction`：`A` / `B` / `C`
- `title`：推荐标题
- `rationale`：基于真实指标的选择依据

## 发布结果归档与验收（Task 2.6/2.7/5.1）

先填写模板：

- `docs/content/publication-evidence-template.json`

然后执行：

```bash
poetry run python scripts/content/record_publication_results.py \
  --input-json ./docs/content/publication-evidence-template.json \
  --output-json ./docs/content/publication-evidence.json \
  --output-md ./docs/content/publication-evidence.md
```

脚本会自动给出：

- `meets_task_2_6`：是否满足 Reddit/HN 英文发布
- `meets_task_2_7`：是否满足掘金/V2EX 中文发布
- `meets_task_5_1`：是否满足至少 2 个渠道发布

## 一键收口评估（外部输入到位后）

```bash
poetry run python scripts/content/assess_content_launch_readiness.py \
  --case-data-json ./docs/content/mionyee-case-data.json \
  --case-data-md ./docs/content/mionyee-case-data.md \
  --direction-json ./docs/content/article-direction-decision.json \
  --publication-json ./docs/content/publication-evidence.json \
  --case-study-md ./docs/content/mionyee-case-study.md \
  --output-json ./docs/content/content-launch-readiness.json \
  --output-md ./docs/content/content-launch-readiness.md
```

该报告会输出当前剩余未满足的外部收口项列表。

## 真实性规则

- 仅允许使用导出的原始数据文件做聚合
- 报告必须保留源文件 SHA256
- 未拿到真实数据时不得填写“结果”段落
