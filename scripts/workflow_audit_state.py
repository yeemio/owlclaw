"""Read and write audit runtime state for audit-a / audit-b windows."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


VALID_AUDIT_AGENTS = {"audit-a", "audit-b"}
VALID_AUDIT_STATUS = {"idle", "started", "blocked", "done", "waiting_review"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(repo_root: Path) -> Path:
    return repo_root / ".kiro" / "runtime"


def _state_dir(repo_root: Path) -> Path:
    return _runtime_dir(repo_root) / "audit-state"


def _state_path(repo_root: Path, agent: str) -> Path:
    return _state_dir(repo_root) / f"{agent}.json"


def _validate_agent(agent: str) -> str:
    if agent not in VALID_AUDIT_AGENTS:
        raise ValueError(f"unknown audit agent '{agent}'")
    return agent


def ensure_dirs(repo_root: Path) -> None:
    _state_dir(repo_root).mkdir(parents=True, exist_ok=True)


def read_state(repo_root: Path, agent: str) -> dict[str, object] | None:
    _validate_agent(agent)
    path = _state_path(repo_root, agent)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_state(
    repo_root: Path,
    agent: str,
    *,
    status: str,
    summary: str = "",
    finding_ref: str = "",
    note: str = "",
) -> dict[str, object]:
    _validate_agent(agent)
    if status not in VALID_AUDIT_STATUS:
        raise ValueError(f"invalid audit status '{status}'")
    ensure_dirs(repo_root)
    payload = {
        "agent": agent,
        "status": status,
        "summary": summary.strip(),
        "finding_ref": finding_ref.strip(),
        "note": note.strip(),
        "updated_at": _utc_now(),
    }
    _state_path(repo_root, agent).write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read or write audit runtime state.")
    parser.add_argument("--repo-root", default=".", help="Path to the main repository root.")

    subparsers = parser.add_subparsers(dest="command", required=True)

    show = subparsers.add_parser("show", help="Show current audit state.")
    show.add_argument("--agent", required=True, choices=sorted(VALID_AUDIT_AGENTS))
    show.add_argument("--json", action="store_true", help="Emit JSON output.")

    update = subparsers.add_parser("update", help="Update current audit state.")
    update.add_argument("--agent", required=True, choices=sorted(VALID_AUDIT_AGENTS))
    update.add_argument("--status", required=True, choices=sorted(VALID_AUDIT_STATUS))
    update.add_argument("--summary", default="", help="Short work summary.")
    update.add_argument("--finding-ref", default="", help="Finding or task reference, e.g. D48.")
    update.add_argument("--note", default="", help="Free-form note.")
    update.add_argument("--json", action="store_true", help="Emit JSON output.")

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = Path(args.repo_root).resolve()

    if args.command == "show":
        payload = read_state(repo_root, args.agent)
        if payload is None:
            payload = {"agent": args.agent, "status": "missing"}
        if args.json:
            print(json.dumps(payload, ensure_ascii=True, indent=2))
        else:
            print(f"{payload['agent']}: {payload['status']}")
        return 0

    payload = write_state(
        repo_root,
        args.agent,
        status=args.status,
        summary=args.summary,
        finding_ref=args.finding_ref,
        note=args.note,
    )
    if args.json:
        print(json.dumps(payload, ensure_ascii=True, indent=2))
    else:
        print(f"{payload['agent']}: {payload['status']} {payload['finding_ref']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
