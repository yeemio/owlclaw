# OwlHub Production Rollout Runbook

Last updated: 2026-02-24

## Scope

This runbook covers Task 40.4 operational steps for OwlHub production rollout:

- Deploy Phase 1 index + Phase 3 API service.
- Monitor errors and performance after rollout.
- Verify index accessibility and CLI workflow.
- Provide Phase 2/3 rollout timeline checkpoints.

## Prerequisites

- GitHub environment secrets and vars are configured for `owlhub-production`.
- Kubernetes context points to production namespace.
- Public index URL is available (for example GitHub Pages `index.json`).
- Release tag exists (`vX.Y.Z`) for production workflow trigger.

## Deployment Steps

1. Trigger API deployment workflow:
   - Workflow: `.github/workflows/owlhub-api-deploy.yml`
   - Target: `production` (or tag push `refs/tags/v*`)
2. Confirm rollout:
   - `kubectl rollout status deployment/owlhub-api -n <production-namespace> --timeout=180s`
3. Confirm service endpoints:
   - `GET https://<hub-domain>/health`
   - `GET https://<hub-domain>/metrics`
4. Confirm public index:
   - `GET https://<index-domain>/index.json`

## Automated Release Gate

Use the release-gate script to generate an auditable report:

```powershell
poetry run python scripts/owlhub_release_gate.py `
  --api-base-url "https://hub.example.com" `
  --index-url "https://hub.example.com/index.json" `
  --query "skill" `
  --output "artifacts/owlhub-release-gate.json"
```

Expected result:
- Exit code `0`
- JSON report with all checks passed:
  - `api_health`
  - `api_metrics`
  - `index_access`
  - `cli_search`

## Rollout Timeline (Phase 2/3)

1. T0 (release day): Deploy Phase 1 index + Phase 3 API to production with smoke checks.
2. T0 + 1 day: Observe 24h metrics and error budget; verify no regression in search/install API.
3. T0 + 3 days: Enable broader CLI API-mode usage (progressive adoption).
4. T0 + 7 days: Review performance and moderation workload; decide on Phase 3 DB scaling actions.
5. T0 + 14 days: Post-release review and backlog sync for next architecture iteration.

## Rollback

1. Roll API image to previous known-good tag via `kubectl set image`.
2. Re-run release gate script against rollback target.
3. Freeze new publish operations until incident closure.
