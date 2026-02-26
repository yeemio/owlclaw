# Cross-language Acceptance

Last updated: 2026-02-26

## Verification Commands

1. Structural baseline:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_cross_lang.ps1 -Strict
```

2. Response field alignment:

```bash
python scripts/cross_lang/compare_response_fields.py \
  --java-json examples/cross_lang/fixtures/java_trigger_response.json \
  --curl-json examples/cross_lang/fixtures/curl_trigger_response.json
```

## Results

1. Baseline file check: pass
2. Response field alignment: pass
3. Java build execution: pending (Maven unavailable in current environment)

## Thresholds

1. JDK baseline: 17
2. Core scenario pass rate target: 100%
3. Local average response latency target: <= 2s

## Acceptance Matrix

| Scenario | Java | curl | Evidence | Pass |
|---|---|---|---|---|
| Trigger agent | [ ] | [x] | `trigger_agent.sh` + fixture contract | [x] |
| Query status | [ ] | [x] | `query_status.sh` + fixture contract | [x] |
| Error handling | [ ] | [x] | `error_scenario.sh` + fixture contract | [x] |
| Field consistency | [x] | [x] | `compare_response_fields.py` output | [x] |

## T+0 to T+15 Tabletop

1. T+0: verification failure detected and rollout blocked.
2. T+3: classify root cause (contract, sample, environment).
3. T+6: fix sample or contract and rerun checks.
4. T+10: add failing case to regression set.
5. T+15: publish updated golden path and result notes.
