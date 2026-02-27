# OwlClaw Governance Gate Policy

> Scope: CI governance gate policy for protocol compatibility and error-model consistency.
> Status: Active baseline.
> Last Updated: 2026-02-26

---

## 1. Gate Stages

| Stage | Behavior | Merge impact |
|---|---|---|
| Stage A (`warning`) | Report diff and risk; no hard fail. | pass with warning |
| Stage B (`soft-block`) | Breaking requires exemption ticket. | conditional pass |
| Stage C (`blocking`) | Breaking without migration package is blocked. | fail |

Current policy: Stage B.

---

## 2. Gate Decision Rules

Input:

- `change_level`: `compatible|additive|breaking`
- `migration_plan`: optional
- `exemption_ticket`: optional

Decision:

1. `compatible` -> `pass`
2. `additive` -> `pass`
3. `breaking` + `migration_plan` -> `pass`
4. `breaking` + `exemption_ticket` -> `warn` + audit log
5. `breaking` with neither -> `block`

---

## 3. Quantitative Thresholds

### 3.1 CI gate runtime SLO

- Target: `< 60s` per gate run.
- Hard timeout: `90s`.

### 3.2 Governance quality thresholds

- Breaking leak rate target: `0` in drill samples.
- Mapping consistency coverage: `100%` for canonical high-risk codes.
- Exemption audit write success: `100%` when exemption path used.

---

## 4. Acceptance Matrix (Bound to Artifacts)

| Scenario | Expected | Artifact |
|---|---|---|
| additive diff | `change_level=additive`, decision `pass` | CI log + JSON report |
| breaking without migration | decision `block` | CI log + JSON report |
| breaking with exemption | decision `warn` + audit row | audit JSONL + drill report |
| error-model consistency | tests pass | pytest report |
| gate policy drift check | CI config test pass | pytest report |

Template location: `docs/protocol/templates/ACCEPTANCE_MATRIX_TEMPLATE.md`

---

## 5. Exemption Audit Policy

Exemption is allowed only when:

- issue is low-frequency and low-blast-radius, and
- rollback is immediate and verified.

Mandatory evidence:

- exemption ticket id
- approver
- expiry date
- rollback owner

Template location:

- `docs/protocol/templates/EXEMPTION_APPROVAL_TEMPLATE.md`

---

## 6. T+0 ~ T+15 Incident Playbook

- `T+0`: Freeze merge queue and mark protocol gate incident.
- `T+3`: Export diff report, gate decision payload, CI trace.
- `T+6`: Switch to strict fallback policy (block on uncertain diff).
- `T+10`: Patch rule and replay latest 10 changes.
- `T+15`: Restore policy and publish postmortem with incident id.

---

## 7. Drill Execution

Use:

```bash
poetry run python scripts/protocol_governance_drill.py
```

Outputs:

- `docs/protocol/reports/governance-drill-latest.md`
- `docs/protocol/reports/governance-gate-audit.jsonl`

---

## 8. Related Documents

- `docs/protocol/VERSIONING.md`
- `docs/protocol/COMPATIBILITY_POLICY.md`
- `docs/protocol/ERROR_MODEL.md`

