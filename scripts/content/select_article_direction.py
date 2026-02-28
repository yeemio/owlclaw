"""Select content-launch article direction (A/B/C) from real case metrics."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DirectionDecision:
    direction: str
    title: str
    rationale: str


def _parse_percent(value: Any) -> float | None:
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    if not isinstance(value, str):
        return None
    raw = value.strip().lower()
    if not raw or raw == "n/a":
        return None
    if raw.endswith("%"):
        raw = raw[:-1].strip()
    try:
        return float(raw)
    except ValueError:
        return None


def choose_direction(payload: dict[str, Any]) -> DirectionDecision:
    llm = payload.get("llm", {})
    scheduler = payload.get("scheduler", {})
    if not isinstance(llm, dict) or not isinstance(scheduler, dict):
        return DirectionDecision(
            direction="C",
            title="One command to connect OpenClaw to your business database",
            rationale="Metrics section missing, fallback to integration tutorial direction.",
        )

    # Cost reduction => negative delta means better.
    llm_cost_delta = _parse_percent(llm.get("delta_cost_pct"))
    scheduler_recovery_delta = _parse_percent(scheduler.get("delta_recovery_seconds_pct"))
    scheduler_success_delta = _parse_percent(scheduler.get("delta_success_rate_pct"))

    governance_score = abs(llm_cost_delta) if llm_cost_delta is not None and llm_cost_delta < 0 else 0.0
    recovery_score = abs(scheduler_recovery_delta) if (
        scheduler_recovery_delta is not None and scheduler_recovery_delta < 0
    ) else 0.0
    success_score = scheduler_success_delta if scheduler_success_delta is not None and scheduler_success_delta > 0 else 0.0
    scheduler_score = recovery_score + success_score

    if governance_score == 0 and scheduler_score == 0:
        return DirectionDecision(
            direction="C",
            title="One command to connect OpenClaw to your business database",
            rationale="No strong governance/scheduler signal from real data; use integration tutorial direction.",
        )

    if governance_score >= scheduler_score:
        return DirectionDecision(
            direction="A",
            title="How I stopped my AI app from burning $50/day on runaway LLM calls",
            rationale=(
                f"Governance signal stronger (cost delta {llm.get('delta_cost_pct')}) "
                f"than scheduler signal (score {scheduler_score:.2f})."
            ),
        )

    return DirectionDecision(
        direction="B",
        title="I replaced APScheduler with Hatchet and my tasks stopped disappearing",
        rationale=(
            "Scheduler signal stronger "
            f"(success delta {scheduler.get('delta_success_rate_pct')}, "
            f"recovery delta {scheduler.get('delta_recovery_seconds_pct')}) "
            f"than governance signal (score {governance_score:.2f})."
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Choose article direction from real Mionyee metrics.")
    parser.add_argument("--input-json", required=True, help="Path to docs/content/mionyee-case-data.json")
    parser.add_argument(
        "--output-json",
        default="docs/content/article-direction-decision.json",
        help="Where to write decision output JSON.",
    )
    args = parser.parse_args()

    input_path = Path(args.input_json)
    output_path = Path(args.output_json)

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Input JSON root must be an object")

    decision = choose_direction(payload)
    result = {
        "direction": decision.direction,
        "title": decision.title,
        "rationale": decision.rationale,
        "source": str(input_path),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[article-direction] {decision.direction}: {decision.title}")
    print(f"[article-direction] rationale: {decision.rationale}")
    print(f"[article-direction] wrote {output_path}")


if __name__ == "__main__":
    main()
