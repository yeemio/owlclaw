# Declarative Binding 三角色工作流

本文档对应 `declarative-binding` Task 19，定义 IT 运维、业务用户、AI 开发者三类角色的最小工作流。

## 1. IT 运维（一次性接入）

目标：从存量系统自动生成可用的 binding SKILL.md，不手写 schema。

```bash
# OpenAPI -> binding
owlclaw migrate scan --openapi ./openapi.yaml --output-mode binding --output ./capabilities

# ORM -> binding
owlclaw migrate scan --orm ./orm-ops.yaml --output-mode binding --output ./capabilities
```

然后配置环境变量（示例）：

```bash
set XAPI_API_KEY=xxx
set READ_DB_DSN=postgresql+psycopg://user:pass@host:5432/db
```

校验：

```bash
owlclaw skill validate ./capabilities
```

## 2. 业务用户（按需补充规则）

目标：只写自然语言规则，不改 binding 结构。

```bash
owlclaw skill init --from-binding ./capabilities/create-order --name create-order-rules --output ./capabilities
```

业务用户只编辑生成文件中的 `# Instructions` 内容，重点补充：

- 触发条件（什么时候调用）
- 风险/阈值判断（调用前检查）
- 异常与兜底策略（调用失败后处理）

## 3. AI 开发者（联调与治理）

目标：把 binding skill 纳入运行时治理并完成联调。

1. 加载能力目录并确认技能被扫描。
2. 检查治理配置（budget/rate-limit/visibility）。
3. 回放典型请求，验证参数映射、返回映射与 Ledger 记录。

建议命令：

```bash
owlclaw skill validate ./capabilities --verbose
poetry run pytest tests/unit/capabilities/test_bindings_*.py -q
```
