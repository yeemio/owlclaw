# Tasks: Console Integration

> **Spec**: console-integration  
> **Design**: `design.md`  
> **最后更新**: 2026-02-28

---

## Task 0：Console 挂载器

**目标**：实现静态文件检测与自动挂载

**文件**：
- `owlclaw/web/mount.py`

**实现**：
- [x] 0.1 实现 `mount_console(app)` 函数：检测 `owlclaw/web/static/index.html`，存在则挂载 Console API 和静态文件
- [x] 0.2 实现 SPA fallback 中间件：非 API 路径返回 `index.html`
- [x] 0.3 实现根路径 `/` 重定向到 `/console/`

**验收**：
- 有静态文件时 `/console/` 返回 HTML
- 无静态文件时 `mount_console()` 返回 False，无报错
- `/api/v1/overview` 和 `/console/` 共存于同一端口
- `poetry run pytest tests/unit/web/test_mount.py` 通过

---

## Task 1：集成到 `owlclaw start`

**目标**：在 `owlclaw start` 启动流程中调用 Console 挂载

**文件**：
- `owlclaw/app.py`（或 `owlclaw/cli/start.py`，视现有实现）

**实现**：
- [x] 1.1 在应用启动流程中调用 `mount_console(app)`
- [x] 1.2 路由优先级正确：API > MCP > Webhook > Console Static > Root Redirect
- [x] 1.3 日志输出 Console 挂载状态

**验收**：
- `owlclaw start` 后 `/console/` 可访问（有静态文件时）
- `owlclaw start` 后 Agent 运行时正常（无静态文件时）
- `poetry run pytest tests/integration/test_console_mount.py` 通过

---

## Task 2：CLI `owlclaw console` 命令

**目标**：便捷打开 Console

**文件**：
- `owlclaw/cli/console.py`
- `owlclaw/cli/__init__.py`（注册命令）

**实现**：
- [x] 2.1 实现 `owlclaw console` 命令：打开浏览器 + 显示 URL
- [x] 2.2 支持 `--port` 参数（默认 8000）
- [x] 2.3 无静态文件时提示安装 `owlclaw[console]`
- [x] 2.4 注册到 CLI 命令组

**验收**：
- `owlclaw console` 输出 URL 并尝试打开浏览器
- `owlclaw console --port 9000` 使用指定端口
- `poetry run pytest tests/unit/cli/test_console_cmd.py` 通过

---

## Task 3：构建流程与打包

**目标**：前端构建产物集成到 Python 包

**文件**：
- `pyproject.toml`
- `Makefile`（或构建脚本）

**实现**：
- [x] 3.1 配置 `pyproject.toml` package-data 包含 `owlclaw/web/static/**`
- [x] 3.2 配置 `[tool.poetry.extras]` 新增 `console` 组
- [x] 3.3 添加构建脚本（`make build-console` 或 `scripts/build_console.sh`）
- [x] 3.4 验证 `poetry build` 后 wheel 包含静态文件

**验收**：
- `poetry build` 产出的 wheel 包含 `owlclaw/web/static/` 目录
- `pip install owlclaw[console]` 后静态文件可用
- `pip install owlclaw` 后 Console 优雅降级

---

## Task 4：集成测试与文档

**目标**：端到端验证和开发文档

**文件**：
- `tests/integration/test_console_integration.py`
- `docs/CONSOLE_DEVELOPMENT.md`

**实现**：
- [x] 4.1 集成测试：完整启动 → Console 可访问 → API 返回数据
- [x] 4.2 集成测试：无静态文件 → 优雅降级 → Agent 正常
- [x] 4.3 编写 Console 开发指南（前端开发流程、构建、调试）

**验收**：
- 集成测试覆盖挂载和降级两种场景
- 开发文档清晰可执行
- `poetry run pytest tests/integration/test_console_integration.py` 通过

---

**维护者**：yeemio  
**最后更新**：2026-02-28
