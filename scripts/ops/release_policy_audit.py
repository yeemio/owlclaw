#!/usr/bin/env python3
"""Audit release branch protection and required checks baseline."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RECOMMENDED_REQUIRED_CHECKS = ["Lint", "Test", "Build"]


def _run_gh_json(args: list[str]) -> tuple[int, str]:
    result = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
    output = (result.stdout or "") + (result.stderr or "")
    return result.returncode, output.strip()


def _parse_json_safe(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:
        return {"raw": text}


def _audit_branch_protection(repo: str, branch: str) -> dict[str, Any]:
    code, output = _run_gh_json(["api", f"repos/{repo}/branches/{branch}/protection"])
    protected = code == 0
    return {
        "protected": protected,
        "api_response": _parse_json_safe(output),
    }


def _audit_workflows(repo: str) -> dict[str, Any]:
    code, output = _run_gh_json(["api", f"repos/{repo}/actions/workflows"])
    if code != 0:
        return {"error": output}
    data = _parse_json_safe(output)
    workflows = [w.get("name") for w in data.get("workflows", []) if isinstance(w, dict)]
    return {"workflows": workflows}


def _build_recommendation(branch: str) -> dict[str, Any]:
    return {
        "branch": branch,
        "required_checks": RECOMMENDED_REQUIRED_CHECKS,
        "strict_status_checks": True,
        "required_approving_review_count": 1,
        "dismiss_stale_reviews": True,
        "require_code_owner_reviews": True,
        "enforce_admins": True,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Release policy audit")
    parser.add_argument("--repo", default="yeemio/owlclaw")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--output", default="docs/release/release-policy-audit.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    protection = _audit_branch_protection(args.repo, args.branch)
    workflows = _audit_workflows(args.repo)
    recommendation = _build_recommendation(args.branch)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo": args.repo,
        "branch": args.branch,
        "protection": protection,
        "workflows": workflows,
        "recommendation": recommendation,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print(f"[release-policy-audit] wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
