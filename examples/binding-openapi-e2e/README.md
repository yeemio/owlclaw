# binding-openapi-e2e

端到端示例：`OpenAPI -> binding SKILL.md -> 业务规则补充 -> Agent 可加载`

## 1) 生成 binding SKILL.md

```bash
owlclaw migrate scan --openapi ./openapi.yaml --output-mode binding --output ./capabilities
```

## 2) 生成业务规则模板（可选）

```bash
owlclaw skill init --from-binding ./capabilities/create-order --name create-order-rules --output ./capabilities
```

## 3) 校验并加载

```bash
owlclaw skill validate ./capabilities
```

该目录已包含一个补充业务规则后的示例文件：

- `capabilities/create-order/SKILL.md`
