# SKILL.md 书写指南（面向非技术用户）

## 1. 最小可用版本（5 分钟上手）

一个可工作的 `SKILL.md` 只需要 3 个部分：

```markdown
---
name: check-order
description: 查询订单状态并给出处理建议
---

# Instructions

1. 先确认用户提供了订单号。
2. 查询订单后，用简洁语言反馈状态。
3. 如果订单异常，给出下一步建议。
```

要求：

- `name` 使用小写短横线（kebab-case），例如 `check-order`
- `description` 一句话说明能力
- body 用 Markdown 写业务规则

## 2. 何时需要 `tools` 或 `binding`

- 只写业务知识：不需要 `tools`，Agent 仅把它当规则文档
- 需要调用外部系统：添加 `tools`，并在工具下声明 `binding`

示例（HTTP 查询）：

```yaml
---
name: check-order
description: 查询订单状态
tools:
  fetch-order:
    description: 根据订单号获取订单
    order_id: string
    binding:
      type: http
      method: GET
      url: https://api.example.com/orders/{order_id}
---
```

## 3. `tools` 参数简写（推荐）

可以直接写：

```yaml
tools:
  check-stock:
    sku: string
    warehouse_id: string
```

也可以写带说明的版本：

```yaml
tools:
  check-stock:
    sku:
      type: string
      description: 商品编码
    warehouse_id:
      type: string
      description: 仓库编码
```

运行时会自动展开成完整 JSON Schema。

## 4. 安全最佳实践

- 密钥不要写死在文件里
- 使用环境变量引用：`${API_TOKEN}`
- 把所需环境变量写到 `owlclaw.prerequisites.env`

## 5. 常见错误

- `name` 不是 kebab-case（如 `CheckOrder`）
- `description` 为空
- body 没有任何业务指引
- 在 binding 里写明文 token

## 6. 建议流程

1. 先写最小版本（name + description + body）
2. 运行 `owlclaw skill validate`
3. 再逐步补 `tools` 与 `binding`
4. 每次变更后重新执行 validate
