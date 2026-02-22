# Implementation Plan: CI 配置

## Overview

建立完整的 CI/CD 流水线，包括 Lint、Test、Build、Release 四个核心流水线，以及配套的质量门禁、本地开发工作流和监控告警机制。

## Tasks

- [ ] 1. 配置项目工具链基础设置
  - [ ] 1.1 配置 Ruff（lint + format）
    - 在 `pyproject.toml` 中添加 `[tool.ruff]` 配置
    - 设置 line-length=100, target-version="py310"
    - 配置 lint 规则（E, W, F, I, B, C4, UP）
    - 配置 per-file-ignores（__init__.py 允许 F401）
    - 配置 format 规则（quote-style, indent-style）
    - _Requirements: FR-1, FR-2_
  
  - [ ] 1.2 配置 MyPy（类型检查）
    - 在 `pyproject.toml` 中添加 `[tool.mypy]` 配置
    - 启用 strict 模式和所有严格检查选项
    - 配置 tests 目录的类型检查豁免
    - _Requirements: FR-1, FR-2_
  
  - [ ] 1.3 配置 Pytest（测试框架）
    - 在 `pyproject.toml` 中添加 `[tool.pytest.ini_options]` 配置
    - 设置 testpaths, python_files, python_classes, python_functions
    - 配置 markers（unit, integration, e2e, slow）
    - 设置 asyncio_mode="auto"
    - _Requirements: FR-1, NFR-1_
  
  - [ ] 1.4 配置 Coverage（覆盖率）
    - 在 `pyproject.toml` 中添加 `[tool.coverage.run]` 和 `[tool.coverage.report]` 配置
    - 设置 source=["owlclaw"], omit 测试文件
    - 配置 exclude_lines（pragma: no cover, TYPE_CHECKING 等）
    - _Requirements: NFR-1_

- [ ] 2. 创建 GitHub Actions 工作流
  - [ ] 2.1 创建 Lint Pipeline
    - 创建 `.github/workflows/lint.yml` 文件
    - 配置触发条件：push 到所有分支 + pull_request
    - 设置 Python 3.11 环境
    - 添加步骤：checkout, setup-python, install dependencies
    - 添加步骤：运行 `ruff check .`
    - 添加步骤：运行 `mypy owlclaw --strict`
    - _Requirements: FR-1, FR-2_
  
  - [ ]* 2.2 编写 Lint Pipeline 单元测试
    - 测试 Ruff 配置正确性
    - 测试 MyPy 配置正确性
    - _Requirements: FR-1_
  
  - [ ] 2.3 创建 Test Pipeline
    - 创建 `.github/workflows/test.yml` 文件
    - 配置触发条件：push 到所有分支 + pull_request
    - 配置 matrix strategy：Python 3.10, 3.11, 3.12
    - 配置 PostgreSQL service container（postgres:16）
    - 设置环境变量：DATABASE_URL
    - 添加步骤：checkout, setup-python, install dependencies
    - 添加步骤：运行 pytest 并生成覆盖率报告（--cov-fail-under=80）
    - 添加步骤：上传覆盖率到 Codecov
    - _Requirements: FR-1, NFR-1_
  
  - [ ]* 2.4 编写 Test Pipeline 集成测试
    - 测试多版本 Python 矩阵
    - 测试 PostgreSQL 服务容器连接
    - 测试覆盖率门禁
    - _Requirements: NFR-1_
  
  - [ ] 2.5 创建 Build Pipeline
    - 创建 `.github/workflows/build.yml` 文件
    - 配置触发条件：push 到 main 分支 + tags v*
    - 设置 Python 3.11 环境
    - 添加步骤：checkout, setup-python, install build tools
    - 添加步骤：运行 `python -m build`
    - 添加步骤：运行 `twine check dist/*`
    - 添加步骤：上传 artifacts（dist/）
    - _Requirements: FR-1_
  
  - [ ]* 2.6 编写 Build Pipeline 验证测试
    - 测试包构建成功
    - 测试 twine check 通过
    - _Requirements: FR-1_
  
  - [ ] 2.7 创建 Release Pipeline
    - 创建 `.github/workflows/release.yml` 文件
    - 配置触发条件：push 到 main 分支 + workflow_dispatch
    - 添加条件：跳过包含 'chore(release)' 的 commit
    - 配置 checkout with fetch-depth=0 和 token
    - 设置 Python 3.11 环境
    - 添加步骤：安装 python-semantic-release, build, twine
    - 添加步骤：运行 semantic-release version 和 publish
    - 添加步骤：构建包并发布到 PyPI（使用 PYPI_TOKEN）
    - 添加步骤：创建 GitHub Release（使用 gh CLI）
    - _Requirements: FR-1_
  
  - [ ]* 2.8 编写 Release Pipeline 端到端测试
    - 测试版本号生成逻辑
    - 测试 CHANGELOG 生成
    - _Requirements: FR-1_

- [ ] 3. Checkpoint - 验证基础工作流
  - 确保所有 workflow 文件语法正确，本地可以通过 act 工具验证，询问用户是否有问题。

