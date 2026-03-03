---
name: deep-codebase-audit
description: >
  Perform comprehensive multi-dimensional code audits that find real bugs,
  security flaws, and architectural issues by reading every line of critical
  paths. This is the final quality gate before a product ships. Use when the
  user asks for a code audit, security review, architecture review, deep
  review, quality audit, codebase health check, or asks to find all
  bugs/issues/defects in a project.
---

# Deep Codebase Audit — Complete Methodology

> **You are the last line of defense.** If you miss it, it ships to users.
> This is not a checklist exercise — it is a disciplined thinking process.

This skill teaches you how to **think like a senior technical director** who is
personally accountable for every defect that reaches production. It covers not
just *what* to look for, but *how to reason*, *how to trace*, *how to decide*,
and *how to avoid the cognitive traps* that cause reviewers to miss real bugs.

---

## Part 0: Mindset — The Mental Model You Must Adopt

Before reading a single line of code, internalize these principles:

### 0.1 You Are Not Reviewing — You Are Attacking

A reviewer looks for whether code "seems right." An auditor assumes the code
is broken and searches for proof. Your default hypothesis for every function
is: **"This has a bug. Where is it?"** You are only satisfied when you have
exhausted every angle and found nothing — not when the code "looks fine."

### 0.2 The Five Thinking Lenses

Apply these lenses to every piece of code, in this order:

1. **Correctness**: Does it do what it claims? Trace inputs → outputs manually.
2. **Failure**: What happens when things go wrong? Network down, disk full,
   null input, concurrent access, timeout, OOM, partial write.
3. **Adversary**: What if the input is crafted by an attacker? Injection,
   overflow, type confusion, privilege escalation, denial of service.
4. **Drift**: Does the code match the spec/docs/comments? Has the design
   evolved but the code hasn't caught up?
5. **Omission**: What *should* exist but doesn't? Missing validation, missing
   cleanup, missing timeout, missing log, missing test.

### 0.3 Cognitive Bias Defense

Research shows ~70% of developer actions are affected by cognitive bias.
Guard against these during audit:

| Bias | Trap | Defense |
|------|------|---------|
| **Confirmation** | "This code looks well-written, so it's probably correct" | Force yourself to find at least one issue per file |
| **Anchoring** | First impression of code quality colors all subsequent judgment | Read the most complex function first, not the cleanest |
| **Decision fatigue** | Quality of review degrades after ~200 lines | Take breaks; audit in 30-minute focused sessions |
| **Authority** | "A senior wrote this, it must be right" | Code has no author during audit — only behavior |
| **Familiarity** | Skipping code you've seen before | Re-read it. Bugs hide in code everyone trusts |
| **Survivorship** | "No one reported a bug, so there isn't one" | Absence of reports ≠ absence of bugs |

### 0.4 The Auditor's Oath

Before starting, commit to these:

- I will read every line of every critical file. I will not skim.
- I will trace every data flow from source to sink.
- I will check every error path, not just the happy path.
- I will question every default value, every hardcoded constant.
- I will verify every claim in comments and docstrings against the code.
- I will not stop when I find "enough" issues — I will stop when I have
  exhausted every angle.

---

## Part 1: Preparation — Before You Read Code

### 1.1 Understand the System (30 minutes)

Before touching code, build a mental model:

1. **Read architecture docs** — What are the major components? How do they
   communicate? What are the trust boundaries?
2. **Read the spec/design docs** — What is the system supposed to do? What
   are the invariants? What are the quality attributes (performance, security,
   availability, modifiability)?
3. **Draw a Data Flow Diagram (DFD)** mentally or on paper:
   - Identify all **external entities** (users, APIs, databases, LLMs)
   - Identify all **processes** (handlers, loops, workers)
   - Identify all **data stores** (DB, cache, files, memory)
   - Mark **trust boundaries** (where does trusted become untrusted?)
4. **Identify the critical paths** — What code runs on every request? What
   code handles money/auth/data? What code is most complex?

### 1.2 Identify Audit Dimensions

Split the codebase into 4 parallel audit dimensions. Each dimension gets a
dedicated focus to ensure depth over breadth.

**Standard dimension template** (adapt to the specific project):

