# Extended Playbooks — Edge Cases and Recovery Procedures

> These playbooks cover situations that don't happen often but are critical
> to handle correctly when they do.

---

## Playbook 1: Three-Way Merge Conflict

**Situation**: Both coding agents modified the same file (despite boundaries),
and review-work also made changes. Three-way conflict on merge to main.

**Steps**:

1. **Don't panic.** Git preserves all versions in conflict markers.

2. **Understand each version**:
   ```bash
   # See what each branch changed
   git diff main..review-work -- path/to/file
   git diff main..codex-work -- path/to/file
   git diff main..codex-gpt-work -- path/to/file
   ```

3. **Merge in order** (review-work first, then coding branches one at a time):
   ```bash
   git merge review-work          # Resolve conflicts with review-work
   git add -A && git commit
   git merge codex-work           # Resolve conflicts with codex-work
   git add -A && git commit
   git merge codex-gpt-work       # Resolve conflicts with codex-gpt-work
   git add -A && git commit
   ```

4. **After resolution**: Run tests to verify the merged code works.
   ```bash
   poetry run pytest tests/ -q --timeout=60
   ```

5. **Prevention**: Update the shared file boundary table to prevent recurrence.
   If the boundaries were already defined and violated, investigate why.

---

## Playbook 2: Agent Crash Recovery

**Situation**: A Codex agent crashed mid-work. The worktree has uncommitted
changes, and the agent's session is lost.

**Steps**:

1. **Assess the damage**:
   ```bash
   cd D:\AI\owlclaw-codex
   git status                    # What files were modified?
   git diff                      # What are the changes?
   git stash list                # Any stashed changes?
   ```

2. **Decision tree**:
   ```
   Are the uncommitted changes valuable?
   ├── YES (substantial progress) → Commit them as-is
   │   git add -A
   │   git commit -m "wip: agent crash recovery — [description]"
   ├── PARTIALLY (some good, some broken) → Selective commit
   │   git add [good files]
   │   git commit -m "wip: partial recovery — [description]"
   │   git checkout -- [broken files]
   └── NO (minimal or broken changes) → Discard
       git checkout -- .
       git clean -fd
   ```

3. **Restart the agent**:
   ```bash
   cd D:\AI\owlclaw-codex
   git merge main               # Sync to latest
   codex                        # Restart agent
   ```

4. **Update status**: Mark the worktree as IDLE in WORKTREE_ASSIGNMENTS.md.

---

## Playbook 3: Spec Splitting

**Situation**: A spec is too large for one agent to complete in a reasonable
time. Need to split it across two agents.

**Steps**:

1. **Analyze the spec**: Read tasks.md and identify natural split points.
   Look for:
   - Groups of tasks that touch different files
   - Tasks with no dependencies on each other
   - A clear "foundation" group and "extension" group

2. **Define the split**:
   ```
   Original: big-feature (40 tasks)
   Split into:
     big-feature-core (tasks 1-20, foundation)  → Agent 1
     big-feature-ext  (tasks 21-40, extensions)  → Agent 2
   ```

3. **Check for file overlap**: If both halves touch the same files,
   define function-level boundaries.

4. **Update assignments**: In WORKTREE_ASSIGNMENTS.md, assign each half
   to a different agent with clear scope definitions.

5. **Order matters**: If the extension depends on the core, assign core
   first. Only assign extension after core is merged to main.

---

## Playbook 4: Review Backlog

**Situation**: Coding agents are producing work faster than the review
agent can audit. Review queue is growing.

**Steps**:

1. **Assess the backlog**:
   ```bash
   git log main..codex-work --oneline | wc -l
   git log main..codex-gpt-work --oneline | wc -l
   ```

2. **Triage**: Which branch has higher-priority work? Review that first.

3. **Options**:

   | Option | When to Use |
   |--------|------------|
   | Pause one coding agent | Backlog > 20 commits |
   | Orchestrator assists review | Backlog is all low-risk changes |
   | Batch review | Multiple small commits can be reviewed together |
   | Skip review for docs-only | Changes that only touch .md files |

4. **Prevention**: Ensure coding agents commit in small, reviewable batches
   (1-3 tasks per commit), not massive dumps.

---

## Playbook 5: Dependency Deadlock Between Specs

**Situation**: Spec A needs a function from Spec B, and Spec B needs a
type definition from Spec A. Neither can proceed.

**Steps**:

1. **Identify the minimal interface**: What is the smallest piece of code
   that would unblock the other spec?

2. **Create a contract commit**: Have one agent produce just the interface
   (function signature, type definition, abstract class) without the
   implementation. Commit it to their branch.

3. **Fast-track merge**: Merge that branch to main immediately (skip full
   review for interface-only commits).

4. **Sync**: Both agents now have the interface and can proceed independently.

5. **Full implementation**: Each agent implements their side against the
   shared interface. Normal review flow applies.

6. **Document**: Add the dependency to the cross-spec table to prevent
   recurrence.

---

## Playbook 6: System Resource Exhaustion

**Situation**: Multiple agents running tests simultaneously have exhausted
system memory. System is slow or unresponsive.

**Steps**:

1. **Immediate triage**:
   ```powershell
   # Windows: Kill all Python processes
   taskkill /F /IM python.exe /T

   # Check memory usage
   Get-Process | Sort-Object WorkingSet -Descending | Select-Object -First 10
   ```

2. **Identify the cause**: Which worktree was running tests? Was there a
   timeout? Was a test hung?

3. **Prevention measures**:
   - Always use `--timeout=30` with pytest
   - Never run `poetry run pytest` without scope (specify test files)
   - Never background test processes (`&`)
   - Clean up after every test batch:
     ```powershell
     taskkill /F /IM python.exe /T 2>$null
     ```

4. **Reduce parallelism**: If resources are tight, run only one coding
   agent at a time. The other can be IDLE.

---

## Playbook 7: Major Architecture Change Mid-Sprint

**Situation**: A design decision changes that affects multiple in-progress
specs across different agents.

**Steps**:

1. **Stop all agents**: Mark all as IDLE. Don't let them continue on
   stale assumptions.

2. **Merge all current work**: Get everything into main, even if incomplete.
   ```bash
   # Merge whatever is committed and reviewed
   git merge review-work
   # For unreviewed but committed work, merge with caution
   ```

3. **Update architecture docs**: Make the design change in the architecture
   document on main.

4. **Update affected specs**: Modify design.md and tasks.md for each
   affected spec.

5. **Sync all agents**: Everyone gets the new architecture.

6. **Reassign if needed**: Some specs may need to be restarted or
   significantly modified.

7. **Resume**: Agents restart with updated specs and architecture.

---

## Playbook 8: New Agent Onboarding

**Situation**: Adding a new AI agent (new tool, new model) to the team.

**Steps**:

1. **Create infrastructure**:
   ```bash
   git worktree add -b new-agent-work D:\AI\project-new-agent main
   cd D:\AI\project-new-agent && poetry install
   ```

2. **Configure the agent**: Ensure it reads:
   - `.cursor/rules/` (or equivalent for the tool)
   - `AGENTS.md`
   - `docs/WORKTREE_GUIDE.md`
   - `.kiro/WORKTREE_ASSIGNMENTS.md`

3. **Start with a small spec**: Don't assign a complex spec first. Give it
   something small and self-contained to verify it follows the workflow.

4. **Review carefully**: The first few commits from a new agent need extra
   scrutiny. Check that it follows naming conventions, import rules,
   commit message format, etc.

5. **Gradually increase scope**: After 2-3 successful spec completions,
   assign larger specs.
