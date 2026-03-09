"""Build repo-data.json from normalized CSV input.

Usage:
    python 50-publish/build_repo_data.py --source "20-normalized/repo_master_latest.csv"
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build publish JSON from normalized CSV.")
    parser.add_argument(
        "--source",
        required=True,
        help="Path to source CSV (e.g. 20-normalized/repo_master_latest.csv).",
    )
    parser.add_argument(
        "--output",
        default="50-publish/site/repo-data.json",
        help="Output JSON path.",
    )
    return parser.parse_args()


def normalize_row(row: dict[str, str]) -> dict[str, str]:
    return {
        "repo": (row.get("repo") or "").strip(),
        "url": (row.get("url") or "").strip(),
        "topic": (row.get("topic") or "").strip(),
        "relevance": (row.get("relevance") or "").strip(),
        "risk": ((row.get("risk") or row.get("risk_level") or "")).strip(),
        "adoption_priority": (row.get("adoption_priority") or "").strip(),
        "activity": (row.get("activity") or "").strip(),
        "license": (row.get("license") or "").strip(),
        "why_relevant": (row.get("why_relevant") or "").strip(),
        "updated_at": (row.get("updated_at") or "").strip(),
    }


def main() -> None:
    args = parse_args()
    source = Path(args.source).resolve()
    output = Path(args.output).resolve()

    if not source.exists():
        raise FileNotFoundError(f"Source CSV not found: {source}")

    rows: list[dict[str, str]] = []
    with source.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            normalized = normalize_row(row)
            if normalized["repo"]:
                rows.append(normalized)

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Wrote {len(rows)} rows to {output}")


if __name__ == "__main__":
    main()

