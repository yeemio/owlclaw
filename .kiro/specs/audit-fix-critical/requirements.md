# audit-fix-critical — 架构审计 Critical 修复

> **来源**: 2026-03-02 总架构师审计报告
> **优先级**: P0（阻断性，必须在任何交付前修复）
> **预计工时**: 1 天

---

## 背景

2026-03-02 对 OwlClaw 进行了全面架构审计（架构设计 → Spec → 代码实现三层审视），发现 2 个 Critical 级别问题：

1. **C1 熔断器永远不会打开**：CircuitBreakerConstraint 检查 `rec.status == "failure"`，但 Runtime 写入 Ledger 的状态是 `"error"` / `"timeout"`，从不写 `"failure"`。导致熔断器核心保护机制静默失效。
2. **C2 Web Console API 无法挂载**：`mount.py` 中 `_load_console_api_app()` 导入 `owlclaw.web.api.app`（不存在），实际模块是 `owlclaw.web.app`。导致 `owlclaw start` 后 Console 前端加载但所有 API 返回 404。

---

## 功能需求

### REQ-C1：修复 CircuitBreaker 状态匹配

- **现状**：`circuit_breaker.py:82` 检查 `rec.status == "failure"`
- **问题**：Runtime 写入 Ledger 的状态值为 `"success"` / `"error"` / `"skipped"` / `"timeout"` / `"pending"` / `"blocked"`，不包含 `"failure"`
- **修复**：将 `"failure"` 改为 `"error"`，并将 `"timeout"` 也视为失败
- **验收**：
  - 当连续 N 次 Ledger 记录状态为 `"error"` 或 `"timeout"` 时，熔断器打开
  - 现有 CircuitBreaker 测试必须使用 Runtime 实际写入的状态值（`"error"` / `"timeout"`），不得使用 `"failure"`
  - 新增测试验证 `"timeout"` 也触发熔断

### REQ-C2：修复 Console API 挂载路径

- **现状**：`mount.py:49` 执行 `importlib.import_module("owlclaw.web.api.app")`
- **问题**：`owlclaw/web/api/app.py` 不存在，`create_console_app` 定义在 `owlclaw/web/app.py`
- **修复**：将导入目标改为 `owlclaw.web.app`
- **验收**：
  - `owlclaw start` 后 `/api/v1/overview` 返回 200（非 404）
  - WebSocket `/api/v1/ws` 可连接
  - 现有 Console 集成测试通过

---

## 非功能需求

- 修复不得引入新的外部依赖
- 修复不得改变公共 API 接口
- 所有现有测试必须继续通过
