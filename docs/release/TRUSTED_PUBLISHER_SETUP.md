# Trusted Publisher Setup (PyPI/TestPyPI)

> last_updated: 2026-02-27  
> scope: `yeemio/owlclaw` release workflow OIDC binding

## 1. TestPyPI 配置

1. 打开 TestPyPI 项目页面：`owlclaw`。
2. 进入 `Publishing` -> `Add a trusted publisher`。
3. 按以下字段填写：
   - Owner: `yeemio`
   - Repository name: `owlclaw`
   - Workflow filename: `.github/workflows/release.yml`
   - Environment name: 留空（当前 workflow 未使用 environment）
4. 保存后执行：
   - `gh workflow run release.yml -f target=testpypi`
5. 验证 run 不再在 `Publish to TestPyPI` 阶段报 `403 Forbidden`。

## 2. PyPI 配置

1. 打开 PyPI 项目页面：`owlclaw`。
2. 进入 `Publishing` -> `Add a trusted publisher`。
3. 填写与 TestPyPI 相同的仓库与 workflow 字段。
4. 保存后执行：
   - `gh workflow run release.yml -f target=pypi`
5. 验证发布、attestation、smoke install、GitHub Release 全链路完成。

## 3. 自动化预检

在仓库根目录执行：

```powershell
poetry run python scripts/release_oidc_preflight.py --repo yeemio/owlclaw --run-id <RUN_ID>
```

报告输出：

- `docs/release/reports/release-oidc-preflight-latest.md`

退出码说明：

- `0`: preflight ready（可继续发布）
- `2`: 仓库侧基线未满足（workflow/protection/ruleset）
- `3`: 检测到 TestPyPI `403 Forbidden`（Trusted Publisher 仍未生效）
