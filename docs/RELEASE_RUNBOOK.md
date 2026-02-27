# Release Runbook

This runbook covers external steps that cannot be completed from repository code alone.

## 1. Configure Trusted Publishing (OIDC)

Preferred path: use PyPI/TestPyPI Trusted Publisher (no long-lived token in workflow).

Required external setup:

1. PyPI/TestPyPI project settings -> Trusted Publishers
2. Bind to repository `yeemio/owlclaw` and workflow `.github/workflows/release.yml`
3. Restrict to expected trigger (tag/manual release)

Detailed field-level setup guide:

- `docs/release/TRUSTED_PUBLISHER_SETUP.md`

Validation:

```bash
gh workflow view release.yml -R yeemio/owlclaw
```

Legacy fallback (not preferred): token-based upload via `PYPI_TOKEN`/`TEST_PYPI_TOKEN`.

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

Run OIDC preflight diagnostics (workflow + branch protection + ruleset + 403 blocker detection):

```bash
poetry run python scripts/release_oidc_preflight.py --repo yeemio/owlclaw --run-id <RUN_ID>
```

If run fails at OIDC validation, verify Trusted Publisher subject mapping first.

Verify installation:

```bash
python -m venv .venv-release-check
.venv-release-check\Scripts\activate
pip install -i https://test.pypi.org/simple/ owlclaw==0.1.0
owlclaw --version
owlclaw skill list
```

## 3. Production Release (PyPI)

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
3. Publish to PyPI via OIDC Trusted Publishing
4. Attest build provenance
5. Smoke install `owlclaw==<version>`
6. Upload release report artifact
7. Create GitHub Release from `CHANGELOG.md`

## 4. Post-release Verification

```bash
python -m venv .venv-prod-check
.venv-prod-check\Scripts\activate
pip install owlclaw
owlclaw --version
owlclaw skill list
```

## 5. Rollback / Retry

If publish or smoke install fails:

1. Stop follow-up release jobs.
2. Check release report artifact and workflow logs.
3. Fix configuration issue (OIDC subject / package metadata / install index).
4. Re-run workflow from failed job.
5. Announce status in release channel and attach incident id.

## 6. Community Settings

Current state (2026-02-25):

1. Discussions enabled
2. Repository visibility: Public
3. Topics and Description configured
