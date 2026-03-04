# Review Checklist — Per-Round Quick Reference

> Print this or keep it open during every review round.
> Check every box before giving your verdict.

---

## Pre-Review

- [ ] `git merge main` — synced to latest baseline
- [ ] Read WORKTREE_ASSIGNMENTS.md — know which spec this agent is working on
- [ ] Read the spec's `design.md` — understand what the implementation should look like
- [ ] Read the spec's `tasks.md` — know which tasks are being claimed as done
- [ ] `git log main..<branch> --oneline` — understand the scope of changes
- [ ] `git diff main..<branch> --stat` — see which files changed and how much

---

## Dimension A: Spec Consistency

- [ ] Implementation matches design.md architecture
- [ ] Task checkboxes match actual code (no false claims of completion)
- [ ] Interfaces match requirements.md
- [ ] Acceptance criteria are verifiable from the code
- [ ] No scope creep (unrequested features)
- [ ] No scope shrinkage (silently skipped requirements)

**Verification method**: For each `[x]` task, trace: requirement → design → code → test.

---

## Dimension B: Code Quality

- [ ] Type annotations complete
- [ ] Error handling uses specific exception types
- [ ] Naming conventions followed (snake_case / PascalCase / UPPER_SNAKE_CASE)
- [ ] Absolute imports only
- [ ] No TODO/FIXME/HACK
- [ ] No hardcoded business rules
- [ ] No fake data
- [ ] Logging uses stdlib `logging` with `%s` formatting
- [ ] Comments and docstrings in English
- [ ] No `print()` in production code

---

## Dimension C: Test Coverage

- [ ] New code has unit tests
- [ ] Test naming: `test_*.py` files, `test_*` functions
- [ ] Tests assert behavior (not just "doesn't throw")
- [ ] Error paths tested
- [ ] `poetry run pytest` passes after merge
- [ ] Critical path coverage >= 75%
- [ ] Tests are deterministic
- [ ] Mocks test the code, not the mock

---

## Dimension D: Architecture Compliance

- [ ] Module boundaries respected
- [ ] Integration isolation maintained
- [ ] Database conventions followed (tenant_id, UUID PK, TIMESTAMPTZ)
- [ ] No cross-database access
- [ ] Config propagates end-to-end
- [ ] External services go through integration wrappers
- [ ] API contracts match implementation

---

## Dimension E: Security

- [ ] External input validated
- [ ] No eval/exec/pickle.loads/unsafe deserialization
- [ ] No SQL/shell/prompt injection vectors
- [ ] Credentials not in logs/errors/URLs
- [ ] Auth enforced on all endpoints
- [ ] CORS config correct
- [ ] LLM prompt injection paths sanitized
- [ ] Tool arguments validated
- [ ] No secrets in code

---

## Dimension F: Cross-Spec Impact

- [ ] Changed interfaces checked for external consumers
- [ ] Shared data models checked for other spec dependencies
- [ ] Cross-spec dependency table updated if needed

---

## Post-Review

- [ ] Verdict given: APPROVE / FIX_NEEDED / REJECT
- [ ] Feedback is actionable (file:line + specific fix suggestion)
- [ ] If APPROVE: branch merged + tests run + commit made
- [ ] SPEC_TASKS_SCAN checkpoint updated
- [ ] Commit message follows review output format

---

## Linter / Type Check (run every round)

```bash
poetry run ruff check .
poetry run mypy owlclaw/
poetry run pytest tests/ -q --timeout=60
```
