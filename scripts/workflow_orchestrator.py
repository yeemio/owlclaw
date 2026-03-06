"""Continuous orchestrator loop for the OwlClaw multi-worktree workflow."""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import workflow_mailbox  # noqa: E402
import workflow_status  # noqa: E402


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(repo_root: Path) -> Path:
    return repo_root / ".kiro" / "runtime"


def _priority_for_state(
    state: workflow_status.WorktreeState,
    snapshot: workflow_status.WorkflowSnapshot,
    action: dict[str, object],
) -> str:
    if not state.clean:
        return "high"
    if action["stage"] == "review" and state.role == "review":
        return "high"
    if action["stage"] == "merge" and state.name == "main":
        return "high"
    if action["stage"] == "assign" and state.name == "main":
        return "high"
    if state.role == "coding" and state.ahead_of_main > 0:
        return "high"
    return "normal"


def _next_transition_for_state(
    state: workflow_status.WorktreeState,
    snapshot: workflow_status.WorkflowSnapshot,
) -> str:
    if state.name == "main":
        coding = [worktree for worktree in snapshot.worktrees if worktree.role == "coding"]
        if (
            snapshot.worktrees[1].ahead_of_main == 0
            and all(worktree.clean and worktree.ahead_of_main == 0 for worktree in coding)
        ):
            return "assign_next_batch"
        return "merge_review" if snapshot.worktrees[1].ahead_of_main > 0 else "monitor"
    if state.role == "review":
        pending = [w for w in snapshot.worktrees if w.role == "coding" and w.ahead_of_main > 0]
        return "review_pending_commits" if pending else "idle"
    if not state.clean:
        return "cleanup"
    if state.ahead_of_main > 0:
        return "await_review"
    return "await_assignment"


def _mailbox_action_text(
    state: workflow_status.WorktreeState,
    snapshot: workflow_status.WorkflowSnapshot,
) -> str:
    if state.name == "main":
        coding = [worktree for worktree in snapshot.worktrees if worktree.role == "coding"]
        if not state.clean:
            return "clean_local_changes"
        if snapshot.worktrees[1].ahead_of_main > 0:
            return "merge_review_work"
        if all(worktree.clean and worktree.ahead_of_main == 0 for worktree in coding):
            return "assign_next_batch"
        return "monitor"
    if state.role == "review":
        pending = [w for w in snapshot.worktrees if w.role == "coding" and w.ahead_of_main > 0]
        return "review_pending_commits" if pending else "idle"
    if not state.clean:
        return "cleanup_or_commit_local_changes"
    if state.ahead_of_main > 0:
        return "wait_for_review"
    return "wait_for_assignment"


def _mailbox_summary(
    state: workflow_status.WorktreeState,
    snapshot: workflow_status.WorkflowSnapshot,
) -> str:
    if state.name == "main":
        coding = [worktree for worktree in snapshot.worktrees if worktree.role == "coding"]
        if not state.clean:
            return "Clean local changes before orchestrating merges or sync."
        if snapshot.worktrees[1].ahead_of_main > 0:
            return "review-work is ahead of main; merge it into main and push."
        if all(worktree.clean and worktree.ahead_of_main == 0 for worktree in coding):
            return "Coding and review queues are clear; assign the next batch before nudging agents."
        return "No immediate main-branch action."
    if state.role == "review":
        pending = [w for w in snapshot.worktrees if w.role == "coding" and w.ahead_of_main > 0]
        if pending:
            names = ", ".join(item.branch for item in pending)
            return f"Review pending coding submissions in order: {names}."
        return "No coding branch is waiting for review."
    if not state.clean:
        return "Clean or commit local changes before continuing."
    if state.ahead_of_main > 0:
        return "Stop coding and wait for review-work verdict."
    return "No active review queue entry; wait for the next assignment."


def _mailbox_blockers(
    state: workflow_status.WorktreeState,
    snapshot: workflow_status.WorkflowSnapshot,
) -> list[str]:
    blockers = list(snapshot.blockers)
    if state.dirty_files:
        blockers.append(f"{state.branch} has uncommitted changes")
    if state.role == "coding" and state.ahead_of_main > 0:
        blockers.append(f"{state.branch} is waiting for review-work review")
    return blockers


