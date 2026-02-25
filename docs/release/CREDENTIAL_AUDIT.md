# Release Credential Audit

- Date: 2026-02-25
- Scope: `.github/workflows/release.yml` (release path)

## Secrets and Tokens in Use

1. `secrets.GITHUB_TOKEN`
   - Used for checkout, semantic-release metadata publish, and GitHub release creation.
   - Current job permissions: `contents: write`.
2. `secrets.PYPI_TOKEN`
   - Used only in Twine publish step as `TWINE_PASSWORD`.
   - Username fixed to `__token__` (token-based auth).

## Least-Privilege Assessment

- `GITHUB_TOKEN` usage is limited to repository release metadata operations.
- `PYPI_TOKEN` is only exposed in the publish step env, not echoed in logs.
- No hardcoded credentials detected in release workflow.

## Recommended Hardening

1. Keep `permissions` scoped to `contents: write` only (already applied).
2. Rotate `PYPI_TOKEN` periodically and enforce short-lived credentials where possible.
3. Restrict publish workflow trigger to tagged releases if release governance requires stronger gate.

