# Design: Cross-language Golden Path

> **目标**：形成面向 Java 团队的低摩擦接入模板。  
> **状态**：设计中  
> **最后更新**：2026-02-26

## 1. 架构

```text
Java Client -> API Gateway -> Runtime -> Ledger
curl Client -> API Gateway -> Runtime -> Ledger
```

## 2. 文件结构

```text
examples/cross_lang/java/
docs/protocol/JAVA_GOLDEN_PATH.md
scripts/verify_cross_lang.ps1
```

## 3. 集成点

- Java 示例调用统一 API 契约。
- 错误处理对齐 `ERROR_MODEL.md`。
- 验证脚本读取同一测试场景数据。

## 4. 红军视角

- 攻击：样例仅覆盖 happy path。  
  防御：必须包含鉴权失败、超时、幂等冲突场景。

---

**维护者**：开发者体验组  
**最后更新**：2026-02-26
