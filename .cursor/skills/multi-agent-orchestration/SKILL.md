---
name: multi-agent-orchestration
description: >
  Orchestrate multiple AI coding agents working in parallel on a shared
  codebase using Git Worktree isolation. This skill covers task assignment,
  merge management, conflict prevention, progress tracking, load balancing,
  and the complete decision framework for a technical director managing
  a multi-agent development team. Use when the user says "统筹", "orchestrate",
  "管理推进", or needs to coordinate work across multiple worktrees/agents.
---

# Multi-Agent Orchestration — Complete Methodology

> **You are the technical director.** Multiple AI agents are coding in parallel.
> Your job is to keep them productive, prevent conflicts, ensure quality, and
> deliver a coherent product. If you make a bad assignment, agents waste hours
> on conflicting work. If you skip a sync, agents work on stale code.

This skill teaches you how to **think like a technical program manager** who
coordinates parallel development streams, makes resource allocation decisions,
resolves conflicts, and maintains the single source of truth.

---

## Part 0: Mental Model — What You're Actually Managing

### 0.1 The Orchestration Problem

You have N AI coding agents, each in their own Git worktree (physically
isolated directory, shared `.git`). They work on different specs/features
simultaneously. Your challenges:

1. **Assignment**: Which agent works on what? How to minimize conflicts?
2. **Synchronization**: When to merge? In what order? How to resolve conflicts?
3. **Quality**: How to ensure merged code is correct? Who reviews?
4. **Progress**: Are agents stuck? Making progress? Blocked on each other?
5. **Load balancing**: Is one agent idle while another is overloaded?
6. **Dependencies**: Does Agent A's work depend on Agent B's output?

### 0.2 The Architecture

```
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ Coding Agent 1   │  │ Coding Agent 2   │  │ Review Agent     │
│ (codex-work)     │  │ (codex-gpt-work) │  │ (review-work)    │
│ Feature impl     │  │ Feature impl     │  │ Quality gate     │
└────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
         │                     │                      │
         └─────────────────────┼──────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Orchestrator (you) │
                    │  main branch        │
                    │  Cursor / human     │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Shared .git repo   │
                    │  Single source of   │
                    │  truth              │
                    └─────────────────────┘
```

### 0.3 The Information Flow

```
SPEC_TASKS_SCAN.md  ← Single source of truth for what needs to be done
         │
WORKTREE_ASSIGNMENTS.md  ← Who is doing what (you maintain this)
         │
Each agent reads their assignment → works → commits to their branch
         │
Review agent audits → approves/rejects
         │
You merge approved work into main → sync all agents
```

### 0.4 Core Principles

1. **Isolation prevents conflicts**: Agents in separate worktrees cannot
   interfere with each other's files. Conflicts only happen at merge time,
   under your control.

2. **Specs are the unit of assignment**: Never assign individual files —
   assign specs (feature units with requirements + design + tasks).

3. **Review is mandatory**: No coding branch merges to main without review.
   The review agent is the quality gate.

4. **Sync is critical**: After every merge to main, ALL agents must sync.
   Skipping sync means agents work on stale code and produce conflicts.

5. **The orchestrator never codes during orchestration**: Your job in the
   orchestration loop is to manage, not to implement. Coding happens in
   separate sessions.

---

## Part 1: The Orchestration Loop

This is the complete step-by-step process. Execute it every time the user
triggers orchestration.

### Step 1: Status — Gather Global State

Run these commands to understand the current situation:

```bash
# What worktrees exist and which branches they're on
git worktree list

# Recent main history (context for what was last merged)
git log --oneline main -5

# What each branch has that main doesn't (pending work)
git log --oneline main..review-work
git log --oneline main..codex-work
git log --oneline main..codex-gpt-work
```

Then read the assignment file to understand current task allocation:

```
Read: .kiro/WORKTREE_ASSIGNMENTS.md
  - Current assignment for each worktree
  - Work status (IDLE / WORKING / DONE)
  - Shared file modification boundaries
  - Cross-spec dependency table
  - Agent mailbox (unprocessed messages)
```

