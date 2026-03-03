# Audit Report Template

Use this template for the final consolidated report. Every section is
mandatory — an incomplete report is an incomplete audit.

---

```markdown
# [Project Name] Comprehensive Audit Report — [Date]

> **Audit Scope**: [What was audited — full codebase / specific modules / specific concern]
> **Auditor**: [Who performed the audit]
> **Duration**: [How long the audit took]
> **Codebase Size**: [Lines of code, number of files, number of modules]
> **Methodology**: Deep Codebase Audit (4-dimension, 3-pass, taint-trace)

---

## Executive Summary

**Total Findings**: [N]
- P0/High: [N] — [one-line summary of the most critical]
- P1/Medium: [N] — [one-line summary of the most impactful]
- Low: [N]

**Overall Assessment**: [SHIP / SHIP WITH CONDITIONS / DO NOT SHIP]

- SHIP: No P0, fewer than 3 P1, all P1 have mitigations
- SHIP WITH CONDITIONS: No P0, P1 issues have fix timeline committed
- DO NOT SHIP: Any P0 exists, or P1 count > 5 without mitigations

**Top 3 Systemic Issues** (root causes that produce multiple findings):
1. [Root cause] → manifests as findings #X, #Y, #Z
2. [Root cause] → manifests as findings #A, #B
3. [Root cause] → manifests as finding #C

---

## Audit Dimensions

| # | Dimension | Files Audited | Lines Read | Findings | Method |
|---|-----------|---------------|------------|----------|--------|
| 1 | [Name] | [count] | [count] | [count] | [focus areas] |
| 2 | [Name] | [count] | [count] | [count] | [focus areas] |
| 3 | [Name] | [count] | [count] | [count] | [focus areas] |
| 4 | [Name] | [count] | [count] | [count] | [focus areas] |
| **Total** | | **[sum]** | **[sum]** | **[sum]** | |

---

## Findings

### P0 / High — Must Fix Before Release

| # | Category | Issue | Location | Root Cause (5 Whys) | Fix | Spec |
|---|----------|-------|----------|---------------------|-----|------|
| 1 | [A-F] | [Specific description of what is wrong] | `file.py:line` | [Why this bug exists — the systemic reason, not just "missing validation"] | [Concrete fix — what code to write, not "add validation"] | [spec-name] |

### P1 / Medium — Important Defect

| # | Category | Issue | Location | Root Cause | Fix | Spec |
|---|----------|-------|----------|------------|-----|------|
| N | [A-F] | [description] | `file.py:line` | [root cause] | [fix] | [spec-name] |

### Low — Improvement

| # | Category | Issue | Location | Fix |
|---|----------|-------|----------|-----|
| N | [A-F] | [description] | `file.py:line` | [fix] |

---

## Root Cause Analysis

Group findings by their systemic root cause. This section reveals the
patterns that produce bugs, not just the individual symptoms.

### Root Cause 1: [Name — e.g., "Configuration propagation chain is broken"]

**Description**: [What is the systemic issue]

**Why it exists**: [5-Whys analysis]
1. Why: [immediate cause]
2. Why: [deeper cause]
3. Why: [deeper cause]
4. Why: [deeper cause]
5. Why: [root cause — usually a process/design gap]

**Manifestations**:
| Finding # | Symptom | Location |
|-----------|---------|----------|
| [#] | [how this root cause manifests here] | `file:line` |

**Systemic Fix**: [What architectural/process change prevents ALL manifestations]

### Root Cause 2: [Name]
[Same structure as above]

---

## Architecture Compliance Assessment

Based on ATAM-Lite analysis of the system's claimed quality attributes:

| Quality Attribute | Architectural Decision | Implementation Status | Verdict |
|-------------------|----------------------|----------------------|---------|
| Security | [e.g., Governance layer filters capabilities] | [e.g., Filter exists but never actually removes anything] | FAIL / PARTIAL / PASS |
| Availability | [e.g., Circuit breaker on external deps] | [e.g., Circuit breaker implemented but threshold too high] | FAIL / PARTIAL / PASS |
| Modifiability | [e.g., Integration isolation via wrappers] | [e.g., Most integrations wrapped, 2 direct calls remain] | FAIL / PARTIAL / PASS |

---

## Data Flow Audit Results

For each critical data flow traced during the audit:

| # | Flow | Source | Validation | Transformation | Sink | Verdict |
|---|------|--------|------------|----------------|------|---------|
| 1 | User config → LLM call | CLI/API | [where validated] | [where transformed] | litellm.acompletion() | [SAFE / UNSAFE — finding #X] |
| 2 | Tool result → LLM prompt | Tool handler | [where validated] | [where transformed] | messages[] | [SAFE / UNSAFE — finding #Y] |

---

## Cross-Reference with Existing Specs

| Existing Spec | Overlap | Resolution |
|---------------|---------|------------|
| [spec-name] | [which findings overlap] | [keep in new spec / mark as "see existing spec X"] |

---

## Recommended Fix Order

Priority-ordered list of specs to implement:

| Order | Spec | Severity | Tasks | Rationale |
|-------|------|----------|-------|-----------|
| 1 | [spec-name] | P0 | [N] | [Why this must be fixed first — e.g., "closes remote attack vector"] |
| 2 | [spec-name] | P0/P1 | [N] | [Why second — e.g., "blocks other fixes" or "highest blast radius"] |
| 3 | [spec-name] | P1 | [N] | [Rationale] |
| 4 | [spec-name] | P1/Low | [N] | [Rationale] |

---

## Audit Completeness Checklist

- [ ] Every file in every dimension was read (3-pass method)
- [ ] Every external data flow was traced source → sink
- [ ] Every error path was checked
- [ ] Every configuration value was traced end-to-end
- [ ] Every finding has a root cause analysis
- [ ] Every finding has a concrete fix suggestion
- [ ] Findings have been deduplicated and cross-referenced
- [ ] Specs have been generated for fix domains with 3+ issues
- [ ] Recommended fix order has been established
- [ ] Executive summary accurately reflects findings
```
