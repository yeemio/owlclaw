# binding-http 示例

本示例展示 Declarative Binding 的三种 Skill 形态：

1. `order-http-active`：有 binding、无 `@handler`，直接调用 HTTP API（active 模式）
2. `order-http-shadow`：有 binding、无 `@handler`，写操作走 shadow 模式（只记录不发送）
3. `order-shell-fallback`：无 binding、无 `@handler`，在 Skill body 中给出 shell/curl 执行指引

## 目录结构

```text
examples/binding-http/
├── capabilities/
│   ├── order-http-active/SKILL.md
│   ├── order-http-shadow/SKILL.md
│   └── order-shell-fallback/SKILL.md
└── mock_server.py
```

## 1) 启动 mock HTTP 服务

```bash
poetry run python examples/binding-http/mock_server.py --port 8008
```

服务提供：

- `GET /orders/{order_id}`
- `POST /orders`

## 2) 校验示例 Skill

```bash
poetry run owlclaw skill validate examples/binding-http/capabilities
```

## 3) 三种模式说明

### A. binding + active

`order-http-active/SKILL.md` 的 `fetch-order` 工具会真实发送 GET 请求到 mock server。

### B. binding + shadow

`order-http-shadow/SKILL.md` 的 `create-order` 配置为 `mode: shadow`。  
运行时写请求不会发出，只会在 Ledger 记录 shadow 结果，可用于零代码对比验证。

### C. no binding + no handler（shell 指令）

`order-shell-fallback/SKILL.md` 不声明 tools。Agent 可根据 body 中的 curl 指令，通过 shell 能力执行外部命令。

## 4) 适用场景

- 先用 active 模式连通读接口，验证参数和返回结构
- 写接口先用 shadow 模式观察调用行为，再切换 active
- 无法立即接入 binding 时，先以 shell 指令模式落地
