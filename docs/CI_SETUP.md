# CI Setup Guide

本文档覆盖 `ci-setup` spec 的运维配置、质量门禁与故障排查要求。

## 1. Workflows 概览

- `lint.yml`: Ruff + MyPy
- `test.yml`: Pytest + Coverage + Codecov（Python 3.10/3.11/3.12）
- `build.yml`: `python -m build` + `twine check`
- `release.yml`: semantic release + PyPI + GitHub Release

## 2. GitHub Secrets

必须在仓库 Settings -> Secrets and variables -> Actions 中配置：

- `PYPI_TOKEN`: PyPI API token（`__token__` 模式）

可选（通常已内置）：

- `GITHUB_TOKEN`: GitHub 自动注入

## 3. Branch Protection 建议

针对 `main` 分支开启保护：

- Require a pull request before merging
- Require approvals: at least 1 reviewer
- Require status checks to pass before merging
- Required checks:
  - `Lint / lint`
  - `Test / test (3.10)`
  - `Test / test (3.11)`
  - `Test / test (3.12)`
  - `Build / build`

## 4. CI 质量指标与告警

关键指标：

- 构建成功率 > 95%
- 覆盖率 >= 80%
- 单次 CI 总时长 < 20 分钟

告警建议：

- 连续 3 次 workflow 失败
- 覆盖率较主分支下降 > 2%
- 构建时间增长 > 50%
- Dependabot 报告高危漏洞

## 5. 常见问题排查

### 5.1 Lint 失败

症状：`ruff check` 报错。  
排查：

1. 本地执行 `poetry run ruff check .`
2. 可自动修复项执行 `poetry run ruff check . --fix`
3. 再执行 `poetry run ruff format .`

### 5.2 MyPy 失败

症状：类型不匹配或缺失注解。  
排查：

1. 本地执行 `poetry run mypy owlclaw/`
2. 优先补充函数签名与返回类型
3. 第三方无类型包补充 `# type: ignore[import-untyped]`

### 5.3 Test 失败

症状：pytest 失败或数据库连接失败。  
排查：

1. 本地执行 `poetry run pytest -q`
2. 数据库相关测试检查 `OWLCLAW_DATABASE_URL`
3. 确认测试未依赖外部不可用服务

### 5.4 覆盖率不足

症状：`--cov-fail-under=80` 未通过。  
排查：

1. 本地执行 `poetry run pytest --cov=owlclaw --cov-report=term`
2. 优先补关键模块单元测试
3. 校验是否误将新代码放进 omit 范围

### 5.5 Build/Release 失败

症状：`python -m build`、`twine check` 或发布失败。  
排查：

1. 本地执行 `python -m build` 与 `twine check dist/*`
2. 检查 `PYPI_TOKEN` 是否有效
3. 检查 `CHANGELOG.md` 与版本号变更是否一致

## 6. 本地模拟与调试技巧

### 6.1 act 本地模拟

```bash
act -W .github/workflows/lint.yml
act -W .github/workflows/test.yml
```

### 6.2 gh CLI 调试

```bash
gh run list --limit 20
gh run view <run-id> --log-failed
gh run rerun <run-id>
```

## 6.3 远端端到端验收（Task 11.1）

新建测试分支并提交后，使用以下流程验证四条 workflow：

```bash
git checkout -b ci-smoke-check
git push origin ci-smoke-check
gh pr create --title "test(ci): smoke validation" --body "CI smoke validation"
gh run list --limit 20
gh run view <run-id> --log-failed
```

验收通过标准：

- `Lint`、`Test (3.10/3.11/3.12)`、`Build` 全部通过
- `Release` 不在 PR 场景触发

## 7. Commit 与 PR 规范

Conventional Commits：

- `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`
- Breaking change 通过 footer：`BREAKING CHANGE: <description>`

示例：

- `feat(cli): add migrate scan output-mode`
- `fix(governance): prevent rate-limit overflow`
- `chore(release): 0.2.0`

PR 标题建议：

- `<type>(<scope>): <short summary>`

PR 描述建议包含：

- 变更目的
- 影响范围
- 验证命令与结果
- 风险与回滚方案

## 8. 测试规范（CI 角度）

- 测试文件：`test_*.py`
- 测试函数：`test_*`
- 建议结构：Arrange / Act / Assert
- 异步测试使用 `pytest.mark.asyncio`

## 9. Code Review 清单

- 功能正确性：需求是否满足
- 可读性：命名/结构是否清晰
- 可维护性：边界与抽象是否稳定
- 性能：是否引入明显低效路径
- 安全：是否泄漏密钥/明文凭证
