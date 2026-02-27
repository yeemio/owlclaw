# Design: 开源发布

## 文档联动

- requirements: `.kiro/specs/release/requirements.md`
- design: `.kiro/specs/release/design.md`
- tasks: `.kiro/specs/release/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


> **目标**：定义 OwlClaw 的 PyPI 发布流程和 GitHub 开源准备（Trusted Publishing 优先）  
> **状态**：进行中（发布资产已就绪，外部发布联调待执行）  
> **最后更新**：2026-02-26

---

## 架构例外声明（实现阶段需固化）

本 spec 当前未引入业务层面的数据库铁律例外。实现阶段遵循以下约束：

1. 发布流程（PyPI/GitHub）属于交付层，不改变核心运行时与数据库契约定义。
2. 版本发布必须绑定可追溯构建产物与验收记录。
3. `alembic_version` 属于 Alembic 系统表，不适用业务表约束。

## 1. 架构设计

### 1.1 发布流水线

```
Developer: git tag v0.1.0 && git push --tags
    │
    ▼
GitHub Actions: release.yml
    │
    ├── Step 1: Checkout + Setup Python
    ├── Step 2: Run tests (poetry run pytest)
    ├── Step 3: Build packages (poetry build)
    ├── Step 4: Publish to TestPyPI/PyPI (OIDC Trusted Publishing)
    ├── Step 5: Create GitHub Release + Changelog
    └── Step 6: Notify (success/failure)
```

### 1.2 包结构

```
PyPI Packages:
├── owlclaw                    # 核心 SDK
│   ├── owlclaw[langchain]     # 可选：LangChain 集成
│   └── owlclaw[dev]           # 可选：开发工具
└── owlclaw-mcp                # MCP Server（独立包）
```

---

## 2. 实现细节

### 2.1 pyproject.toml 配置

```toml
[tool.poetry]
name = "owlclaw"
version = "0.1.0"
description = "Agent base for business applications — give your existing systems AI autonomy"
authors = ["yeemio"]
license = "MIT"
readme = "README.md"
keywords = ["agent", "ai", "autonomous", "business", "skills"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.10",
    "Topic :: Software Development :: Libraries",
]

[tool.poetry.extras]
langchain = ["langchain-core"]
dev = ["pytest", "pytest-asyncio", "ruff", "mypy"]

[tool.poetry.scripts]
owlclaw = "owlclaw.cli:main"
```

### 2.2 GitHub Actions Workflow

```yaml
# .github/workflows/release.yml
name: Release
on:
  push:
    tags: ['v*']

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - run: pip install poetry
      - run: poetry install
      - run: poetry run pytest
      - run: poetry build
      - uses: pypa/gh-action-pypi-publish@release/v1
        with:
          packages-dir: dist/
      - uses: softprops/action-gh-release@v2
        with:
          generate_release_notes: true
```

### 2.3 发布前检查清单

```
Pre-release Checklist:
├── [ ] 所有测试通过
├── [ ] CHANGELOG.md 更新
├── [ ] 版本号更新（pyproject.toml）
├── [ ] README.md Quick Start 验证
├── [ ] examples/ 可独立运行
├── [ ] 无敏感信息（git-secrets scan）
├── [ ] MIT LICENSE 正确
└── [ ] 文档链接有效
```

---

## 3. 数据流

### 3.1 发布流程

```
git tag v1.x.x
    → GitHub Actions triggered
    → pytest (all tests pass)
    → python -m build (sdist + wheel)
    → pypa/gh-action-pypi-publish (OIDC upload to TestPyPI/PyPI)
    → gh release create (GitHub Release + notes)
    → notification (success/failure)
```

---

## 4. 错误处理

### 4.1 发布失败

**场景**：PyPI/TestPyPI 上传失败（OIDC 交换失败、配置错误、版本冲突）

**处理**：GitHub Actions 标记为失败，通知维护者手动处理。版本号不可重复使用。

### 4.2 测试失败

**场景**：Tag push 后测试未通过

**处理**：发布流程终止，不上传到 PyPI。删除 tag 并修复后重新发布。

---

## 5. 配置

### 5.1 环境变量

| 变量 | 说明 | 存储位置 |
|------|------|---------|
| `ACTIONS_ID_TOKEN_REQUEST_TOKEN` | GitHub OIDC token（Actions 注入） | GitHub Actions runtime |
| `ACTIONS_ID_TOKEN_REQUEST_URL` | GitHub OIDC endpoint（Actions 注入） | GitHub Actions runtime |

### 5.2 平台配置

| 项 | 说明 |
|------|------|
| Trusted Publisher | PyPI/TestPyPI 需配置 `owner=yeemio`、`repo=owlclaw`、`workflow=.github/workflows/release.yml`、`environment=pypi-release` |
| Branch Protection | `main` 需开启 required checks（Lint/Test/Build）与 PR 审核策略 |
| Environment Policy | `pypi-release` 允许 `main` 与 `codex-gpt-work` 触发 |

---

## 6. 测试策略

### 6.1 发布验证测试

```bash
# 在干净环境中验证
python -m venv test_env && source test_env/bin/activate
pip install owlclaw
owlclaw --version
owlclaw skill list
python -c "from owlclaw import OwlClaw; print('OK')"
```

---

## 7. 迁移计划

### 7.1 Phase 1：准备（1-2 天）
- [ ] 确认 pyproject.toml 包元数据完整
- [ ] 创建 PyPI/TestPyPI Trusted Publisher 映射
- [ ] 校验 GitHub Actions OIDC 权限与 environment 策略
- [ ] 编写 CHANGELOG.md
- [ ] 编写 CONTRIBUTING.md

### 7.2 Phase 2：发布（1 天）
- [ ] 创建 release workflow
- [ ] 测试 tag-triggered 发布流程
- [ ] 发布 v0.1.0 到 PyPI

### 7.3 Phase 3：社区（1-2 天）
- [ ] 创建 Issue 模板
- [ ] 启用 Discussions
- [ ] 编写 README 英文版

---

**维护者**：OwlClaw Team  
**最后更新**：2026-02-22
