"""Validate required real-data CSV exports for Mionyee case study."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path


REQUIRED_FILES = {
    "llm_before.csv": {"cost_usd", "calls_total", "calls_blocked"},
    "llm_after.csv": {"cost_usd", "calls_total", "calls_blocked"},
    "scheduler_before.csv": {"total_tasks", "success_tasks", "failed_tasks", "recovery_seconds"},
    "scheduler_after.csv": {"total_tasks", "success_tasks", "failed_tasks", "recovery_seconds"},
}


@dataclass(frozen=True)
class ValidationResult:
    file_name: str
    exists: bool
    row_count: int
    missing_columns: list[str]
    status: str


def validate_file(path: Path, required_columns: set[str]) -> ValidationResult:
    if not path.exists():
        return ValidationResult(
            file_name=path.name,
            exists=False,
            row_count=0,
            missing_columns=sorted(required_columns),
            status="missing",
        )

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing_columns = sorted(required_columns - columns)
        row_count = sum(1 for _ in reader)

    if missing_columns:
        status = "invalid_columns"
    elif row_count == 0:
        status = "empty"
    else:
        status = "ok"

    return ValidationResult(
        file_name=path.name,
        exists=True,
        row_count=row_count,
        missing_columns=missing_columns,
        status=status,
    )


def build_report(input_dir: Path) -> dict[str, object]:
    results = []
    for file_name, columns in REQUIRED_FILES.items():
        results.append(validate_file(input_dir / file_name, columns))

    payload = {
        "input_dir": str(input_dir),
        "required_files": sorted(REQUIRED_FILES.keys()),
        "results": [
            {
                "file_name": item.file_name,
                "exists": item.exists,
                "row_count": item.row_count,
                "missing_columns": item.missing_columns,
                "status": item.status,
            }
            for item in results
        ],
    }
    all_ok = all(item.status == "ok" for item in results)
    payload["status"] = "pass" if all_ok else "fail"
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Mionyee real-data CSV inputs.")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    report = build_report(input_dir)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[mionyee-input-verify] wrote {output}")
    print(f"[mionyee-input-verify] status={report['status']}")


if __name__ == "__main__":
    main()