| # | Dimension | Target | What You're Really Checking |
|---|-----------|--------|-----------------------------|
| 1 | **Core Logic** | Main processing loop, decision engine, state machine | "Does the brain of the system actually work correctly under all conditions?" |
| 2 | **Lifecycle + Integrations** | App entry/exit, external service adapters, SDK wrappers | "Can the system start, run, and stop cleanly? Do external calls fail gracefully?" |
| 3 | **I/O Boundaries** | Triggers, API handlers, event processors, CLI | "Is every input validated? Is every output safe? Can an attacker get in?" |
| 4 | **Data + Security** | DB layer, auth, crypto, sanitization, secrets | "Is data safe at rest and in transit? Can users see each other's data?" |

### 1.3 File Inventory

For each dimension, create an explicit file list. Do not rely on memory.

```
Dimension 1 — Core Logic:
  owlclaw/agent/runtime/runtime.py    (520 lines)
  owlclaw/agent/runtime/heartbeat.py  (180 lines)
  owlclaw/agent/runtime/context.py    (95 lines)
  ...
```

This ensures no file is accidentally skipped.

---

## Part 2: The Audit Process — How to Read Code

### 2.1 The Three-Pass Reading Method

For each file, do three passes. Never try to find everything in one pass.

#### Pass 1: Structure (2 min per 100 lines)
- Read class/function signatures, imports, module docstring
- Understand the file's role in the system
- Note: public API surface, dependencies, inheritance
- Question: Does this file belong in this module? Are imports correct?

#### Pass 2: Logic (5 min per 100 lines)
- Read every line of every function body
- For each function, mentally execute it with:
  - **Normal input** — does it produce the expected output?
  - **Empty/null input** — does it handle gracefully?
  - **Boundary input** — max int, empty string, huge list
  - **Concurrent input** — what if called simultaneously?
- For each branch (`if/else/try/except`):
  - Is the condition correct? (Off-by-one? Wrong operator?)
  - Is the else/except handler correct? (Not just present — correct?)
  - Is there a missing branch? (What about the case not covered?)

#### Pass 3: Data Flow (3 min per 100 lines)
- Trace every piece of external data from entry to final use:
  - **Source** → where does this data come from? (user, API, DB, file, env)
  - **Validation** → is it validated? Where? Is the validation sufficient?
  - **Transformation** → is it modified? Could the modification introduce issues?
  - **Sink** → where does it end up? (SQL query, shell command, LLM prompt,
    HTML template, log file, response body)
- This is **taint analysis** — track untrusted data through the system.

### 2.2 The Question Protocol

At every decision point in the code, ask these questions:

#### For every function:
- What is the contract? (preconditions, postconditions, invariants)
- What happens if a precondition is violated?
- Is the function idempotent? Should it be?
- What resources does it acquire? Are they always released?
- Can it be called concurrently? Is it safe?

#### For every external call (HTTP, DB, LLM, file I/O):
- Is there a timeout?
- What happens on timeout? On connection error? On malformed response?
- Is the response validated before use?
- Is there retry logic? Is it bounded? Does it have backoff?
- Are credentials handled safely?

#### For every configuration value:
- Where is it defined? Where is it read?
- Can the user override it? Does the override actually take effect?
- Trace the value from definition → storage → retrieval → use.
  Does it arrive at the point of use unchanged?
- What is the default? Is the default safe? Is it documented?

#### For every error handler (try/except/catch):
- Is the exception type specific enough? (Catching `Exception` hides bugs)
- Is the error logged with sufficient context?
- Is the error propagated correctly? (Not swallowed silently)
- Does the handler clean up resources?
- Could the handler itself throw?

#### For every data model / DB operation:
- Is tenant isolation enforced? (Every query filtered by tenant_id?)
- Are inputs parameterized? (No string concatenation in SQL)
- Is the connection/session properly managed? (Closed on error?)
- Are migrations reversible? Do they handle existing data?

### 2.3 The "5 Whys" for Every Finding

When you find an issue, don't stop at the symptom. Ask "why" five times:

```
Finding: LLM call uses hardcoded model "gpt-4o-mini" instead of user config.

Why 1: The runtime constructor doesn't receive the model parameter.
Why 2: The factory function `create_agent_runtime()` doesn't pass it.
Why 3: The `OwlClaw.configure()` stores it but `create_agent_runtime()`
        doesn't read it from the config object.
Why 4: The config object has the field, but the factory was written before
        the config field was added.
Why 5: There is no integration test that verifies config propagation
        end-to-end.

Root cause: Missing end-to-end config propagation test.
Fix: Add the test AND fix the propagation chain.
```

This prevents surface-level fixes that leave the root cause intact.

---

## Part 3: Specialized Audit Techniques

