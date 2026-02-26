# OpenAPI Breaking Rules Mapping

> Scope: Contract-testing rule map for OpenAPI diff classification.
> Last Updated: 2026-02-26

## 1. Mapping Rules

| OpenAPI change | Level | Reason |
|---|---|---|
| Remove existing path | breaking | existing clients fail |
| Remove operation method from path | breaking | call target removed |
| Remove response field used by clients | breaking | parse/runtime failure risk |
| Change field type | breaking | schema incompatibility |
| Change required `false -> true` | breaking | request becomes invalid |
| Add new optional field | additive | backward compatible |
| Add new endpoint | additive | does not break old clients |
| Description/example update only | compatible | no behavior change |

## 2. Gate Policy Link

These mappings are enforced by:

- `scripts/contract_diff.py`
- PR gate workflow: `.github/workflows/contract-gate.yml`

## 3. Escalation

If rule classification is ambiguous:

1. classify as `breaking`
2. require migration plan or exemption ticket
3. log decision in governance audit trail