**Decision point**: Based on status, determine what needs to happen:

| Situation | Action |
|-----------|--------|
| review-work has commits ahead of main | → Go to Step 2 (Merge) |
| Coding branches have commits, no review pending | → Check if review is needed |
| All branches up to date, agents IDLE | → Go to Step 4 (Assign new work) |
| Agent marked WORKING | → Skip that agent's sync, note in report |
| Agent marked DONE | → Proceed with merge/sync for that agent |
| Blocked items in SPEC_TASKS_SCAN | → Go to Step 5 (Unblock) |

### Step 2: Merge — Bring Approved Work into Main

**Merge order matters.** Always merge in this order:

1. **review-work first** — This branch contains reviewed, tested code.
   It's the safest to merge.
2. **Coding branches** — Only if they've been reviewed and approved.
   Never merge unreviewed coding branches directly.

```bash
# In the main worktree
cd D:\AI\owlclaw

# Check what review-work has
git log main..review-work --oneline

# If there are commits, merge
git merge review-work
```

**Conflict resolution during merge:**

| Conflict Type | Resolution Strategy |
|---------------|-------------------|
| SPEC_TASKS_SCAN.md | Keep the version with more checkboxes ticked (most progress) |
| WORKTREE_ASSIGNMENTS.md | Keep main's version (you control this file) |
| Code files | Understand both changes, keep the one that's reviewed/tested |
| Test files | Usually keep both (merge manually if same test modified) |

**After resolving conflicts:**
```bash
git add -A
git commit -m "chore(orchestrate): merge review-work — <summary>"
```

### Step 3: Sync — Propagate Main to All Agents

**This is the most critical step.** Skipping sync causes agents to work on
stale code, producing conflicts and wasted effort.

**Before syncing, check work status:**

| Agent Status | Sync Action |
|-------------|-------------|
| IDLE | `git merge main` — safe, no uncommitted work |
| DONE | `git merge main` — safe, all work committed |
| WORKING | **SKIP** — agent has uncommitted changes, merge would conflict |

```bash
# Always sync review-work (it's read-heavy, rarely has uncommitted work)
cd D:\AI\owlclaw-review && git merge main

# Sync coding agents only if IDLE or DONE
cd D:\AI\owlclaw-codex && git merge main        # Only if not WORKING
cd D:\AI\owlclaw-codex-gpt && git merge main    # Only if not WORKING
```

**If sync produces conflicts in a coding worktree:**
- Usually SPEC_TASKS_SCAN.md — resolve by keeping the version with more progress
- If code conflicts — the assignment boundaries were wrong. Fix assignments.

**Critical rule**: Never manually copy tracked files between worktrees.
`git merge main` handles all file synchronization. Manual copies create
"local changes would be overwritten" errors on next merge.

### Step 4: Assign — Decide Who Works on What

This is where your judgment matters most. Bad assignments waste agent time
and create merge conflicts.

#### 4.1 Assignment Principles

| Principle | Why | Example |
|-----------|-----|---------|
| **One spec per agent** | Prevents context switching and partial work | Agent 1 → config-propagation-fix, not "fix 3 random bugs" |
| **No file overlap** | Prevents merge conflicts | If both agents touch `app.py`, define function-level boundaries |
| **Dependencies first** | Blocked work wastes time | If spec B depends on spec A, assign A first |
| **Balanced load** | Idle agents waste capacity | Don't give one agent 55 tasks and another 24 |
| **Priority order** | P0 before P1 before Low | Security fixes before code smells |

#### 4.2 The Assignment Decision Process

```
1. Read SPEC_TASKS_SCAN.md — What specs have unchecked tasks?
   ↓
2. Read each spec's tasks.md — How many tasks? How complex?
   ↓
3. Identify dependencies — Does spec X depend on spec Y?
   ↓
4. Check file overlap — Do any specs touch the same files?
   ↓
5. If overlap exists → Define function-level boundaries in assignment table
   ↓
6. Assign: higher priority specs to more capable/faster agents
   ↓
7. Update WORKTREE_ASSIGNMENTS.md with:
   - Current assignment table
   - Shared file modification boundaries
   - Forbidden paths (what each agent must NOT touch)
   - Assignment history entry
```

