# Design: CI 配置

> **目标**：建立 CI 流水线，覆盖 lint/test/build/release  
> **状态**：设计中  
> **最后更新**：2026-02-22

---

## 1. 架构设计

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        GitHub Actions                            │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Lint       │  │    Test      │  │    Build     │          │
│  │   Pipeline   │  │   Pipeline   │  │   Pipeline   │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                   │
│         ▼                 ▼                 ▼                   │
│  ┌──────────────────────────────────────────────────┐          │
│  │              Quality Gates                        │          │
│  │  • Ruff (lint)                                   │          │
│  │  • MyPy (type check)                             │          │
│  │  • Pytest (unit + integration)                   │          │
│  │  • Coverage (>80%)                               │          │
│  └──────────────────────┬───────────────────────────┘          │
│                         │                                       │
│                         ▼                                       │
│  ┌──────────────────────────────────────────────────┐          │
│  │              Release Pipeline                     │          │
│  │  • Version bump                                  │          │
│  │  • Build wheel                                   │          │
│  │  • Publish to PyPI                               │          │
│  │  • Create GitHub Release                         │          │
│  └──────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 核心组件

#### 组件 1：Lint Pipeline

**职责**：代码质量检查，确保代码风格一致性和基本质量。

**工具链**：
- **Ruff**：Python linter 和 formatter（替代 flake8 + black + isort）
- **MyPy**：静态类型检查

**触发条件**：
- Push 到任何分支
- Pull Request

**配置文件**：
```yaml
# .github/workflows/lint.yml
name: Lint

on:
  push:
    branches: ['**']
  pull_request:

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install ruff mypy
          pip install -e .
      
      - name: Run Ruff
        run: ruff check .
      
      - name: Run MyPy
        run: mypy owlclaw --strict
```



#### 组件 2：Test Pipeline

**职责**：运行单元测试和集成测试，确保代码功能正确性。

**工具链**：
- **Pytest**：测试框架
- **pytest-cov**：覆盖率报告
- **pytest-asyncio**：异步测试支持
- **pytest-mock**：Mock 支持

**触发条件**：
- Push 到任何分支
- Pull Request

**配置文件**：
```yaml
# .github/workflows/test.yml
name: Test

on:
  push:
    branches: ['**']
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.10', '3.11', '3.12']
    
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: owlclaw_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
      
      - name: Run tests
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/owlclaw_test
        run: |
          pytest tests/ \
            --cov=owlclaw \
            --cov-report=xml \
            --cov-report=term \
            --cov-fail-under=80
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
          fail_ci_if_error: true
```

**关键点**：
- 多 Python 版本矩阵测试（3.10, 3.11, 3.12）
- PostgreSQL 服务容器用于集成测试
- 覆盖率要求 >80%
- 上传覆盖率报告到 Codecov

#### 组件 3：Build Pipeline

**职责**：构建 Python wheel 包，验证打包正确性。

**工具链**：
- **build**：PEP 517 构建工具
- **twine**：PyPI 上传工具（验证）

**触发条件**：
- Push 到 main 分支
- 创建 tag

**配置文件**：
```yaml
# .github/workflows/build.yml
name: Build

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install build tools
        run: pip install build twine
      
      - name: Build package
        run: python -m build
      
      - name: Check package
        run: twine check dist/*
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/
```



#### 组件 4：Release Pipeline

**职责**：自动化发布流程，包括版本管理、PyPI 发布和 GitHub Release。

**工具链**：
- **semantic-release**：自动版本管理
- **twine**：PyPI 上传
- **GitHub CLI**：创建 Release

**触发条件**：
- Push 到 main 分支（自动发布）
- 手动触发（workflow_dispatch）

**配置文件**：
```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  release:
    runs-on: ubuntu-latest
    if: "!contains(github.event.head_commit.message, 'chore(release)')"
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          token: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install python-semantic-release build twine
      
      - name: Semantic Release
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          semantic-release version
          semantic-release publish
      
      - name: Build package
        run: python -m build
      
      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
        run: twine upload dist/*
      
      - name: Create GitHub Release
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          VERSION=$(python -c "import owlclaw; print(owlclaw.__version__)")
          gh release create "v${VERSION}" \
            --title "Release v${VERSION}" \
            --notes-file CHANGELOG.md \
            dist/*
```