def _mailbox_payload(
    state: workflow_status.WorktreeState,
    snapshot: workflow_status.WorkflowSnapshot,
    action: dict[str, object],
) -> dict[str, object]:
    pending_commits = state.pending_commits
    if state.role == "review":
        pending_commits = [
            commit
            for worktree in snapshot.worktrees
            if worktree.role == "coding" and worktree.ahead_of_main > 0
            for commit in worktree.pending_commits
        ]
    return {
        "mailbox_version": 1,
        "generated_at": _utc_now(),
        "agent": state.name,
        "branch": state.branch,
        "role": state.role,
        "stage": action["stage"],
        "owner": action["owner"],
        "action": _mailbox_action_text(state, snapshot),
        "priority": _priority_for_state(state, snapshot, action),
        "summary": _mailbox_summary(state, snapshot),
        "blockers": _mailbox_blockers(state, snapshot),
        "dirty_files": state.dirty_files,
        "pending_commits": pending_commits,
        "next_expected_transition": _next_transition_for_state(state, snapshot),
    }


def _collect_acks(repo_root: Path) -> dict[str, dict[str, object] | None]:
    return {
        agent: workflow_mailbox.read_ack(repo_root, agent)
        for agent in sorted(workflow_mailbox.VALID_AGENT_NAMES)
    }


def _classify_action(snapshot: workflow_status.WorkflowSnapshot) -> dict[str, object]:
    worktrees = {state.name: state for state in snapshot.worktrees}
    coding = [state for state in snapshot.worktrees if state.role == "coding"]
    pending_coding = [state for state in coding if state.ahead_of_main > 0]
    review = worktrees["review"]
    main = worktrees["main"]

    stage = "stable"
    owner = "main"
    summary = snapshot.next_action

    if not main.clean:
        stage = "cleanup"
        owner = "main"
    elif any(not state.clean for state in coding):
        stage = "cleanup"
        owner = "coding"
    elif review.ahead_of_main > 0:
        stage = "merge"
        owner = "main"
    elif pending_coding:
        stage = "review"
        owner = "review"
    elif review.clean and all(state.clean for state in coding):
        stage = "assign"
        owner = "main"

    return {
        "stage": stage,
        "owner": owner,
        "summary": summary,
        "pending_coding_branches": [state.branch for state in pending_coding],
        "blockers": snapshot.blockers,
    }


def _render_actions(snapshot: workflow_status.WorkflowSnapshot, action: dict[str, object]) -> str:
    worktrees = {state.name: state for state in snapshot.worktrees}
    coding = [state for state in snapshot.worktrees if state.role == "coding"]
    lines = [
        f"# Workflow Actions",
        "",
        f"- generated_at: {_utc_now()}",
        f"- stage: {action['stage']}",
        f"- owner: {action['owner']}",
        f"- summary: {action['summary']}",
        "",
        "## Main",
    ]

    if not worktrees["main"].clean:
        lines.append("- Clean uncommitted changes before any merge or review promotion.")
    elif worktrees["review"].ahead_of_main > 0:
        lines.append("- Merge `review-work` into `main` and push.")
    elif all(state.clean and state.ahead_of_main == 0 for state in coding):
        lines.append("- Coding queues are clear; assign the next batch before sending new prompts.")
    else:
        lines.append("- No immediate main-branch action.")

    lines.extend(["", "## Review"])
    pending_coding = [state for state in coding if state.ahead_of_main > 0]
    if pending_coding:
        for state in pending_coding:
            lines.append(f"- Review `{state.branch}` pending commits ({len(state.pending_commits)} commits).")
    else:
        lines.append("- No coding branch pending review.")

    lines.extend(["", "## Coding"])
    for state in coding:
        if not state.clean:
            lines.append(f"- `{state.branch}`: clean dirty worktree before continuing.")
        elif state.ahead_of_main > 0:
            lines.append(f"- `{state.branch}`: stop coding and wait for review-work review.")
        else:
            lines.append(f"- `{state.branch}`: no pending review commit detected.")

    lines.extend(["", "## Audit"])
    lines.append(
        f"- findings={snapshot.audit.total_findings or '?'} p1={snapshot.audit.p1 or '?'} "
        f"low={snapshot.audit.low or '?'} progress={snapshot.audit.spec_progress or '?'}"
    )
    if snapshot.audit.spec_summary:
        lines.append(f"- {snapshot.audit.spec_summary}")

    if snapshot.blockers:
        lines.extend(["", "## Blockers"])
        for blocker in snapshot.blockers:
            lines.append(f"- {blocker}")

    return "\n".join(lines) + "\n"