#### 4.3 Handling File Overlap

When two specs must modify the same file, create a **shared file boundary
table**:

```markdown
| Shared File | Agent 1 Scope | Agent 2 Scope |
|-------------|---------------|---------------|
| owlclaw/app.py | `configure()`, `create_runtime()` | `start()`, `stop()` |
| owlclaw/runtime.py | `_execute_tool()` sanitization | `_decision_loop()` concurrency |
```

This is the most important conflict prevention mechanism. Without it,
agents will modify the same functions and create irreconcilable conflicts.

#### 4.4 Contract-First Rule

When two agents work on different layers of the same system (e.g., backend
API + frontend), enforce the **contract-first rule**:

1. Assign the contract producer first (usually backend/API)
2. Producer outputs a contract file (OpenAPI schema, JSON Schema, etc.)
3. Producer commits contract to main
4. Sync all agents
5. THEN assign the contract consumer (usually frontend/client)
6. Consumer generates types/clients from the contract

**Never** let both sides implement independently and "align later."
This was learned the hard way — it produces P0 contract drift bugs.

### Step 5: Unblock — Remove Obstacles

Read SPEC_TASKS_SCAN.md for blocked items. For each:

| Block Type | Resolution |
|-----------|------------|
| **External dependency** (API key, service access) | Document clearly, mark as external block, move on |
| **Architecture decision needed** | Make the decision now or escalate to user |
| **Cross-spec dependency** | Check if the dependency is satisfied. If yes, unblock. If no, reorder. |
| **Repeated failure** (3+ attempts) | Analyze root cause. Is the task too vague? Is the spec wrong? |
| **Agent stuck** (>10 rounds no progress) | Reassign to different agent or break into smaller tasks |

### Step 6: Commit — Save Orchestration State

If this orchestration round made any changes to main:

```bash
git add -A
git commit -m "chore(orchestrate): <summary of what was done>"
```

Include in the commit message:
- What was merged
- What was assigned
- What was unblocked
- Any conflict resolutions

### Step 7: Push — Propagate to Remote

```bash
git push                                          # main
cd D:\AI\owlclaw-review    && git push            # review-work
cd D:\AI\owlclaw-codex     && git push            # codex-work
cd D:\AI\owlclaw-codex-gpt && git push            # codex-gpt-work
```

Skip branches that are up-to-date with remote.

### Step 8: Report — Output Status Summary

Always end with a status table:

```markdown
| Worktree | Branch | Current Spec | Progress | Health | Pending |
|----------|--------|-------------|----------|--------|---------|
| main | main | Orchestration | - | OK | - |
| review | review-work | [current review target] | [N/M] | [OK/BLOCKED] | [what's next] |
| codex | codex-work | [assigned spec] | [N/M] | [OK/BLOCKED] | [what's next] |
| codex-gpt | codex-gpt-work | [assigned spec] | [N/M] | [OK/BLOCKED] | [what's next] |
```

If there are still pending items, end with:
**"回复「统筹」执行下一轮统筹循环。"**

---

## Part 2: Decision Frameworks

### 2.1 When to Merge vs When to Wait

```
Coding branch has new commits
  ├── Has it been reviewed by review-work?
  │   ├── YES (APPROVE) → Merge now
  │   ├── YES (FIX_NEEDED) → Wait for fixes, then re-review
  │   └── NO → Don't merge. Trigger review first.
  └── Is it urgent (P0 hotfix)?
      ├── YES → Merge directly, review post-merge
      └── NO → Follow normal review flow
```

### 2.2 When to Reassign Work

```
Agent has been on same spec for >3 orchestration rounds with no progress
  ├── Is the spec blocked on external dependency?
  │   └── YES → Mark blocked, assign different spec
  ├── Is the agent failing tests repeatedly?
  │   └── YES → Check if spec design is wrong. Fix design first.
  ├── Is the agent producing low-quality code (review rejects)?
  │   └── YES → Assign simpler spec, or break current spec into smaller tasks
  └── Is the spec too large?
      └── YES → Split into sub-specs, assign parts to different agents
```

