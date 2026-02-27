# OwlClaw Protocol Compatibility Policy

> Scope: Compatibility governance for API and MCP contracts.
> Status: Active baseline (warning gate, planned blocking upgrade).
> Last Updated: 2026-02-26

---

## 1. Change Levels

Contract changes are classified into three levels:

- `compatible`: internal or non-behavioral change.
- `additive`: backward-compatible extension.
- `breaking`: existing client behavior can fail or change.

When multiple changes exist in one PR, the strictest level wins.

---

## 2. Classification Table

| Change example | API impact | MCP impact | Level |
|---|---|---|---|
| Doc text only / comments only | None | None | compatible |
| Add optional response field | Safe (old clients ignore) | Safe | additive |
| Add optional request field with default behavior unchanged | Safe | Safe | additive |
| Add new endpoint/tool without changing existing ones | Safe | Safe | additive |
| Remove endpoint/tool | Existing calls fail | Existing calls fail | breaking |
| Rename field used by clients | Parse/runtime failure | Parse/runtime failure | breaking |
| Change field type (`string` -> `object`) | Contract mismatch | Contract mismatch | breaking |
| Make optional field required | Request rejection likely | Request rejection likely | breaking |
| Change error code semantics without compatibility alias | Retry/alert logic drift | Retry/alert logic drift | breaking |

---

## 3. Breaking Change Requirements

Any `breaking` change must include all items below, otherwise governance gate blocks merge:

1. Migration plan document:
   - impacted clients
   - concrete migration steps
   - owner and deadline
2. Deprecation window:
   - start date
   - end date
   - supported fallback version
3. Rollback plan:
   - rollback trigger thresholds
   - rollback commands/runbook link
4. Compatibility evidence:
   - contract diff report
   - replay or regression test evidence

Required PR labels/checks:

- `protocol-breaking`
- `migration-plan-attached`
- `rollback-plan-attached`

---

## 4. Deprecation Window Policy

Default deprecation window:

- minimum: `2` minor releases or `30` days (whichever is longer).
- recommended: `2-3` release cycles for high-traffic surfaces.

Exceptions:

- security emergency fix (must include incident record).
- legal/compliance mandatory change (must include approval record).

All exceptions require audit trail and explicit reviewer approval.

---

## 5. Deprecation Announcement Template

Use this template in release notes and protocol bulletin:

```markdown
## Protocol Deprecation Notice

- Surface: API|MCP
- Affected contract: <endpoint/tool/resource>
- Change level: breaking
- Deprecated behavior: <what will be removed/changed>
- Replacement behavior: <new contract>
- Start date: YYYY-MM-DD
- End date: YYYY-MM-DD
- Fallback version: <version>
- Migration guide: <link>
- Rollback reference: <link>
- Incident contact: <on-call / channel>
```

---

## 6. Gate Rollout Stages

- Stage A (warning): breakings produce warning + artifact.
- Stage B (soft block): breakings require explicit exemption approval.
- Stage C (blocking): breakings without migration package are blocked.

Current stage: Stage A.

See `docs/protocol/GOVERNANCE_GATE_POLICY.md` for rollout control.

---

## 7. Auditability Requirements

For each breaking change, archive:

- PR link
- diff report artifact link
- migration plan link
- deprecation notice link
- exemption decision (if any)

Retention target: at least 180 days.

