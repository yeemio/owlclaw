# audit-fix-critical — 设计文档

---

## C1：CircuitBreaker 状态修复

### 变更范围

**文件**：`owlclaw/governance/constraints/circuit_breaker.py`

**当前代码**（第 82 行）：
```python
if rec.status == "failure":
```

**修改为**：
```python
if rec.status in ("error", "timeout"):
```

### 设计考量

1. **为什么包含 `"timeout"`**：超时是一种失败形式，连续超时说明下游服务不可用，应触发熔断保护。
2. **为什么不包含 `"skipped"` / `"blocked"`**：这些是治理层主动跳过/阻断的结果，不代表执行失败。
3. **`governance/proxy.py` 写 `"failure"` 的问题**：Proxy 层是独立的治理代理，它的 Ledger 记录与 Runtime 的记录可能写入不同路径。CircuitBreaker 应基于 Runtime 实际写入的状态判断，因此对齐 Runtime 的 `"error"` / `"timeout"`。

### 测试修复

现有测试 `tests/unit/governance/` 中的 CircuitBreaker 测试需要：
1. 将 mock 数据中的 `status="failure"` 改为 `status="error"`
2. 新增 `status="timeout"` 的测试用例
3. 新增混合场景测试（error + timeout 交替出现）

---

## C2：Console mount 路径修复

### 变更范围

**文件**：`owlclaw/web/mount.py`

**当前代码**（第 49 行）：
```python
module = importlib.import_module("owlclaw.web.api.app")
```

**修改为**：
```python
module = importlib.import_module("owlclaw.web.app")
```

### 设计考量

1. `create_console_app` 定义在 `owlclaw/web/app.py`，它内部调用 `owlclaw.web.api.create_api_app()` 并注册 providers
2. 修复后 `_load_console_api_app()` 能正确获取 `create_console_app` 并创建 FastAPI 子应用
3. `mount_console()` 将子应用挂载到 `/api/v1`，前端 SPA 的 API 调用恢复正常

### 测试补强

1. 修复 `tests/unit/web/test_mount.py` 确保 `_load_console_api_app()` 返回非 None
2. 新增集成测试：启动 app → 请求 `/api/v1/overview` → 断言 200

---

## 数据流验证

修复后的完整数据流：

```
owlclaw start
  → create_start_app()
    → mount_console(app)
      → _load_console_api_app()
        → importlib.import_module("owlclaw.web.app")  # 修复点
        → create_console_app()
        → FastAPI sub-app
      → app.mount("/api/v1", sub_app)
      → app.mount("/console", SPAStaticFiles)
  → uvicorn.run(app)

用户访问 /console/ → SPA 加载
SPA 调用 /api/v1/overview → FastAPI 路由 → OverviewProvider → 真实数据
```
