#!/usr/bin/env python3
"""Workflow agent entrypoint for multi-worktree coordination.

Usage:
  poetry run python scripts/workflow_agent.py --agent codex
  poetry run python scripts/workflow_agent.py --agent codex-gpt
  poetry run python scripts/workflow_agent.py --agent review
  poetry run python scripts/workflow_agent.py --agent codex --sync   # merge main then exit
  poetry run python scripts/workflow_agent.py --agent codex --test  # run unit tests

Local development use. See docs/WORKTREE_GUIDE.md and .kiro/WORKTREE_ASSIGNMENTS.md.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run workflow steps for the given agent (worktree).",
        epilog="See .kiro/WORKTREE_ASSIGNMENTS.md for task assignments.",
    )
    parser.add_argument(
        "--agent",
        required=True,
        choices=["codex", "codex-gpt", "review", "main"],
        help="Agent/worktree identifier.",
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Run git fetch + merge main in current directory.",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run unit tests (poetry run pytest tests/unit/ -q).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands only, do not execute.",
    )
    args = parser.parse_args()

    cwd = os.getcwd()
    print(f"workflow_agent: agent={args.agent} cwd={cwd}")

    if args.sync:
        for cmd in [
            ["git", "fetch", "origin", "main"],
            ["git", "merge", "main", "--no-edit"],
        ]:
            print(f"  run: {' '.join(cmd)}")
            if not args.dry_run:
                r = subprocess.run(cmd, cwd=cwd)
                if r.returncode != 0:
                    return r.returncode
        print("  sync done.")
        return 0

    if args.test:
        cmd = ["poetry", "run", "pytest", "tests/unit/", "-q"]
        print(f"  run: {' '.join(cmd)}")
        if not args.dry_run:
            r = subprocess.run(cmd, cwd=cwd)
            return r.returncode if r.returncode is not None else 0
        return 0

    # Default: report status
    if not args.dry_run:
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        print(f"  branch: {branch.stdout.strip() if branch.returncode == 0 else '?'}")
        print("  status:")
        subprocess.run(["git", "status", "-sb"], cwd=cwd)
    else:
        print("  branch: [dry-run] git branch --show-current")
        print("  status: [dry-run] git status -sb")
    print("  (use --sync to merge main, --test to run unit tests)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
