# Java Golden Path

> Scope: reproducible Java + curl onboarding path for OwlClaw API.
> Last Updated: 2026-02-26

## 1. Environment Baseline

- JDK: `17`
- Build tool: Maven `3.9+`
- API endpoint baseline: `http://localhost:8000`

## 2. Core Scenarios

1. Trigger Agent
2. Query Status
3. Error Handling (invalid payload)

Java assets:

- `examples/cross_lang/java/src/main/java/dev/owlclaw/examples/OwlClawApiClient.java`

curl assets:

- `examples/cross_lang/curl/trigger_agent.sh`
- `examples/cross_lang/curl/query_status.sh`
- `examples/cross_lang/curl/error_case.sh`

## 3. Reliability Defaults

- request timeout configured in Java client
- retry wrapper for transient IO failures
- idempotency key header for trigger requests

## 4. Validation

Run:

```powershell
pwsh -File scripts/verify_cross_lang.ps1
```

Expected checks:

- java project files exist
- java trigger/query methods exist
- curl parity scripts exist

## 5. Thresholds and Acceptance Matrix

Thresholds:

- JDK 17 baseline enforced
- local scenario response target: `<= 2s`
- core scenario pass rate: `100%`

Acceptance matrix:

| Scenario | Java | curl | Evidence |
|---|---|---|---|
| Trigger | yes | yes | verification log |
| Query | yes | yes | verification log |
| Error handling | yes | yes | verification log |
| Retry + idempotency | yes | yes | client + curl script config |

## 6. T+0 ~ T+15 Playbook

- `T+0`: cross-language verification fails, stop rollout.
- `T+3`: classify contract drift vs sample bug vs environment issue.
- `T+6`: patch sample/script and rerun.
- `T+10`: add regression assertion for failure mode.
- `T+15`: publish updated guidance and recovery note.

