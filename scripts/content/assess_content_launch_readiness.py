"""Assess content-launch closure readiness from generated evidence files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def assess(
    *,
    case_data_json: Path,
    case_data_md: Path,
    direction_json: Path,
    publication_json: Path,
    case_study_md: Path,
) -> dict[str, Any]:
    case_data_payload = _load_json(case_data_json)
    direction_payload = _load_json(direction_json)
    publication_payload = _load_json(publication_json)

    has_case_data = case_data_payload is not None and case_data_md.exists()
    direction_ok = (
        direction_payload is not None
        and str(direction_payload.get("direction", "")).strip() in {"A", "B", "C"}
    )
    publication_ok = (
        publication_payload is not None
        and bool(publication_payload.get("all_required_passed", False))
    )
    case_material_ok = has_case_data and case_study_md.exists()

    task_status = {
        "task_1_data_collected": has_case_data,
        "task_2_1_direction_selected": direction_ok,
        "task_2_6_2_7_5_1_published": publication_ok,
        "task_3_2_case_data_attached": has_case_data,
        "task_5_3_case_material_complete": case_material_ok,
    }
    remaining = [task for task, ok in task_status.items() if not ok]
    return {
        "task_status": task_status,
        "remaining_tasks": remaining,
        "all_external_gates_passed": len(remaining) == 0,
        "inputs": {
            "case_data_json": str(case_data_json),
            "case_data_md": str(case_data_md),
            "direction_json": str(direction_json),
            "publication_json": str(publication_json),
            "case_study_md": str(case_study_md),
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    task_status = report["task_status"]
    assert isinstance(task_status, dict)
    lines = [
        "# Content Launch Readiness",
        "",
        "| Gate | Passed |",
        "|---|---|",
    ]
    for key, value in task_status.items():
        lines.append(f"| `{key}` | `{bool(value)}` |")
    lines.extend(
        [
            "",
            f"- all_external_gates_passed: `{report['all_external_gates_passed']}`",
            "",
            "## Remaining",
        ]
    )
    remaining = report["remaining_tasks"]
    assert isinstance(remaining, list)
    if not remaining:
        lines.append("- none")
    else:
        for item in remaining:
            lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Assess content-launch readiness from evidence artifacts.")
    parser.add_argument("--case-data-json", default="docs/content/mionyee-case-data.json")
    parser.add_argument("--case-data-md", default="docs/content/mionyee-case-data.md")
    parser.add_argument("--direction-json", default="docs/content/article-direction-decision.json")
    parser.add_argument("--publication-json", default="docs/content/publication-evidence.json")
    parser.add_argument("--case-study-md", default="docs/content/mionyee-case-study.md")
    parser.add_argument("--output-json", default="docs/content/content-launch-readiness.json")
    parser.add_argument("--output-md", default="docs/content/content-launch-readiness.md")
    args = parser.parse_args()

    report = assess(
        case_data_json=Path(args.case_data_json),
        case_data_md=Path(args.case_data_md),
        direction_json=Path(args.direction_json),
        publication_json=Path(args.publication_json),
        case_study_md=Path(args.case_study_md),
    )

    output_json = Path(args.output_json)
    output_md = Path(args.output_md)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    output_md.write_text(render_markdown(report), encoding="utf-8")
    print(f"[content-launch-readiness] wrote {output_json}")
    print(f"[content-launch-readiness] wrote {output_md}")
    print(f"[content-launch-readiness] all_external_gates_passed={report['all_external_gates_passed']}")


if __name__ == "__main__":
    main()