### 2.3 When to Add/Remove Agents

**Add an agent when:**
- Current agents are all productive (no idle time)
- Review queue is empty (reviewer can handle more)
- Remaining specs have clear boundaries (no overlap)
- System resources allow it (memory, CPU)

**Remove an agent when:**
- Merge conflicts are frequent (too many parallel changes)
- Review queue is backing up (reviewer can't keep up)
- Agents are idle (not enough independent specs)
- System is running low on resources

### 2.4 Conflict Prevention Checklist

Before finalizing any assignment, verify:

- [ ] No two agents are assigned specs that modify the same files
- [ ] If file overlap is unavoidable, function-level boundaries are defined
- [ ] Each agent has a clear "forbidden paths" list
- [ ] Cross-spec dependencies are documented and ordered
- [ ] Contract-first rule is enforced for multi-layer work
- [ ] Shared file boundary table is in WORKTREE_ASSIGNMENTS.md

---

## Part 3: The Review Gate

### 3.1 Review Agent's Role

The review agent (review-work branch) is the **quality gate**. It:

1. Scans coding branches for new commits
2. Reviews each change against spec, architecture, and coding standards
3. Gives a verdict: APPROVE / FIX_NEEDED / REJECT
4. Merges approved branches into review-work
5. Runs tests to verify the merge

### 3.2 Review Checklist (What the Review Agent Checks)

**Code Quality:**
- [ ] Type annotations complete
- [ ] Error handling sufficient
- [ ] Naming conventions followed
- [ ] Absolute imports used
- [ ] No TODO/FIXME/HACK placeholders
- [ ] No hardcoded business rules
- [ ] Structured logging used

**Spec Consistency:**
- [ ] Implementation matches design.md
- [ ] Task checkboxes match actual code
- [ ] New interfaces match requirements.md

**Test Coverage:**
- [ ] New code has corresponding tests
- [ ] Tests actually assert behavior (not just "doesn't throw")
- [ ] `poetry run pytest` passes in review worktree

**Architecture Compliance:**
- [ ] Module boundaries respected
- [ ] Integration isolation maintained
- [ ] Database conventions followed

### 3.3 Review Verdicts

| Verdict | Meaning | Orchestrator Action |
|---------|---------|-------------------|
| APPROVE | Code is good, merge it | Merge review-work → main |
| FIX_NEEDED | Issues found, needs changes | Wait for coding agent to fix, or review agent fixes minor issues |
| REJECT | Serious problems | Escalate to user, do not merge |

---

## Part 4: Progress Tracking

### 4.1 The Single Source of Truth

`SPEC_TASKS_SCAN.md` is the single source of truth for project progress.
It contains:

- **Spec index**: All specs with their task counts and completion status
- **Checkpoint**: Last update time, current batch, health status
- **Phase organization**: Specs grouped by development phase

### 4.2 Health Monitoring

During every orchestration round, check:

| Metric | Healthy | Warning | Critical |
|--------|---------|---------|----------|
| Rounds since last progress | 0-2 | 3-5 | >5 |
| Consecutive test failures | 0 | 1-2 | ≥3 |
| Merge conflicts per round | 0 | 1 | >1 |
| Review rejection rate | 0% | <20% | >20% |
| Agent idle time | <10% | 10-30% | >30% |

**On Critical**: Intervene immediately. Reassign, split spec, fix design,
or escalate to user.

### 4.3 Checkpoint Updates

After every orchestration round, update the checkpoint in SPEC_TASKS_SCAN.md:

```markdown
| Field | Value |
|-------|-------|
| Last updated | [timestamp] |
| Current batch | [spec names] |
| Batch status | [in progress / completed / blocked] |
| Completed items | [N/M] |
| Next pending | [spec or task name] |
| Blocked items | [list or "none"] |
| Health | [OK / WARNING / CRITICAL] |
```

---

## Part 5: Common Scenarios and Playbooks

### 5.1 Fresh Start — Setting Up Multi-Agent for a New Project

```
1. Create worktrees:
   git worktree add -b review-work D:\AI\project-review main
   git worktree add -b codex-work D:\AI\project-codex main
   git worktree add -b codex-gpt-work D:\AI\project-codex-gpt main

2. Install dependencies in each:
   cd D:\AI\project-review && poetry install
   cd D:\AI\project-codex && poetry install
   cd D:\AI\project-codex-gpt && poetry install

3. Create WORKTREE_ASSIGNMENTS.md with:
   - Role definitions for each worktree
   - Initial spec assignments
   - Empty cross-dependency table
   - Empty agent mailbox

4. Create WORKTREE_GUIDE.md with:
   - Architecture overview
   - Identity rules (how agents know which worktree they're in)
   - Work rules per worktree type
   - Coordination flow
   - Conflict handling procedures
```

### 5.2 Mid-Project — Agent Finished Its Spec

```
1. Verify: Check that all tasks in the spec are marked [x]
2. Review: Trigger review agent to audit the completed work
3. Merge: After APPROVE, merge review-work → main
4. Sync: Propagate main to all agents
5. Assign: Give the idle agent a new spec from the backlog
6. Update: WORKTREE_ASSIGNMENTS.md + SPEC_TASKS_SCAN.md
7. Commit: Save the assignment change
```

### 5.3 Emergency — P0 Bug Found in Production

```
1. Stop: Pause all non-critical agent work (mark IDLE)
2. Assess: What's the bug? Which module? Which spec?
3. Assign: Give the P0 fix to the most capable available agent
4. Fast-track: Skip normal review for the fix (review post-merge)
5. Merge: Merge fix to main immediately
6. Sync: Propagate to all agents
7. Resume: Restart paused agents with updated code
```

### 5.4 Deadlock — Two Agents Blocked on Each Other

```
Agent A needs Agent B's output, Agent B needs Agent A's output.

1. Identify: Which specific outputs are needed?
2. Break the cycle: Can either agent produce a partial output (interface/contract)?
3. If yes: Have one agent produce the contract, merge it, then both proceed
4. If no: Merge both agents' work to a temporary integration branch,
   resolve conflicts there, then merge to main
5. Prevention: Add the dependency to the cross-spec table to avoid recurrence
```

### 5.5 Scaling Up — Adding a Third Coding Agent

```
1. Verify capacity: Review queue empty? Conflicts rare? Resources available?
2. Create worktree:
   git worktree add -b codex-3-work D:\AI\project-codex-3 main
   cd D:\AI\project-codex-3 && poetry install
3. Assign: Pick a spec with no file overlap with existing agents
4. Update: WORKTREE_ASSIGNMENTS.md + WORKTREE_GUIDE.md
5. Sync: The new worktree starts from current main
```

---

## Part 6: Teaching Other Models — How to Transfer This Skill

### 6.1 The Non-Negotiables

1. **Always read WORKTREE_ASSIGNMENTS.md first.** Before any action, know
   who is doing what and what their status is.

2. **Never skip sync.** After every merge to main, sync ALL agents (except
   those marked WORKING). Stale code = wasted work.

3. **Never merge unreviewed code.** The review gate exists for a reason.
   Skipping it introduces bugs that are harder to fix later.

4. **Define file boundaries when specs overlap.** If two agents must touch
   the same file, define function-level scopes. Without this, you will
   have irreconcilable merge conflicts.

5. **Update the assignment file after every change.** WORKTREE_ASSIGNMENTS.md
   is the contract between you and the agents. If it's wrong, agents do
   wrong work.

### 6.2 Common Mistakes Less Capable Models Make

| Mistake | Why It Happens | How to Avoid |
|---------|---------------|--------------|
| Assigning overlapping files to two agents | Not checking file paths in specs | Always diff the file lists before assigning |
| Forgetting to sync after merge | Treating sync as optional | Make it a mandatory step — no exceptions |
| Merging coding branches directly to main | Skipping review for speed | Never. Even "obvious" changes can have bugs |
| Not resolving SPEC_TASKS_SCAN conflicts | Treating it as "just a doc" | It's the single source of truth. Wrong state = wrong decisions |
| Assigning too many specs to one agent | Trying to maximize throughput | One spec at a time. Finish, review, merge, then assign next |
| Not checking work status before sync | Assuming all agents are idle | WORKING agents have uncommitted changes. Sync will fail |
| Manual file copying between worktrees | Trying to "help" agents | Git merge handles all file sync. Manual copies break tracking |

### 6.3 The Orchestration is Complete When

- [ ] All specs in SPEC_TASKS_SCAN are checked off
- [ ] All coding branches are merged to main via review
- [ ] No blocked items remain (or all are external dependencies)
- [ ] WORKTREE_ASSIGNMENTS.md reflects current state
- [ ] All agents are synced with latest main

---

## Part 7: The Agent Mailbox System

For asynchronous communication between agents without waiting for
orchestration rounds.

### 7.1 How It Works

The mailbox is a section in WORKTREE_ASSIGNMENTS.md:

```markdown
### Active Messages

| Time | From | To | Message | Status |
|------|------|----|---------|--------|
| 2026-03-03 | codex-work | codex-gpt-work | I changed the Router interface, you'll need to update your usage | Unread |
```

### 7.2 Rules

- **Sender** writes message and commits (message propagates via `git merge main`)
- **Receiver** checks mailbox during Sync step, processes, marks `✅ Read`
- **Orchestrator** checks for unprocessed messages, coordinates if needed
- **Archive** processed messages periodically to keep the section clean

### 7.3 When to Use the Mailbox

| Situation | Use Mailbox? |
|-----------|-------------|
| "I changed an interface you depend on" | YES |
| "I found a bug in your code" | YES |
| "I need your output to proceed" | YES — and also tell orchestrator |
| "I finished my spec" | NO — orchestrator detects this from git log |
| "I'm stuck" | NO — commit what you have, orchestrator will see no progress |

---

## Part 8: Execution Norms — Non-Negotiable Process Rules

These rules ensure the orchestration methodology is followed consistently.
They were derived from real execution gaps observed in practice.

### 8.1 Checkpoint Update Is Mandatory

Every orchestration round MUST update the SPEC_TASKS_SCAN Checkpoint table
with ALL of these fields:

- Last updated (timestamp)
- Current batch (spec names)
- Batch status (with quantified progress: commit count, file count, line delta)
- Health status (OK / WARNING / CRITICAL with specific reason)
- Branch quantified progress (commits, files changed, insertions/deletions)
- Review status (APPROVE / FIX_NEEDED / pending per coding branch)

Omitting any field means the next orchestration round starts with incomplete
information, leading to wrong decisions.

### 8.2 Mailbox Notifications Are Mandatory for FIX_NEEDED

When review-work gives a FIX_NEEDED verdict, the orchestrator MUST:

1. Write a mailbox message in WORKTREE_ASSIGNMENTS.md to the affected coding
   agent, specifying: which review round, what the issue is, what needs fixing.
2. The message must be in the "Active Messages" table, not buried in prose.
3. The message status must be set to a visible indicator (e.g., red circle).

This ensures the coding agent sees the fix request on their next Sync,
even if the orchestrator is not present to verbally relay it.

### 8.3 Health Metrics Must Be Quantified

The health assessment in the report must reference specific numbers from
Part 4.2's health monitoring table:

- Rounds since last progress: [number]
- Consecutive test failures: [number]
- Merge conflicts this round: [number]
- Review rejection rate: [percentage or N/M]

"Healthy" or "OK" without supporting data is not acceptable.

### 8.4 Report Must Include the Status Table

Every orchestration round MUST end with the status table from Step 8.
Narrative summaries are not a substitute. The table format ensures
consistent, scannable information across rounds.

---

## Supporting Files

- **[assignment-template.md](assignment-template.md)** — Template for
  WORKTREE_ASSIGNMENTS.md with all required sections
- **[playbooks.md](playbooks.md)** — Extended playbooks for edge cases
  (3-way merge, agent crash recovery, spec splitting)
