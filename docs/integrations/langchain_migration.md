# 从 LangChain 迁移到 OwlClaw 指南

## 迁移目标

将现有 chain/workflow 作为 OwlClaw capability 注册，复用治理、审计和触发体系。

## 迁移步骤

1. 安装依赖：`pip install "owlclaw[langchain]"`
2. 保留原有 runnable 逻辑（`invoke/ainvoke/stream`）
3. 在 OwlClaw 中注册 runnable
4. 配置 schema、fallback、retry、privacy
5. 用 `registry.invoke_handler` 或 Agent Runtime 验证

## 代码对照

原 LangChain：

```python
result = await runnable.ainvoke({"text": "hello"})
```

迁移后：

```python
app.register_langchain_runnable(...)
result = await app.registry.invoke_handler("entry-monitor", session={"text": "hello"})
```

## 常见迁移场景

- 单 runnable：直接 `register_langchain_runnable`
- 多 runnable：每个 capability 单独注册，统一治理
- 流式输出：使用 `LangChainAdapter.execute_stream`
- 高可靠场景：启用 `retry_policy` + `fallback`

## 注意事项

- `mount_skills()` 必须先执行。
- 不安装 LangChain 时，注册会抛出明确 ImportError。
- 旧版本 LangChain 会被版本校验拒绝。
- 生产环境建议开启输入输出脱敏。