### 3.1 Configuration Propagation Audit

This is the #1 source of "it works on my machine" bugs.

**Method**: Pick every user-configurable value. Trace it through the system:

```
User sets value
  → stored in config object
    → passed to factory function
      → received by component constructor
        → used at point of execution
```

At each step, verify:
- Is the value actually passed? (Not a different variable with the same name)
- Is it transformed? (Could the transformation lose information?)
- Is there a default that silently overrides it?
- Is there a cache that serves a stale value?

**Common traps**:
- Factory function has `model="gpt-4o-mini"` as default parameter
- Config object stores the value but the constructor reads from env instead
- Value is passed to parent class but parent class ignores it
- Value is set after initialization, but the component reads it during init

### 3.2 Security Audit for AI/Agent Systems

AI systems have unique attack surfaces. Apply OWASP's Agentic Top 10 (2026):

| Risk | What to Check | How to Check |
|------|---------------|--------------|
| **Agent Goal Hijack (ASI01)** | Can external data (emails, docs, RAG results) alter agent behavior? | Trace every piece of external text that enters the LLM prompt. Is it sandboxed? |
| **Tool Misuse (ASI02)** | Can the agent be tricked into misusing its tools? | Check tool argument validation. Can the LLM pass arbitrary args? |
| **Memory Poisoning** | Can stored memories be manipulated to alter future behavior? | Check memory write path — is content sanitized before storage? |
| **Excessive Autonomy** | Can the agent take high-impact actions without approval? | Check governance layer — are dangerous operations gated? |
| **Denial of Wallet** | Can an attacker trigger unbounded LLM/API calls? | Check loop termination, retry limits, budget enforcement |
| **Cascading Failures** | Does one agent's failure propagate to others? | Check error isolation between agents/capabilities |

**Prompt injection audit checklist**:
- [ ] User message → LLM: Is user content clearly delimited from system prompt?
- [ ] Tool results → LLM: Are tool outputs sanitized before inclusion?
- [ ] SKILL.md → LLM: Is skill content validated/sandboxed?
- [ ] Memory → LLM: Are retrieved memories sanitized?
- [ ] RAG results → LLM: Are retrieved documents treated as untrusted?

### 3.3 Architecture Compliance Audit (ATAM-Lite)

Based on CMU SEI's Architecture Tradeoff Analysis Method:

1. **List quality attributes** the system claims to support
   (from architecture docs): e.g., security, modifiability, availability
2. **For each attribute, identify the architectural decisions** that support it
   (from design docs): e.g., "governance layer provides security"
3. **For each decision, verify the implementation** actually delivers it:
   - Does the governance layer actually filter capabilities? Test it.
   - Does the circuit breaker actually trip? Under what conditions?
   - Does the heartbeat actually detect failures? How quickly?
4. **Identify sensitivity points**: Where does changing one thing break another?
5. **Identify tradeoff points**: Where do quality attributes conflict?

### 3.4 Concurrency and State Audit

For every piece of shared mutable state:

1. **Identify** — What data is shared between threads/tasks/requests?
2. **Protect** — Is there a lock/mutex/atomic? Is it the right granularity?
3. **Order** — Can operations happen in an unexpected order?
4. **Deadlock** — Can two locks be acquired in different orders?
5. **Starvation** — Can one consumer monopolize a resource?

For async code specifically:
- Are `await` points in safe locations? (State consistent at yield points?)
- Are tasks properly cancelled on shutdown?
- Are task results collected? (Uncollected tasks = swallowed exceptions)

### 3.5 Error Propagation Audit

Trace what happens when each external dependency fails:

```
Database down → what happens?
  → Connection timeout (is there one?) → 30s
  → Exception type → OperationalError
  → Caught where? → In the session context manager
  → Logged? → Yes, but without request context
  → Propagated? → Converted to generic InternalError
  → User sees? → 500 with no useful message
  → Retry? → No
  → Circuit breaker? → No
  → Recovery? → Manual restart required
```

Do this for: DB, LLM provider, message queue, cache, external APIs, file system.

---

## Part 4: The Complete Audit Checklist

This is the full checklist. Use it as a verification tool AFTER the thinking
process above, not as a substitute for it.

