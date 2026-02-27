# Release OIDC Preflight Report

> generated_at: 2026-02-27 06:42:23Z
> repo: yeemio/owlclaw
> run_id: 22475093887
> status: BLOCKED

## Checks

- workflow_oidc_publish: PASS
- main_branch_protection: PASS
- release_ruleset: PASS
- trusted_publisher_blocker: DETECTED

## Findings

- latest release run indicates TestPyPI 403 Forbidden (Trusted Publisher binding missing)

## Manual Trusted Publisher Checklist

1. TestPyPI project -> Publishing -> Trusted Publishers -> Add.
2. PyPI project -> Publishing -> Trusted Publishers -> Add.
3. Repository: `yeemio/owlclaw`.
4. Workflow filename: `.github/workflows/release.yml`.
5. Environment name: leave empty unless workflow explicitly uses one.
6. Re-run `gh workflow run release.yml -f target=testpypi`.