**关键点**：
- 使用 Conventional Commits 自动生成版本号
- 自动更新 CHANGELOG.md
- 发布到 PyPI
- 创建 GitHub Release 并附加构建产物

---

## 2. 实现细节

### 2.1 文件结构

```
.github/
├── workflows/
│   ├── lint.yml           # Lint 流水线
│   ├── test.yml           # Test 流水线
│   ├── build.yml          # Build 流水线
│   └── release.yml        # Release 流水线
└── dependabot.yml         # 依赖自动更新

.releaserc.json            # Semantic Release 配置
pyproject.toml             # 项目配置（包含 Ruff、MyPy 配置）
```

### 2.2 Ruff 配置

**配置文件**：`pyproject.toml`

```toml
[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
]
ignore = [
    "E501",  # line too long (handled by formatter)
]

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401"]  # unused imports in __init__.py

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

**关键点**：
- 行长度限制 100 字符
- 支持 Python 3.10+
- 启用常用规则集
- 自动格式化

### 2.3 MyPy 配置

**配置文件**：`pyproject.toml`

```toml
[tool.mypy]
python_version = "3.10"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_any_generics = true
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
strict_equality = true

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false
```

**关键点**：
- 严格模式
- 要求所有函数有类型注解
- 测试代码可以放宽类型检查

### 2.4 Pytest 配置

**配置文件**：`pyproject.toml`

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--strict-markers",
    "--strict-config",
    "--showlocals",
    "-ra",
]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "e2e: End-to-end tests",
    "slow: Slow tests",
]
asyncio_mode = "auto"

[tool.coverage.run]
source = ["owlclaw"]
omit = [
    "*/tests/*",
    "*/test_*.py",
    "*/__pycache__/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
    "@abstractmethod",
]
```

**关键点**：
- 自动发现测试
- 支持异步测试
- 覆盖率排除测试代码
- 标记不同类型的测试



### 2.5 Semantic Release 配置

**配置文件**：`.releaserc.json`

```json
{
  "branches": ["main"],
  "plugins": [
    "@semantic-release/commit-analyzer",
    "@semantic-release/release-notes-generator",
    [
      "@semantic-release/changelog",
      {
        "changelogFile": "CHANGELOG.md"
      }
    ],
    [
      "@semantic-release/exec",
      {
        "verifyReleaseCmd": "echo ${nextRelease.version} > .VERSION"
      }
    ],
    [
      "@semantic-release/git",
      {
        "assets": ["CHANGELOG.md", "pyproject.toml", ".VERSION"],
        "message": "chore(release): ${nextRelease.version} [skip ci]\n\n${nextRelease.notes}"
      }
    ],
    "@semantic-release/github"
  ]
}
```

**Commit 规范**：

遵循 Conventional Commits 规范：

- `feat:` - 新功能（触发 minor 版本）
- `fix:` - Bug 修复（触发 patch 版本）
- `docs:` - 文档更新
- `style:` - 代码格式（不影响功能）
- `refactor:` - 重构
- `perf:` - 性能优化
- `test:` - 测试相关
- `chore:` - 构建/工具相关
- `BREAKING CHANGE:` - 破坏性变更（触发 major 版本）

**示例**：
```
feat(agent-runtime): add heartbeat mechanism

Implement periodic heartbeat to check for pending events.

BREAKING CHANGE: Agent Runtime now requires Hatchet client
```

### 2.6 Dependabot 配置

**配置文件**：`.github/dependabot.yml`

```yaml
version: 2
updates:
  # Python dependencies
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
    reviewers:
      - "owlclaw-team"
    labels:
      - "dependencies"
      - "python"
  
  # GitHub Actions
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
    reviewers:
      - "owlclaw-team"
    labels:
      - "dependencies"
      - "github-actions"
```

**关键点**：
- 每周检查依赖更新
- 自动创建 PR
- 限制同时打开的 PR 数量
- 自动添加标签和审阅者

---

## 3. 质量门禁

### 3.1 Pull Request 检查

**必须通过的检查**：

1. **Lint**：
   - Ruff 检查通过
   - MyPy 类型检查通过

2. **Test**：
   - 所有测试通过
   - 覆盖率 ≥ 80%
   - 所有 Python 版本（3.10, 3.11, 3.12）通过

3. **Build**：
   - 包构建成功
   - Twine 检查通过

**分支保护规则**：

