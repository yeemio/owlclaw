# Release Runbook

This runbook covers external steps that cannot be completed from repository code alone.

## 1. Configure GitHub Secrets

Required repository secrets:

- `PYPI_TOKEN` (production PyPI token)
- `TEST_PYPI_TOKEN` (optional, for TestPyPI dry-run)

Path:

1. GitHub repository -> `Settings` -> `Secrets and variables` -> `Actions`
2. Create or rotate tokens with least privilege

Verification (CLI):

```bash
gh auth status
gh secret list -R yeemio/owlclaw
```

Expected: secret names include `PYPI_TOKEN` and `TEST_PYPI_TOKEN`.

## 2. Dry-run To TestPyPI

Preferred path: trigger release workflow manually with TestPyPI target:

```bash
gh workflow run release.yml -R yeemio/owlclaw -f target=testpypi
```

Inspect latest run:

```bash
gh run list -R yeemio/owlclaw --workflow release.yml --limit 5
gh run view <RUN_ID> -R yeemio/owlclaw
```

If run fails at token validation, return to step 1 and configure missing secrets.

Alternative manual upload:

```bash
python -m build
twine upload --repository-url https://test.pypi.org/legacy/ dist/*
```

Verify installation:

```bash
python -m venv .venv-release-check
.venv-release-check\Scripts\activate
pip install -i https://test.pypi.org/simple/ owlclaw==0.1.0
owlclaw --version
owlclaw skill list
```

## 3. Production Release

Tag-driven workflow trigger:

```bash
git tag v0.1.0
git push origin v0.1.0
```

Workflow: `.github/workflows/release.yml`

Optional manual trigger to production:

```bash
gh workflow run release.yml -R yeemio/owlclaw -f target=pypi
```

Expected behavior:

1. Install deps and run tests
2. Build package
3. Publish to PyPI
4. Create GitHub Release from `CHANGELOG.md`

## 4. Post-release Verification

```bash
python -m venv .venv-prod-check
.venv-prod-check\Scripts\activate
pip install owlclaw
owlclaw --version
owlclaw skill list
```

## 5. Community Settings

Current state (2026-02-25):

1. Discussions enabled
2. Repository visibility: Public
3. Topics and Description configured
