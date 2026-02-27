#!/usr/bin/env python3
"""Extract trusted-publisher claim hints from failed release run logs."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any


CLAIM_RE = re.compile(r"\*\s+`(?P<key>[^`]+)`:\s+`(?P<value>[^`]*)`")


def _run(command: list[str]) -> tuple[int, str]:
    result = subprocess.run(command, capture_output=True, text=False, check=False)
    stdout = (result.stdout or b"").decode("utf-8", errors="replace")
    stderr = (result.stderr or b"").decode("utf-8", errors="replace")
    return result.returncode, (stdout + stderr).strip()


def _extract_claims(text: str) -> dict[str, str]:
    claims: dict[str, str] = {}
    for match in CLAIM_RE.finditer(text):
        claims[match.group("key")] = match.group("value")
    return claims


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract trusted publisher claims from run logs")
    parser.add_argument("--repo", default="yeemio/owlclaw")
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument(
        "--output",
        default="docs/release/trusted-publisher-claims.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    code, output = _run(
        ["gh", "run", "view", str(args.run_id), "-R", args.repo, "--log-failed"]
    )
    if code != 0:
        raise SystemExit(f"failed to fetch run log: {output}")

    claims = _extract_claims(output)
    report: dict[str, Any] = {
        "repo": args.repo,
        "run_id": args.run_id,
        "claims": claims,
        "mapping_template": {
            "owner": claims.get("repository_owner"),
            "repository": claims.get("repository", "").split("/")[-1] if claims.get("repository") else None,
            "workflow": ".github/workflows/release.yml",
            "environment": claims.get("environment"),
        },
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[extract-trusted-publisher-claims] wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
