#!/usr/bin/env python3
"""Audit release supply-chain readiness and blocking conditions."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _run(args: list[str]) -> tuple[int, str]:
    result = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
    output = (result.stdout or "") + (result.stderr or "")
    return result.returncode, output.strip()


def _parse_json_safe(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:
        return {"raw": text}


def _list_release_runs(repo: str, limit: int) -> dict[str, Any]:
    code, output = _run(
        [
            "run",
            "list",
            "-R",
            repo,
            "--workflow",
            "release.yml",
            "--limit",
            str(limit),
            "--json",
            "databaseId,status,conclusion,headBranch,createdAt,updatedAt,url,displayTitle",
        ]
    )
    if code != 0:
        return {"error": output}
    data = _parse_json_safe(output)
    if not isinstance(data, list):
        return {"error": "unexpected response", "raw": data}
    return {"runs": data}


def _list_environments(repo: str) -> dict[str, Any]:
    code, output = _run(["api", f"repos/{repo}/environments"])
    if code != 0:
        return {"error": output}
    data = _parse_json_safe(output)
    envs: list[dict[str, Any]] = []
    for item in data.get("environments", []):
        if not isinstance(item, dict):
            continue
        envs.append(
            {
                "name": item.get("name"),
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
                "deployment_branch_policy": item.get("deployment_branch_policy"),
            }
        )
    return {"total_count": data.get("total_count"), "environments": envs}


def _list_secrets(repo: str) -> dict[str, Any]:
    code, output = _run(["secret", "list", "-R", repo])
    if code != 0:
        return {"error": output}
    names: list[str] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        if parts:
            names.append(parts[0])
    return {"count": len(names), "names": names}


def _branch_protection(repo: str, branch: str) -> dict[str, Any]:
    code, output = _run(["api", f"repos/{repo}/branches/{branch}/protection"])
    return {"protected": code == 0, "response": _parse_json_safe(output)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Release supply-chain readiness audit")
    parser.add_argument("--repo", default="yeemio/owlclaw")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument(
        "--output",
        default="docs/release/release-supply-chain-audit.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo": args.repo,
        "branch": args.branch,
        "release_runs": _list_release_runs(args.repo, args.limit),
        "environments": _list_environments(args.repo),
        "secrets": _list_secrets(args.repo),
        "branch_protection": _branch_protection(args.repo, args.branch),
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[release-supply-chain-audit] wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