### A. Correctness
- [ ] Every branch/path has defined behavior (no silent fallthrough)
- [ ] Loop termination is guaranteed (no infinite loops/retries)
- [ ] Return values are checked (no ignored errors, no bare `except: pass`)
- [ ] Edge cases: empty input, None, max values, concurrent access
- [ ] State mutations are atomic or properly locked
- [ ] Numeric operations: overflow, underflow, division by zero, float precision
- [ ] String operations: encoding (UTF-8 assumed but not verified?), length limits
- [ ] Collection operations: empty collection, single element, duplicate keys
- [ ] Time operations: timezone handling, DST, leap seconds, clock skew
- [ ] Comparison operations: `==` vs `is`, float equality, None comparison

### B. Security
- [ ] All external input is validated before use (type, range, format, length)
- [ ] No `eval()`, `exec()`, `pickle.loads()`, or unsafe deserialization
- [ ] No shell injection (`subprocess` with `shell=True` + user input)
- [ ] No SQL injection (string concatenation in queries)
- [ ] No path traversal (`../` in file paths from user input)
- [ ] No SSRF (user-controlled URLs in server-side requests)
- [ ] No XXE (XML parsing without defusedxml)
- [ ] Credentials never logged, never in error messages, never in URLs
- [ ] Auth enforced on ALL endpoints (not just the ones you remember)
- [ ] CORS: `credentials: true` requires explicit origins (not `*`)
- [ ] Rate limiting on authentication endpoints
- [ ] Secrets in env vars, not in code, not in config files committed to git
- [ ] Dependencies: known vulnerabilities? Pinned versions?
- [ ] Prompt injection: all paths from external data to LLM prompt are sanitized
- [ ] Tool argument validation: LLM-generated arguments are validated before execution

### C. Robustness
- [ ] Timeouts on ALL external calls (DB, HTTP, LLM, SDK, file I/O)
- [ ] Resource cleanup in `finally`/`with`/context managers (connections, files, locks, tasks)
- [ ] Idempotent operations where expected (start, register, configure, retry)
- [ ] Graceful degradation when optional dependencies are missing
- [ ] Size/rate limits on all input channels (request body, file upload, WebSocket message)
- [ ] Backpressure handling (what if producer is faster than consumer?)
- [ ] Graceful shutdown (in-flight requests completed, resources released)
- [ ] Health check endpoint (not just "is process alive" but "can it serve requests?")
- [ ] Circuit breaker on external dependencies (with proper thresholds and recovery)
- [ ] Retry with exponential backoff and jitter (not fixed interval, not unbounded)

### D. Architecture Compliance
- [ ] Imports follow project conventions (absolute vs relative)
- [ ] Module boundaries respected (no cross-layer imports)
- [ ] DB models follow schema conventions (PK type, tenant isolation, timestamps)
- [ ] Index naming and composition match conventions
- [ ] Configuration propagates end-to-end (no hardcoded defaults overriding user config)
- [ ] Integration isolation (external services wrapped, not called directly)
- [ ] API contracts match implementation (request/response schemas)
- [ ] Error codes/types are consistent across the codebase
- [ ] Logging format is consistent (structured, with correlation IDs)
- [ ] Feature flags/config toggles actually control the features they claim to

### E. Observability
- [ ] Errors logged with context (request ID, user ID, operation, input summary)
- [ ] Critical paths have structured logging (not just print statements)
- [ ] Audit events persisted (not just in-memory)
- [ ] Metrics are thread-safe (atomic counters, not `count += 1`)
- [ ] Log levels are appropriate (ERROR for errors, not WARN; DEBUG for debug, not INFO)
- [ ] No sensitive data in logs (passwords, tokens, PII)
- [ ] Distributed tracing: correlation IDs propagated across service boundaries
- [ ] Alertable conditions have corresponding log entries

### F. Testing Quality
- [ ] Critical paths have tests (not just the easy paths)
- [ ] Error paths have tests (what happens when X fails?)
- [ ] Edge cases have tests (empty, null, max, concurrent)
- [ ] Tests actually assert behavior (not just "doesn't throw")
- [ ] Tests are deterministic (no flaky tests, no time-dependent assertions)
- [ ] Integration tests use realistic configurations (not just defaults)
- [ ] No tests that test the mock instead of the code
- [ ] Test coverage of security-critical code ≥ 90%

---

## Part 5: Issue Reporting — How to Write Findings

### 5.1 Finding Format

Every finding MUST include all of these fields:

```markdown
| # | Severity | Category | Issue | File:Line | Root Cause | Fix |
```

