# Release Supply Chain Playbook

Last updated: 2026-02-26

## Scope

This playbook defines thresholds, acceptance matrix, and T+0~T+15 response flow for release supply chain operations.

## Thresholds

1. TestPyPI publish success rate target: >= 99% (last 20 runs)
2. Publish-to-install smoke total time target: <= 5 minutes
3. Provenance/attestation archive completeness: 100%

## Acceptance Matrix

| Scenario | Check | Evidence | Pass |
|---|---|---|---|
| TestPyPI publish | OIDC publishing flow executes | Workflow logs | [ ] |
| PyPI publish | Package install smoke passes | Smoke logs | [ ] |
| Provenance | Attestation is generated and archived | Attestation artifact | [ ] |
| Failure rollback | Rollback path is executable | Drill logs | [ ] |

## Current Evidence Snapshot

1. Run `22446541468` (main, 2026-02-26) failed at TestPyPI upload with `HTTP 403` and empty `TWINE_PASSWORD`.
2. This confirms main branch still follows legacy token-based publishing path.
3. OIDC-based workflow baseline has been prepared in coding branch and awaits review/merge.

## T+0 to T+15 Response Script

1. T+0: Release failure detected; block downstream publish steps.
2. T+3: Identify failure stage (OIDC auth, upload, smoke, provenance).
3. T+6: Replay in TestPyPI and verify platform configuration.
4. T+10: Execute rollback or retry decision.
5. T+15: Publish status update and remediation plan.
