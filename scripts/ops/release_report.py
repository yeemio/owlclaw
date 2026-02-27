#!/usr/bin/env python3
"""Generate a minimal release report artifact for audit trails."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Release report generator")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--output", default="artifacts/release-report.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workflow_run_id": args.run_id,
        "commit": args.commit,
        "target": args.target,
    }

    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print(f"[release-report] wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
