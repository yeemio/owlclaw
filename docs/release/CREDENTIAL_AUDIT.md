# Release Credential Audit

- Date: 2026-02-26
- Scope: `.github/workflows/release.yml` (release path)

## Secrets and Tokens in Use

1. `secrets.GITHUB_TOKEN`
   - Used for checkout, semantic-release metadata publish, and GitHub release creation.
   - Current job permissions: `contents: write`, `id-token: write`, `attestations: write`.
2. OIDC identity token (`id-token: write`)
   - Used by `pypa/gh-action-pypi-publish@release/v1` for Trusted Publishing.
   - Replaces long-lived `PYPI_TOKEN`/`TEST_PYPI_TOKEN` in workflow runtime.
3. Attestation permission (`attestations: write`)
   - Used by `actions/attest-build-provenance@v2` to publish provenance metadata.

## Least-Privilege Assessment

- `GITHUB_TOKEN` usage is limited to repository release metadata operations.
- No long-lived PyPI token is required in workflow steps after OIDC migration.
- No hardcoded credentials detected in release workflow.

## Recommended Hardening

1. Keep `permissions` scoped to `contents/id-token/attestations` only.
2. Restrict Trusted Publisher subject in PyPI/TestPyPI to this repository + workflow.
3. Keep tagged-release trigger and branch protections aligned with required checks.

