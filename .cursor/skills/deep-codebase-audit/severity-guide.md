# Severity Classification Guide

> **Principle**: When in doubt, classify higher. It is always easier to
> downgrade a finding than to explain why a shipped bug was missed.

---

## Decision Tree

Use this tree for every finding. Start at the top, follow the branches.

```
1. Can this be exploited by an external attacker without authentication?
   ├── YES → P0/High
   │   Examples: SQL injection in public API, unauthenticated admin endpoint,
   │   SSRF via user-controlled URL, prompt injection that exfiltrates data
   └── NO ↓

2. Can this cause data loss, corruption, or cross-tenant data leakage?
   ├── YES → P0/High
   │   Examples: Missing tenant_id filter in query, unprotected DELETE endpoint,
   │   migration that drops column without backup, race condition on write
   └── NO ↓

3. Can this cause service unavailability under normal conditions?
   ├── YES → P0/High
   │   Examples: Infinite retry loop, unbounded memory growth, missing timeout
   │   on synchronous external call, deadlock in common code path
   └── NO ↓

4. Is a core feature silently broken (user thinks it works but it doesn't)?
   ├── YES → P0/High
   │   Examples: Config value set but never propagated, mock mode bypassed,
   │   governance filter that never actually filters, circuit breaker that
   │   never trips, heartbeat that never detects events
   └── NO ↓

5. Can this be exploited by an authenticated user to escalate privileges?
   ├── YES → P0/High
   │   Examples: Missing authorization check on admin API, tenant_id from
   │   user input instead of session, role check that only checks name string
   └── NO ↓

6. Does this cause incorrect behavior in an edge case that real users will hit?
   ├── YES → P1/Medium
   │   Examples: Empty input causes crash, concurrent requests cause duplicate
   │   records, timezone handling breaks for non-UTC users, Unicode in
   │   username causes encoding error
   └── NO ↓

7. Is there a resource leak on an error path?
   ├── YES → P1/Medium
   │   Examples: DB connection not closed on exception, file handle leaked
   │   when validation fails, async task not cancelled on shutdown,
   │   thread pool not shut down on error
   └── NO ↓

8. Does this violate a documented architectural invariant?
   ├── YES → P1/Medium
   │   Examples: Cross-module import that breaks isolation, DB query without
   │   tenant filter in multi-tenant system, direct external service call
   │   bypassing integration wrapper, hardcoded value overriding config
   └── NO ↓

9. Is this a missing safety mechanism that should exist?
   ├── YES → P1/Medium
   │   Examples: No rate limiting on auth endpoint, no size limit on upload,
   │   no circuit breaker on flaky dependency, no timeout on LLM call,
   │   no input validation on CLI arguments
   └── NO ↓

10. Is this a code quality issue with no immediate runtime impact?
    └── YES → Low
        Examples: Inconsistent naming, missing type hints, redundant code,
        suboptimal algorithm for small input, missing docstring on public API
```

---

## Detailed Criteria by Category

### P0 / High — Must Fix Before Release

**The test**: "If this ships, will it cause a security incident, data loss,
or service outage?"

#### Security P0
| Pattern | Why P0 | Example |
|---------|--------|---------|
| Unauthenticated access to sensitive endpoint | Attacker can access without credentials | Management API with no auth middleware |
| Injection (SQL, command, prompt, LDAP) | Attacker can execute arbitrary operations | `f"SELECT * FROM users WHERE name='{user_input}'"` |
| Credential exposure | Attacker gains access to other systems | API key in error response, token in URL parameter |
| Unsafe deserialization | Remote code execution | `pickle.loads(user_data)`, `yaml.load()` without SafeLoader |
| Path traversal | Attacker reads/writes arbitrary files | `open(f"/uploads/{user_filename}")` without sanitization |
| SSRF | Attacker accesses internal services | `requests.get(user_provided_url)` from server |
| Prompt injection leading to tool misuse | Agent performs unintended actions | Unsanitized RAG results in system prompt |

#### Data P0
| Pattern | Why P0 | Example |
|---------|--------|---------|
| Missing tenant isolation | Users see each other's data | Query without `WHERE tenant_id = ?` |
| Race condition on write | Data corruption | Check-then-act without lock |
| Irreversible migration | Data loss on rollback | `DROP COLUMN` without data backup |
| Unbounded data growth | Disk exhaustion → outage | Audit log with no rotation/TTL |

