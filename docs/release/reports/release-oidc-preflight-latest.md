# Release OIDC Preflight Report

> generated_at: 2026-03-02 08:52:46Z
> repo: yeemio/owlclaw
> run_id: 22477795502
> status: BLOCKED

## Checks

- workflow_oidc_publish: PASS
- main_branch_protection: FAIL
- release_ruleset: PASS
- trusted_publisher_blocker: DETECTED

## Findings

- main branch protection does not enforce strict Lint/Test/Build checks
- latest release run indicates TestPyPI 403 Forbidden (Trusted Publisher binding missing)
- failed to fetch api repos/yeemio/owlclaw/branches/main/protection: gh: Branch not protected (HTTP 404)

## Manual Trusted Publisher Checklist

1. TestPyPI project -> Publishing -> Trusted Publishers -> Add.
2. PyPI project -> Publishing -> Trusted Publishers -> Add.
3. Repository: `yeemio/owlclaw`.
4. Workflow filename: `.github/workflows/release.yml`.
5. Environment name: leave empty unless workflow explicitly uses one.
6. Re-run `gh workflow run release.yml -f target=testpypi`.