- **#**: Sequential number within the audit
- **Severity**: P0/High, P1/Medium, Low (see severity-guide.md)
- **Category**: Which checklist item (e.g., B.Security, C.Robustness)
- **Issue**: One-sentence description of what is wrong
- **File:Line**: Exact location (not "somewhere in runtime.py")
- **Root Cause**: WHY it's wrong (the 5-Whys result)
- **Fix**: Concrete fix suggestion (not "fix this" — actual code change)

### 5.2 Bad vs Good Findings

**Bad finding** (too vague, no root cause, no actionable fix):
```
| 1 | P1 | Security | Input not validated | app.py | Needs validation | Add validation |
```

**Good finding** (specific, traced, actionable):
```
| 1 | P1 | B.Security | `configure()` accepts `model` parameter as string
  with no validation — attacker could pass "../../etc/passwd" which propagates
  to litellm's `model` field | owlclaw/app.py:142 | No input validation on
  `configure()` parameters; the method trusts all caller input because it was
  originally designed for internal use only, but is now exposed via CLI |
  Add `_validate_model_name(model)` that checks against allowlist pattern
  `^[a-zA-Z0-9/_.-]+$` before storing |
```

### 5.3 Consolidation Process

After all dimensions complete:

1. **Deduplicate** — Same issue found by multiple dimensions → keep the one
   with the best root cause analysis
2. **Cross-reference** — Check if issues are already tracked in existing
   specs/tasks. Mark as "see existing spec X" if so.
3. **Categorize by fix domain** — Group by which module/team would fix it,
   not by which dimension found it
4. **Root cause clustering** — Multiple symptoms from one root cause →
   single finding with multiple manifestations
5. **Prioritize** — P0 first, then P1, then Low. Within same severity,
   prioritize by blast radius (affects all users > affects edge case)

---

## Part 6: Decision Framework — How to Make Judgment Calls

### 6.1 Severity Decision Tree

```
Is there a security vulnerability?
├── Yes → Can it be exploited remotely without authentication?
│   ├── Yes → P0
│   └── No → Can it be exploited by an authenticated user?
│       ├── Yes → P0 if privilege escalation, P1 otherwise
│       └── No → P1
├── No → Can it cause data loss or corruption?
│   ├── Yes → P0
│   └── No → Can it cause service unavailability?
│       ├── Yes → Under normal load? → P0. Only under extreme load? → P1
│       └── No → Is a core feature silently broken?
│           ├── Yes → P0 (user thinks it works but it doesn't)
│           └── No → Is it a functional defect?
│               ├── Yes → Affects happy path? → P1. Affects edge case? → Low
│               └── No → Low
```

### 6.2 "Should I Report This?" Decision

When in doubt about whether something is worth reporting:

- **Report it.** It's always better to report a non-issue than to miss a real
  bug. The consolidation phase will filter false positives.
- If you're unsure about severity, report it as P1 and let the consolidation
  phase adjust.
- If you think "this is probably fine" — that's confirmation bias talking.
  Investigate it.

### 6.3 When to Stop Auditing a File

You are done with a file when ALL of these are true:
- You have read every line (not skimmed — read)
- You have traced every external data flow to its sink
- You have checked every error path
- You have verified every claim in comments/docstrings
- You have applied all 5 thinking lenses
- You can explain what every function does without re-reading it

---

## Part 7: Spec Generation — From Findings to Action

### 7.1 When to Create a Spec

Create a new spec when:
- 3+ findings share a common fix domain (same module/subsystem)
- A finding requires architectural change (not just a one-line fix)
- Multiple findings stem from the same root cause

### 7.2 Spec Structure

```
category-name/
├── requirements.md   # REQ-XX per issue, with:
│                     #   - Current behavior (what's wrong)
│                     #   - Expected behavior (what should happen)
│                     #   - Acceptance criteria (how to verify the fix)
│                     #   - Root cause reference (from 5-Whys)
├── design.md         # For each REQ:
│                     #   - Fix approach (concrete, not hand-wavy)
│                     #   - Affected files table
│                     #   - Risk assessment (what could this fix break?)
│                     #   - Test strategy (what tests prove it's fixed?)
└── tasks.md          # Task per REQ with:
                      #   - Implementation subtasks
                      #   - Test subtasks
                      #   - Regression test task at end
```

### 7.3 Fix Ordering

Order specs by:
1. **P0 security** — fixes that close attack vectors
2. **P0 correctness** — fixes that prevent data loss/corruption
3. **P0 availability** — fixes that prevent service outage
4. **P1 that block other fixes** — foundational issues
5. **P1 by blast radius** — most users affected first
6. **Low** — batch into improvement specs