#### Availability P0
| Pattern | Why P0 | Example |
|---------|--------|---------|
| Infinite loop/retry | CPU exhaustion | `while True: retry()` with no max attempts |
| Missing timeout on sync call | Thread starvation | `requests.get(url)` with no timeout parameter |
| Unbounded memory growth | OOM kill | Appending to list in loop with no size limit |
| Deadlock | Complete service freeze | Acquiring locks A→B in one path, B→A in another |

#### Correctness P0
| Pattern | Why P0 | Example |
|---------|--------|---------|
| Config not propagating | User's settings are silently ignored | `model` parameter set but factory uses default |
| Safety mechanism disabled | Protection exists but doesn't work | Circuit breaker that never trips |
| Silent data loss | Operation appears to succeed but data is lost | `except: pass` on write operation |

### P1 / Medium — Important Defect

**The test**: "This won't cause an incident today, but it will cause problems
for real users or accumulate into a bigger issue."

| Category | Pattern | Example |
|----------|---------|---------|
| **Edge case** | Works normally, fails on boundary input | Empty string, max int, null, Unicode |
| **Resource leak** | Leak on error path (not happy path) | Connection not closed in `except` block |
| **Race condition** | Under realistic (not extreme) load | Counter increment without atomic operation |
| **Config override** | User setting silently ignored | Default value shadows user config |
| **Convention violation** | Breaks documented architectural rules | Missing tenant_id in DB index |
| **Missing safety** | No timeout/limit where one should exist | LLM call with no timeout |
| **Incomplete feature** | Feature exists but doesn't fully work | CLI command that ignores some flags |
| **Error handling** | Error caught but poorly handled | Generic `except Exception` that logs and continues |

### Low — Improvement

**The test**: "This is suboptimal but won't cause problems under normal use."

| Category | Pattern | Example |
|----------|---------|---------|
| **Code smell** | Functional but messy | Deeply nested conditionals |
| **Missing validation** | Unlikely to be triggered | Internal function doesn't validate type |
| **Performance** | Suboptimal for small inputs | O(n²) where n < 100 |
| **Documentation** | Missing or outdated | Docstring doesn't match current behavior |
| **Naming** | Inconsistent but understandable | `get_user` vs `fetch_user` in same module |
| **Dead code** | Unreachable but harmless | Commented-out function |

---

## Adjustment Rules

### Upgrade Triggers (Low → P1, or P1 → P0)

1. **Compound risk**: Two P1 issues that together create a P0 scenario.
   Example: Missing input validation (P1) + string concatenation in SQL (P1)
   = SQL injection (P0).

2. **Blast radius**: A P1 issue that affects every request (not just edge
   cases) should be upgraded to P0.

3. **Exploitability**: A theoretical vulnerability becomes P0 if you can
   construct a realistic attack scenario in under 5 minutes.

4. **Data sensitivity**: Any issue involving PII, financial data, or
   credentials is automatically one level higher.

5. **Cascading failure**: An issue that can trigger failures in other
   components is one level higher.

### Downgrade Triggers (P0 → P1, or P1 → Low)

1. **Defense in depth**: The vulnerability exists but is mitigated by another
   layer (e.g., SQL injection in code, but parameterized queries enforced by
   ORM). Downgrade by one level but still report.

2. **Internal-only**: The vulnerable code path is only reachable by
   authenticated internal users with admin privileges.

3. **Theoretical only**: No realistic attack path exists given the system's
   deployment model (e.g., SSRF in a system that only runs on localhost).

4. **Already mitigated**: The issue exists in code but is prevented by
   infrastructure (WAF, network policy, etc.). Still report as Low.

---

## Classification Checklist

Before finalizing severity, verify:

- [ ] I have considered the worst-case scenario, not the average case
- [ ] I have checked if this issue combines with others to create a higher
      severity scenario
- [ ] I have assessed exploitability (not just theoretical possibility)
- [ ] I have considered the blast radius (all users vs edge case)
- [ ] I have checked for defense-in-depth mitigations
- [ ] I have not downgraded just because "it's unlikely" — unlikely ≠ impossible