def _render_worktree_instruction(
    state: workflow_status.WorktreeState,
    snapshot: workflow_status.WorkflowSnapshot,
    action: dict[str, object],
) -> str:
    lines = [
        f"# {state.branch}",
        "",
        f"- generated_at: {_utc_now()}",
        f"- role: {state.role}",
        f"- clean: {'yes' if state.clean else 'no'}",
        f"- ahead_of_main: {state.ahead_of_main}",
        f"- ahead_of_remote: {state.ahead_of_remote}",
    ]
    if state.pending_commits:
        lines.append(f"- latest_pending_commit: {state.pending_commits[0]}")
    lines.append("")

    if state.name == "main":
        if not state.clean:
            lines.append("Action: clean local changes before orchestrating merges.")
        elif snapshot.worktrees[1].ahead_of_main > 0:
            lines.append("Action: merge review-work into main.")
        elif all(
            worktree.clean and worktree.ahead_of_main == 0
            for worktree in snapshot.worktrees
            if worktree.role == "coding"
        ):
            lines.append("Action: assign the next batch only after coding and review are both clear.")
        else:
            lines.append("Action: monitor only.")
    elif state.role == "review":
        pending = [w for w in snapshot.worktrees if w.role == "coding" and w.ahead_of_main > 0]
        if pending:
            lines.append("Action: review coding branches in order:")
            for pending_state in pending:
                lines.append(f"- {pending_state.branch}")
        else:
            lines.append("Action: no pending coding branch to review.")
    else:
        if not state.clean:
            lines.append("Action: commit or clean local changes first.")
        elif state.ahead_of_main > 0:
            lines.append("Action: wait for review-work; do not continue overlapping work.")
        else:
            lines.append("Action: no pending review commit; wait for next assignment.")

    if action["stage"] == "cleanup" and state.role == "coding" and not state.clean:
        lines.append("Priority: high")
    elif action["stage"] == "review" and state.role == "review":
        lines.append("Priority: high")
    return "\n".join(lines) + "\n"


def write_runtime_files(repo_root: Path, snapshot: workflow_status.WorkflowSnapshot) -> None:
    runtime_dir = _runtime_dir(repo_root)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    worktree_dir = runtime_dir / "worktrees"
    worktree_dir.mkdir(parents=True, exist_ok=True)
    workflow_mailbox.ensure_runtime_dirs(repo_root)

    action = _classify_action(snapshot)
    acknowledgements = _collect_acks(repo_root)
    payload = {
        "generated_at": _utc_now(),
        "snapshot": asdict(snapshot),
        "action": action,
        "acks": acknowledgements,
    }
    (runtime_dir / "workflow_snapshot.json").write_text(
        json.dumps(payload, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    (runtime_dir / "workflow_actions.md").write_text(
        _render_actions(snapshot, action),
        encoding="utf-8",
    )
    for state in snapshot.worktrees:
        mailbox = _mailbox_payload(state, snapshot, action)
        (runtime_dir / "mailboxes" / f"{state.name}.json").write_text(
            json.dumps(mailbox, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )
        (worktree_dir / f"{state.name}.md").write_text(
            _render_worktree_instruction(state, snapshot, action),
            encoding="utf-8",
        )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Continuously orchestrate the OwlClaw workflow.")
    parser.add_argument("--repo-root", default=".", help="Path to the main repository root.")
    parser.add_argument("--once", action="store_true", help="Run a single orchestration pass.")
    parser.add_argument("--interval", type=int, default=30, help="Watch interval in seconds.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    repo_root = Path(args.repo_root).resolve()

    while True:
        snapshot = workflow_status.build_snapshot(repo_root)
        write_runtime_files(repo_root, snapshot)
        print(f"[{_utc_now()}] {snapshot.next_action}")
        if args.once:
            return 0
        time.sleep(max(5, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