- [ ] 4. 配置 Semantic Release
  - [ ] 4.1 创建 Semantic Release 配置文件
    - 创建 `.releaserc.json` 文件
    - 配置 branches: ["main"]
    - 配置 plugins：commit-analyzer, release-notes-generator
    - 配置 changelog plugin（changelogFile: "CHANGELOG.md"）
    - 配置 exec plugin（写入 .VERSION 文件）
    - 配置 git plugin（提交 CHANGELOG.md, pyproject.toml, .VERSION）
    - 配置 github plugin
    - _Requirements: FR-1_
  
  - [ ] 4.2 更新项目文档说明 Commit 规范
    - 在 README.md 或 CONTRIBUTING.md 中添加 Conventional Commits 说明
    - 列出所有 commit types（feat, fix, docs, style, refactor, perf, test, chore）
    - 说明 BREAKING CHANGE 的使用
    - 提供 commit message 示例
    - _Requirements: FR-2_

- [ ] 5. 配置本地开发工作流
  - [ ] 5.1 创建 Pre-commit Hooks 配置
    - 创建 `.pre-commit-config.yaml` 文件
    - 配置 ruff-pre-commit hook（ruff + ruff-format）
    - 配置 mypy hook
    - 配置 pre-commit-hooks（trailing-whitespace, end-of-file-fixer, check-yaml, check-added-large-files, check-merge-conflict）
    - _Requirements: FR-2, NFR-1_
  
  - [ ]* 5.2 编写 Pre-commit Hooks 测试
    - 测试 hooks 配置正确性
    - 测试 hooks 可以正常运行
    - _Requirements: NFR-1_
  
  - [ ] 5.3 更新开发文档
    - 在 README.md 或 CONTRIBUTING.md 中添加开发环境设置说明
    - 说明如何安装 pre-commit hooks（`pre-commit install`）
    - 说明本地测试命令（pytest, ruff, mypy）
    - 提供本地调试技巧
    - _Requirements: FR-2, NFR-1_

- [ ] 6. 配置依赖管理
  - [ ] 6.1 创建 Dependabot 配置
    - 创建 `.github/dependabot.yml` 文件
    - 配置 pip package-ecosystem（weekly, open-pull-requests-limit=10）
    - 配置 github-actions package-ecosystem（weekly, open-pull-requests-limit=5）
    - 设置 reviewers 和 labels
    - _Requirements: FR-2_
  
  - [ ] 6.2 配置 GitHub Secrets
    - 文档化需要配置的 Secrets：PYPI_TOKEN
    - 在 README.md 或部署文档中说明如何配置
    - _Requirements: FR-1_

- [ ] 7. Checkpoint - 验证完整工作流
  - 确保所有配置文件已创建，询问用户是否需要调整配置或有其他问题。

- [ ] 8. 配置质量门禁
  - [ ] 8.1 文档化分支保护规则
    - 在 docs/ 目录创建 CI_SETUP.md 或更新现有文档
    - 说明需要在 GitHub 仓库设置中配置的分支保护规则
    - 列出 required_status_checks：Lint, Test (3.10/3.11/3.12), Build
    - 说明 required_pull_request_reviews 设置
    - _Requirements: FR-2, NFR-1_
  
  - [ ] 8.2 文档化质量指标
    - 在文档中说明 CI 关键指标（构建成功率 >95%, 覆盖率 >80%, 构建时间限制）
    - 说明告警规则（连续失败、覆盖率下降、构建时间异常、安全漏洞）
    - _Requirements: NFR-1_

- [ ] 9. 创建故障排查文档
  - [ ] 9.1 编写常见问题排查指南
    - 在文档中添加常见问题章节
    - 包含：Lint 失败、测试失败、覆盖率不足、构建失败、Release 失败
    - 每个问题提供症状、排查步骤、示例代码
    - _Requirements: NFR-1_
  
  - [ ] 9.2 编写调试技巧文档
    - 说明如何使用 act 工具本地模拟 CI
    - 说明如何使用 gh CLI 查看日志和重新运行 jobs
    - 提供实用命令示例
    - _Requirements: NFR-1_

- [ ] 10. 编写最佳实践文档
  - [ ] 10.1 文档化 Commit 和 PR 规范
    - 提供好的和不好的 commit message 对比示例
    - 提供 PR 标题和描述模板
    - _Requirements: FR-2_
  
  - [ ] 10.2 文档化测试规范
    - 说明测试命名规范
    - 说明测试结构（AAA 模式）
    - 提供测试代码示例
    - _Requirements: NFR-1_
  
  - [ ] 10.3 文档化代码审查规范
    - 提供代码审查清单（功能性、可读性、可维护性、性能、安全性）
    - _Requirements: FR-2_

- [ ] 11. 集成与验证
  - [ ] 11.1 端到端验证
    - 创建测试 PR 验证所有 workflows 正常运行
    - 验证 Lint Pipeline 可以检测代码问题
    - 验证 Test Pipeline 可以运行测试并报告覆盖率
    - 验证 Build Pipeline 可以构建包
    - 验证 pre-commit hooks 正常工作
    - _Requirements: FR-1, FR-2, NFR-1_
  
  - [ ]* 11.2 编写集成测试
    - 测试完整的 CI/CD 流程
    - 测试质量门禁生效
    - _Requirements: NFR-1_
  
  - [ ] 11.3 验证文档完整性
    - 检查所有文档是否完整
    - 验证文档中的命令和示例可以正常运行
    - _Requirements: FR-2, NFR-1_

- [ ] 12. Final Checkpoint - 完整验收
  - 确保所有测试通过，所有文档完整，询问用户是否满意或需要调整。

## Notes

- 任务标记 `*` 为可选任务，可以跳过以加快 MVP 交付
- 每个任务都引用了具体的需求条款以保证可追溯性
- Checkpoint 任务确保增量验证
- 所有配置文件遵循项目现有规范和最佳实践
- 文档使用中文以保持与现有文档一致
