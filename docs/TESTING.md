# 测试指南（Testing）

## 测试分层

1. `tests/unit/`
- 目标：纯逻辑验证，不依赖外部服务。
- 运行：`poetry run pytest tests/unit/ -q`

2. `tests/integration/`
- 目标：跨模块与外部边界验证（PostgreSQL/Hatchet/Redis/Kafka 等）。
- 运行：`poetry run pytest tests/integration/ -q`
- 服务不可用时，按 `requires_*` marker 自动 `skip`。

## 常用命令

```bash
# 全量
poetry run pytest

# unit only
poetry run pytest tests/unit/ -q

# integration only
poetry run pytest tests/integration/ -q

# 指定 marker（仅 unit / 仅 integration）
poetry run pytest -m unit -q
poetry run pytest -m "not integration" -q
poetry run pytest -m requires_postgres -q
```

## 服务依赖矩阵

| 测试层 | PostgreSQL | Hatchet | Redis | Kafka |
|---|---|---|---|---|
| unit | 否（应为 0 外部依赖） | 否 | 否 | 否 |
| integration | 是（默认） | 按用例 | 按用例 | 按用例 |

## 并行测试

使用 `pytest-xdist` 多进程加速（CI 或本地大批量时）：

```bash
poetry run pytest tests/unit/ -n auto -q
```

`-n auto` 使用与 CPU 核数相当的 worker 数。

## HTML 报告

生成自包含 HTML 测试报告（依赖 `pytest-html`）：

```bash
poetry run pytest --html=report.html --self-contained-html
```

报告输出到 `report.html`，可在浏览器中打开查看结果与时长分布。

## 覆盖率目标与 HTML 报告

1. unit 目标：`>= 73%`（当前阶段可执行门槛，避免伪失败阻塞）
2. overall 目标：`>= 75%`（integration 叠加后的当前阶段门槛）
3. 配置位置：`pyproject.toml` 的 `[tool.coverage.*]`

生成覆盖率 HTML 报告（输出到 `htmlcov/`）：

```bash
poetry run pytest --cov=owlclaw --cov-report=html
```

## 新增测试建议

1. 优先把逻辑放到 unit；仅把真实边界放到 integration。
2. 新 integration 用例请声明 `requires_*` 依赖（或依赖 integration 默认 postgres 标注）。
3. 遇到外部服务波动时，优先保证 “可跳过而不是误失败”。
