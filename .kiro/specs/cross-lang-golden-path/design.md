# Design: Cross-language Golden Path

> **目标**：让 Java 团队无需 Python SDK 也能快速接入。  
> **状态**：设计中  
> **最后更新**：2026-02-26

## 1. 路径设计

```text
Java Client -> HTTP API Gateway -> OwlClaw Runtime -> Ledger
curl       -> HTTP API Gateway -> OwlClaw Runtime -> Ledger
```

## 2. 样例结构

```text
examples/cross_lang/java/
docs/protocol/JAVA_GOLDEN_PATH.md
scripts/verify_cross_lang.ps1
```

## 3. 关键设计

- 先 HTTP 再 MCP（降低 Java 端复杂度）
- 错误对象与重试策略遵循统一错误域
- 幂等键用于触发类请求去重

## 4. 红军视角

- 攻击：样例只适配 happy path，生产失败率高。  
  防御：强制加入超时、重试、幂等、鉴权失败场景。

---

**维护者**：开发者体验组  
**最后更新**：2026-02-26