```yaml
# 在 GitHub 仓库设置中配置
main:
  required_status_checks:
    strict: true
    contexts:
      - "Lint"
      - "Test (3.10)"
      - "Test (3.11)"
      - "Test (3.12)"
      - "Build"
  required_pull_request_reviews:
    required_approving_review_count: 1
  enforce_admins: true
  restrictions: null
```

### 3.2 Release 检查

**发布前检查**：

1. 所有 PR 检查通过
2. 版本号符合语义化版本规范
3. CHANGELOG.md 自动生成
4. 构建产物验证通过

**发布后验证**：

1. PyPI 包可安装
2. GitHub Release 创建成功
3. 文档自动更新（如果有）

---

## 4. 本地开发工作流

### 4.1 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/owlclaw/owlclaw.git
cd owlclaw

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装开发依赖
pip install -e ".[dev]"

# 安装 pre-commit hooks
pre-commit install
```

### 4.2 Pre-commit Hooks

**配置文件**：`.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
  
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
```

**关键点**：
- 提交前自动运行 Ruff 和 MyPy
- 自动修复简单问题
- 防止提交大文件和合并冲突

### 4.3 本地测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_agent_runtime.py

# 运行带覆盖率的测试
pytest --cov=owlclaw --cov-report=html

# 运行特定标记的测试
pytest -m unit
pytest -m integration
pytest -m "not slow"

# 并行运行测试（需要 pytest-xdist）
pytest -n auto
```

### 4.4 本地 Lint

```bash
# 运行 Ruff 检查
ruff check .

# 自动修复
ruff check --fix .

# 格式化代码
ruff format .

# 运行 MyPy
mypy owlclaw
```

---

## 5. 监控和告警

### 5.1 CI 指标

**关键指标**：

1. **构建成功率**：
   - 目标：> 95%
   - 监控：GitHub Actions 统计

2. **测试覆盖率**：
   - 目标：> 80%
   - 监控：Codecov

3. **构建时间**：
   - Lint：< 2 分钟
   - Test：< 10 分钟
   - Build：< 5 分钟
   - Release：< 15 分钟

4. **依赖更新响应时间**：
   - 目标：< 7 天
   - 监控：Dependabot PR 状态

### 5.2 告警规则

**GitHub Actions 告警**：

1. **连续失败**：
   - 条件：同一 workflow 连续失败 3 次
   - 通知：Slack/Email

2. **覆盖率下降**：
   - 条件：覆盖率下降 > 5%
   - 通知：PR 评论 + Slack

3. **构建时间异常**：
   - 条件：构建时间 > 平均值 2 倍
   - 通知：Slack

4. **依赖安全漏洞**：
   - 条件：Dependabot 发现高危漏洞
   - 通知：立即通知 + 创建 Issue



---

## 6. 故障排查

### 6.1 常见问题

#### 问题 1：Lint 失败

**症状**：Ruff 或 MyPy 检查失败

**排查步骤**：
1. 本地运行 `ruff check .` 查看具体错误
2. 运行 `ruff check --fix .` 自动修复
3. 对于 MyPy 错误，检查类型注解
4. 如果是第三方库类型问题，添加 `# type: ignore` 注释

**示例**：
```python
# 错误：Missing type annotation
def process_data(data):  # ❌
    return data

# 正确：添加类型注解
def process_data(data: dict) -> dict:  # ✅
    return data
```

#### 问题 2：测试失败

**症状**：Pytest 测试失败

**排查步骤**：
1. 本地运行失败的测试：`pytest tests/test_xxx.py::test_yyy -v`
2. 检查测试日志和错误信息
3. 确认数据库连接（如果是集成测试）
4. 检查环境变量配置

**示例**：
```bash
# 运行单个测试并显示详细输出
pytest tests/test_agent_runtime.py::test_heartbeat -vv -s

# 使用 pdb 调试
pytest tests/test_agent_runtime.py::test_heartbeat --pdb
```

#### 问题 3：覆盖率不足

**症状**：Coverage < 80%

**排查步骤**：
1. 运行 `pytest --cov=owlclaw --cov-report=html`
2. 打开 `htmlcov/index.html` 查看未覆盖的代码
3. 添加缺失的测试用例
4. 对于不可测试的代码，添加 `# pragma: no cover`