---

## Part 8: Teaching Other Models — How to Transfer This Skill

If you are a more capable model teaching a less capable one, emphasize:

### 8.1 The Non-Negotiables

1. **Read every line.** Not "scan" — read. If you can't explain what line 247
   does, you haven't read it.
2. **Trace data flows.** Pick a user input. Follow it through every function,
   every transformation, every storage, until it reaches its final destination.
   Did it get validated? Did it get sanitized? Did it get logged safely?
3. **Check failure paths.** For every `try`, read the `except`. For every
   external call, ask "what if this times out?" For every loop, ask "what
   stops this?"
4. **Question defaults.** Every hardcoded value is suspicious. Every default
   parameter is suspicious. Every `or fallback_value` is suspicious.
5. **Verify, don't trust.** If a comment says "thread-safe" — find the lock.
   If a docstring says "validates input" — find the validation. If the
   architecture doc says "circuit breaker" — find the implementation.

### 8.2 Common Mistakes Less Capable Models Make

| Mistake | Why It Happens | How to Avoid |
|---------|---------------|--------------|
| Reporting code smells instead of bugs | Easier to spot style issues than logic errors | Ask "does this cause incorrect behavior?" — if no, it's Low at best |
| Stopping after finding 5-10 issues | Anchoring on "that's enough" | Set a minimum: read every file in the dimension, report every finding |
| Vague findings ("input not validated") | Lack of specificity | Always include: which input, which function, which line, what could go wrong |
| Missing config propagation bugs | Not tracing end-to-end | Pick every config value, trace from user → storage → use |
| Missing concurrency bugs | Not thinking about parallel execution | For every shared variable, ask "what if two threads access this simultaneously?" |
| Reporting theoretical issues as P0 | Not assessing exploitability | Ask "can a real attacker actually trigger this?" — if unlikely, downgrade |
| Copying the checklist without thinking | Treating audit as checkbox exercise | The checklist is a verification tool, not the audit itself |

### 8.3 The Audit is Complete When

- [ ] Every file in every dimension has been read (three-pass method)
- [ ] Every external data flow has been traced source → sink
- [ ] Every error path has been checked
- [ ] Every configuration value has been traced end-to-end
- [ ] Every finding has a root cause (5 Whys)
- [ ] Every finding has a concrete fix suggestion
- [ ] Findings have been deduplicated and cross-referenced
- [ ] Specs have been generated for fix domains with 3+ issues
- [ ] A recommended fix order has been established

---

## Part 9: Execution Norms — Non-Negotiable Process Rules

These rules ensure the audit methodology is followed consistently, not just
understood. They were derived from real execution gaps observed in practice.

### 9.1 Existing Reports Do Not Replace Fresh Audits

If a prior audit report exists (e.g., from a previous session or another agent),
you MUST still execute the full methodology independently. Prior reports serve
as a **cross-reference baseline**, not a substitute. Specifically:

- Read the prior report AFTER completing your own Dimension 1 pass (to avoid
  anchoring bias — see Part 0.3).
- Cross-reference your findings with the prior report in the consolidation
  phase (Part 5.3), not during the audit itself.
- Any finding in the prior report that you cannot independently reproduce
  should be flagged as "unverified — prior report only."

### 9.2 File Inventory Is Mandatory

Before starting any dimension, produce an explicit file list with line counts
(Part 1.3). Do not rely on "I know the codebase" — files get added, renamed,
and deleted. Use `find` or `glob` to enumerate.

### 9.3 Quantify Everything

Every audit must produce these metrics in the final report:

- Total files audited (per dimension)
- Total lines read
- Total findings (by severity: P0 / P1 / Low)
- Total specs generated
- Audit duration (wall clock)

### 9.4 Report Must Use Template

The final report MUST use `report-template.md`. Incremental summaries or
narrative-style reports are not acceptable as the primary deliverable.
They may supplement the template-based report but never replace it.

---

## Supporting Files

- **[thinking-models.md](thinking-models.md)** — Detailed analysis patterns
  for specific code patterns (loops, state machines, auth, crypto, etc.)
- **[anti-patterns.md](anti-patterns.md)** — Catalog of common code
  anti-patterns with detection heuristics and real examples
- **[severity-guide.md](severity-guide.md)** — Detailed severity classification
  with decision trees and examples
- **[report-template.md](report-template.md)** — Template for the final
  consolidated audit report
