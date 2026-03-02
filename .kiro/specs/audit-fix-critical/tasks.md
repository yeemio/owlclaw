# audit-fix-critical — 任务清单

---

## Task 0：C1 修复 CircuitBreaker 状态匹配

- [x] 0.1 修改 `owlclaw/governance/constraints/circuit_breaker.py`：将 `rec.status == "failure"` 改为 `rec.status in ("error", "timeout")`
- [x] 0.2 修复现有 CircuitBreaker 单元测试：将 mock 数据中 `status="failure"` 改为 `status="error"`
- [x] 0.3 新增测试：`status="timeout"` 连续 N 次触发熔断
- [x] 0.4 新增测试：`"error"` 和 `"timeout"` 混合出现时正确计数
- [x] 0.5 验证 `poetry run pytest tests/unit/governance/` 全部通过

## Task 1：C2 修复 Console API 挂载路径

- [x] 1.1 修改 `owlclaw/web/mount.py`：将 `importlib.import_module("owlclaw.web.api.app")` 改为 `importlib.import_module("owlclaw.web.app")`
- [x] 1.2 修复/补强 `tests/unit/web/test_mount.py`：验证 `_load_console_api_app()` 返回有效 app
- [x] 1.3 补强集成测试：`owlclaw start` 后 `/api/v1/overview` 返回 200
- [x] 1.4 验证 `poetry run pytest tests/unit/web/ tests/integration/test_console_*.py` 全部通过

## Task 2：回归验证

- [x] 2.1 运行完整测试套件 `poetry run pytest tests/unit/` 确认无回归
- [x] 2.2 运行 `poetry run ruff check owlclaw/governance/constraints/ owlclaw/web/` 确认无 lint 问题