**示例**：
```python
def main():
    if __name__ == "__main__":  # pragma: no cover
        # 这部分代码不需要测试覆盖
        run_app()
```

#### 问题 4：构建失败

**症状**：Build workflow 失败

**排查步骤**：
1. 检查 `pyproject.toml` 配置
2. 本地运行 `python -m build`
3. 运行 `twine check dist/*` 验证包
4. 检查依赖版本冲突

**示例**：
```bash
# 本地构建测试
python -m build
twine check dist/*

# 测试安装
pip install dist/owlclaw-*.whl
```

#### 问题 5：Release 失败

**症状**：Release workflow 失败

**排查步骤**：
1. 检查 commit message 是否符合 Conventional Commits
2. 验证 GitHub Token 权限
3. 检查 PyPI Token 配置
4. 查看 semantic-release 日志

**示例**：
```bash
# 本地测试 semantic-release
npx semantic-release --dry-run

# 检查 commit 格式
git log --oneline -10
```

### 6.2 调试技巧

#### 技巧 1：本地模拟 CI 环境

使用 `act` 工具本地运行 GitHub Actions：

```bash
# 安装 act
brew install act  # macOS
# 或 choco install act  # Windows

# 运行 lint workflow
act -j lint

# 运行 test workflow
act -j test
```

#### 技巧 2：查看 CI 日志

```bash
# 使用 GitHub CLI 查看最近的 workflow 运行
gh run list

# 查看特定 run 的日志
gh run view <run-id> --log

# 下载 artifacts
gh run download <run-id>
```

#### 技巧 3：重新运行失败的 Job

```bash
# 重新运行失败的 jobs
gh run rerun <run-id> --failed

# 重新运行所有 jobs
gh run rerun <run-id>
```

---

## 7. 最佳实践

### 7.1 Commit 规范

**好的 commit message**：
```
feat(agent-runtime): add memory search capability

- Implement vector search for long-term memory
- Add similarity threshold configuration
- Update MEMORY.md format

Closes #123
```

**不好的 commit message**：
```
fix bug
update code
wip
```

### 7.2 PR 规范

**PR 标题**：遵循 Conventional Commits

```
feat(governance): implement budget constraint
fix(ledger): resolve race condition in batch write
docs(readme): update installation instructions
```

**PR 描述模板**：

```markdown
## Description
Brief description of the changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests pass locally
```

### 7.3 测试规范

**测试命名**：

```python
# 好的测试命名
def test_budget_constraint_blocks_high_cost_capability_when_budget_exceeded():
    pass

def test_ledger_batch_write_retries_on_failure():
    pass

# 不好的测试命名
def test_budget():
    pass

def test_ledger():
    pass
```

**测试结构**：遵循 AAA 模式（Arrange-Act-Assert）

```python
@pytest.mark.asyncio
async def test_visibility_filter_applies_all_constraints():
    # Arrange
    ledger = MockLedger()
    filter = VisibilityFilter()
    filter.register_evaluator(BudgetConstraint(ledger, config))
    
    # Act
    filtered = await filter.filter_capabilities(capabilities, agent_id, context)
    
    # Assert
    assert len(filtered) == 1
    assert filtered[0].name == "low_cost_capability"
```

### 7.4 代码审查规范

**审查清单**：

1. **功能性**：
   - [ ] 代码实现了需求
   - [ ] 边界条件处理正确
   - [ ] 错误处理完善

2. **可读性**：
   - [ ] 命名清晰
   - [ ] 逻辑简洁
   - [ ] 注释充分

3. **可维护性**：
   - [ ] 遵循 SOLID 原则
   - [ ] 避免重复代码
   - [ ] 易于扩展

4. **性能**：
   - [ ] 无明显性能问题
   - [ ] 数据库查询优化
   - [ ] 缓存使用合理

5. **安全性**：
   - [ ] 输入验证
   - [ ] SQL 注入防护
   - [ ] 敏感数据处理

---

## 8. 参考文档

- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [Ruff 文档](https://docs.astral.sh/ruff/)
- [MyPy 文档](https://mypy.readthedocs.io/)
- [Pytest 文档](https://docs.pytest.org/)
- [Semantic Release 文档](https://semantic-release.gitbook.io/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Python Packaging User Guide](https://packaging.python.org/)

---

**维护者**：OwlClaw 开发团队  
**最后更新**：2026-02-22  
**版本**：1.0.0
