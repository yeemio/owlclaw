#!/usr/bin/env python3
"""Execute or simulate gateway rollback actions."""

from __future__ import annotations

import argparse
import sys


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gateway rollback executor")
    parser.add_argument("--run-id", default="", help="Pipeline run ID")
    parser.add_argument("--reason", default="unspecified", help="Rollback reason")
    parser.add_argument(
        "--target-version",
        default="previous-stable",
        help="Rollback target artifact version",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print actions without external calls")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    print("[gateway-rollback] start")
    print(f"  run_id: {args.run_id or 'n/a'}")
    print(f"  reason: {args.reason}")
    print(f"  target_version: {args.target_version}")

    if args.dry_run:
        print("[gateway-rollback] dry-run mode; no external execution.")
        return 0

    # External executor integration is intentionally isolated behind this entry point.
    # Actual production command wiring is environment-specific.
    print("[gateway-rollback] external rollback executor is not configured in this environment.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
